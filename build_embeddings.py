import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv

import openai
from pinecone import Pinecone, ServerlessSpec
import pandas as pd

# =====================================
# Step 0: Load environment variables
# =====================================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")  # e.g., "us-east-1"
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "agentic-med-hi-en")

if not OPENAI_API_KEY or not PINECONE_API_KEY:
    raise ValueError("❌ Missing OPENAI_API_KEY or PINECONE_API_KEY in .env")

openai.api_key = OPENAI_API_KEY

# =====================================
# Step 1: Initialize Pinecone (new SDK style)
# =====================================
pc = Pinecone(api_key=PINECONE_API_KEY)

# Get all existing indexes
existing_indexes = [idx["name"] for idx in pc.list_indexes()]

if INDEX_NAME not in existing_indexes:
    print(f"🧱 Creating Pinecone index: {INDEX_NAME}")
    pc.create_index(
        name=INDEX_NAME,
        dimension=3072,  # text-embedding-3-large
        metric="cosine",
        spec=ServerlessSpec(
            cloud=PINECONE_CLOUD,
            region=PINECONE_ENVIRONMENT
        )
    )
else:
    print(f"✅ Pinecone index '{INDEX_NAME}' already exists")

# Connect to the index
index = pc.Index(INDEX_NAME)

# =====================================
# Helper: embed a list of texts
# =====================================
def embed_texts(texts, model="text-embedding-3-large"):
    """
    Takes a list of texts, calls OpenAI embeddings API,
    and returns list of embeddings.
    Also prints dimension info for the first call.
    """
    response = openai.embeddings.create(model=model, input=texts)
    embeddings = [d.embedding for d in response.data]

    # Print dimension + preview (only once per run)
    if not hasattr(embed_texts, "_printed_once"):
        dim = len(embeddings[0])
        print(f"\n🧩 Embedding model: {model}")
        print(f"   → Dimension: {dim}")
        print(f"   → Preview of first embedding: {embeddings[0][:5]} ...")
        embed_texts._printed_once = True

    return embeddings


# =====================================
# Step 2: Load artifacts and upsert embeddings
# =====================================
ARTIFACTS_DIR = Path("artifacts")
EMB_ARTIFACTS_DIR = Path("embeddings_artifacts")
EMB_ARTIFACTS_DIR.mkdir(exist_ok=True)

# ========== 2A. Bilingual Chunks ==========
bilingual_file = ARTIFACTS_DIR / "bilingual_chunks.jsonl"
if not bilingual_file.exists():
    raise FileNotFoundError(f"❌ Bilingual chunks file not found: {bilingual_file}")

print("\n➡️  Upserting bilingual medical chunks ...")
batch_size = 64
namespace = "bilingual_medical"
batch = []

with open(bilingual_file, "r", encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        chunk_id = rec["chunk_id"]
        text = rec["text"]
        metadata = {k: v for k, v in rec.items() if k not in ["chunk_id", "text"]}
        batch.append((chunk_id, text, metadata))

        if len(batch) >= batch_size:
            ids, texts, metas = zip(*batch)
            embs = embed_texts(list(texts))
            upserts = [(ids[i], embs[i], metas[i]) for i in range(len(ids))]
            index.upsert(vectors=upserts, namespace=namespace)
            print(f"  → Upserted batch of {len(ids)} into namespace '{namespace}'")
            batch = []
            time.sleep(1)

# Final remainder
if batch:
    ids, texts, metas = zip(*batch)
    embs = embed_texts(list(texts))
    upserts = [(ids[i], embs[i], metas[i]) for i in range(len(ids))]
    index.upsert(vectors=upserts, namespace=namespace)
    print(f"  → Upserted final batch of {len(ids)} into namespace '{namespace}'")

print("✅ Completed upserting bilingual medical chunks.")


# ========== 2B. Cultural Semantics Entries ==========
cs_file = ARTIFACTS_DIR / "cultural_semantics_entries.jsonl"
if not cs_file.exists():
    raise FileNotFoundError(f"❌ Cultural semantics file not found: {cs_file}")

print("\n➡️  Upserting cultural semantics entries ...")
batch_size = 64
namespace = "cultural_semantics"
batch = []

with open(cs_file, "r", encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        rec_id = rec["id"]
        text = rec["text"]
        metadata = rec["metadata"]
        batch.append((rec_id, text, metadata))

        if len(batch) >= batch_size:
            ids, texts, metas = zip(*batch)
            embs = embed_texts(list(texts))
            upserts = [(ids[i], embs[i], metas[i]) for i in range(len(ids))]
            index.upsert(vectors=upserts, namespace=namespace)
            print(f"  → Upserted batch of {len(ids)} into namespace '{namespace}'")
            batch = []
            time.sleep(1)

# Final remainder
if batch:
    ids, texts, metas = zip(*batch)
    embs = embed_texts(list(texts))
    upserts = [(ids[i], embs[i], metas[i]) for i in range(len(ids))]
    index.upsert(vectors=upserts, namespace=namespace)
    print(f"  → Upserted final batch of {len(ids)} into namespace '{namespace}'")

print("✅ Completed upserting cultural semantics entries.")


# =====================================
# Step 3: Verification / Stats
# =====================================
print("\n🔍 Index stats:")
stats = index.describe_index_stats()
for ns, ns_data in stats["namespaces"].items():
    print(f"  Namespace '{ns}': {ns_data['vector_count']} vectors")

print("\n🎉 Embedding + upload complete.\n")
