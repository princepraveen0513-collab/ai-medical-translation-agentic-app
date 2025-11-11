"""
Batch Preprocessing Pipeline for Bilingual Medical PDFs
-------------------------------------------------------
- Scans data/bilingual/ for all PDF files
- Extracts English and Hindi text separately
- Cleans, normalizes, and lowercases
- Saves one clean JSON record per document in:
      data/preprocessed/bilingual_clean.jsonl
"""

import os
import re
import json
import unicodedata
import fitz  # PyMuPDF
from tqdm import tqdm

# ===============================================================
# Configuration
# ===============================================================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "bilingual")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "preprocessed", "bilingual_clean.jsonl")

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

# ===============================================================
# Helpers
# ===============================================================

def normalize_text(text: str) -> str:
    """Clean, normalize, lowercase, and remove extra noise."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = text.replace("–", "-").replace("•", "-")
    noise_patterns = [
        r'www\.[A-Za-z0-9./_-]+',
        r'reproductive health access project',
        r'healthinfotranslations\.org',
        r'page \d+ of \d+',
        r'©.*\d{4}',  # copyright
    ]
    for pat in noise_patterns:
        text = re.sub(pat, '', text, flags=re.IGNORECASE)
    return text.strip()


def detect_language(text: str) -> str:
    """Detect if text is English or Hindi."""
    if re.search(r'[\u0900-\u097F]', text):
        return "hi"
    elif re.search(r'[A-Za-z]', text):
        return "en"
    else:
        return "other"


def extract_text_by_language(pdf_path: str):
    """Extract and separate all English and Hindi text from a PDF."""
    doc = fitz.open(pdf_path)
    english_blocks, hindi_blocks = [], []

    for page in doc:
        blocks = page.get_text("blocks")
        for b in blocks:
            _, _, _, _, text, *_ = b
            if not text or len(text.strip()) < 3:
                continue
            text = normalize_text(text)
            lang = detect_language(text)
            if lang == "en":
                english_blocks.append(text)
            elif lang == "hi":
                hindi_blocks.append(text)
    doc.close()
    return " ".join(english_blocks), " ".join(hindi_blocks)


# ===============================================================
# Main Pipeline
# ===============================================================

def process_all_pdfs(data_dir, output_path):
    pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"❌ No PDFs found in {data_dir}")
        return

    print(f"📘 Found {len(pdf_files)} PDF(s) in {data_dir}")
    results = []

    for pdf_name in tqdm(pdf_files, desc="Processing PDFs"):
        pdf_path = os.path.join(data_dir, pdf_name)
        english_text, hindi_text = extract_text_by_language(pdf_path)

        topic = os.path.splitext(pdf_name)[0].replace("_Hindi", "")
        record = {
            "id": topic.lower(),
            "source_file": pdf_name,
            "english_char_count": len(english_text),
            "hindi_char_count": len(hindi_text),
            "english": english_text,
            "hindi": hindi_text,
            "metadata": {
                "extracted_from": pdf_path,
                "processing_stage": "preprocessed_batch"
            },
        }
        results.append(record)

    # Save as JSONL
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in results:
            json.dump(rec, f, ensure_ascii=False)
            f.write("\n")

    print(f"\n✅ Saved {len(results)} processed records to: {output_path}")
    print(f"   (Each line = 1 bilingual document record)\n")


# ===============================================================
# Run
# ===============================================================
if __name__ == "__main__":
    process_all_pdfs(DATA_DIR, OUTPUT_PATH)
