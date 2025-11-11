import os
from dotenv import load_dotenv
import openai
from pinecone import Pinecone
from textwrap import shorten

# =====================================
# Load environment variables
# =====================================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "agentic-med-hi-en")

if not OPENAI_API_KEY or not PINECONE_API_KEY:
    raise ValueError("❌ Missing API keys in .env")

openai.api_key = OPENAI_API_KEY

# =====================================
# Initialize Pinecone client
# =====================================
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

# =====================================
# Helper: create embedding for query
# =====================================
def get_query_embedding(query, model="text-embedding-3-large"):
    response = openai.embeddings.create(model=model, input=query)
    emb = response.data[0].embedding
    print(f"\n🧩 Created embedding for query → dim: {len(emb)}")
    return emb

# =====================================
# Helper: pretty-print results
# =====================================
def print_results(title, results):
    print(f"\n🔹 {title}")
    if not results:
        print("   (no results)")
        return
    for i, match in enumerate(results, start=1):
        metadata = match["metadata"]
        text = metadata.get("text") or match.get("text", "")
        preview = shorten(text, width=150, placeholder=" ...")
        score = round(match["score"], 3)
        print(f"   {i}. Score: {score}")
        print(f"      Source: {metadata.get('source', 'N/A')}")
        if "category" in metadata:
            print(f"      Category: {metadata['category']}")
        if "risk_flag" in metadata:
            print(f"      Risk Flag: {metadata['risk_flag']}")
        print(f"      Preview: {preview}")
        print("")

# =====================================
# Query both namespaces
# =====================================
query = input("\n💬 Enter a query (Hindi or English): ").strip()
query_emb = get_query_embedding(query)

# 1️⃣ Cultural semantics
results_cultural = index.query(
    namespace="cultural_semantics",
    vector=query_emb,
    top_k=3,
    include_metadata=True
)["matches"]

# 2️⃣ Bilingual medical
results_medical = index.query(
    namespace="bilingual_medical",
    vector=query_emb,
    top_k=3,
    include_metadata=True
)["matches"]

# =====================================
# Print combined results
# =====================================
print_results("Cultural Semantics Results (Idioms / Expressions)", results_cultural)
print_results("Bilingual Medical Results (Educational Context)", results_medical)
