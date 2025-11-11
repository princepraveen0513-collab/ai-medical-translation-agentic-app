"""
Build embeddings for preprocessed bilingual medical documents
------------------------------------------------------------
Creates a new namespace: bilingual_medical_clean
Uses OpenAI text-embedding-3-large (3072 dimensions)
"""

import os
import json
import time
from tqdm import tqdm
from openai import OpenAI
from pinecone import Pinecone

# ===============================================================
# Configuration
# ===============================================================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "preprocessed", "bilingual_clean.jsonl")

# Namespace name for new cleaned bilingual docs
NAMESPACE = "bilingual_medical_clean"

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

# Initialize clients
client = OpenAI(api_key=OPENAI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

# ===============================================================
# Helper Functions
# ===============================================================

def embed_texts(texts, model="text-embedding-3-large"):
    """Get embeddings for a list of texts."""
    response = client.embeddings.create(model=model, input=texts)
    embeddings = [d.embedding for d in response.data]

    # Print dimension + preview once
    if not hasattr(embed_texts, "_printed_once"):
        dim = len(embeddings[0])
        print(f"\n🧩 Embedding model: {model}")
        print(f"   → Dimension: {dim}")
        print(f"   → Preview of first embedding: {embeddings[0][:5]} ...")
        embed_texts._printed_once = True
    return embeddings


def chunk_text(text, chunk_size=600, overlap=100):
    """Split text into overlapping chunks (by characters)."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk.strip())
        start += chunk_size - overlap
    return [c for c in chunks if len(c) > 50]


def process_jsonl(data_path):
    """Load bilingual JSONL and create chunked records for embedding."""
    docs = []
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            docs.append(json.loads(line))

    all_chunks = []
    for doc in docs:
        doc_id = doc.get("id")
        src = doc.get("source_file")
        for lang in ["english", "hindi"]:
            text = doc.get(lang, "")
            if not text.strip():
                continue
            chunks = chunk_text(text)
            for i, chunk in enumerate(chunks):
                all_chunks.append({
                    "id": f"{doc_id}_{lang}_chunk_{i}",
                    "text": chunk,
                    "metadata": {
                        "doc_id": doc_id,
                        "source_file": src,
                        "language": lang,
                        "chunk_index": i,
                        "namespace": NAMESPACE
                    }
                })
    print(f"🧾 Prepared {len(all_chunks):,} text chunks from {len(docs)} documents.")
    return all_chunks


def batch_upsert(chunks, batch_size=64):
    """Embed and upsert in batches."""
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        texts = [c["text"] for c in batch]
        ids = [c["id"] for c in batch]
        metadata = [c["metadata"] for c in batch]

        embeddings = embed_texts(texts)
        vectors = [
            {"id": ids[j], "values": embeddings[j], "metadata": metadata[j]}
            for j in range(len(embeddings))
        ]
        index.upsert(vectors=vectors, namespace=NAMESPACE)
        print(f"  → Upserted batch of {len(vectors)} into namespace '{NAMESPACE}'")
        time.sleep(0.5)


# ===============================================================
# Main Pipeline
# ===============================================================

def main():
    print(f"\n🚀 Building embeddings for cleaned bilingual docs...")
    print(f"📁 Source: {DATA_PATH}")
    print(f"📦 Target namespace: {NAMESPACE}")

    chunks = process_jsonl(DATA_PATH)
    batch_upsert(chunks)

    # Print index stats
    stats = index.describe_index_stats()
    ns = stats.get("namespaces", {}).get(NAMESPACE, {})
    print(f"\n✅ Completed upserting cleaned bilingual chunks.")
    print(f"🔍 Namespace '{NAMESPACE}': {ns.get('vector_count', 0)} vectors.\n")


if __name__ == "__main__":
    main()
