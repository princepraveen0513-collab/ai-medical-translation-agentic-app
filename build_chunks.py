import os
import re
import json
from pathlib import Path

import fitz  # PyMuPDF
import pandas as pd
from langdetect import detect
from langchain_text_splitters import RecursiveCharacterTextSplitter



# =========================
# Paths
# =========================
BASE_DIR = Path(__file__).resolve().parent
BILINGUAL_DIR = BASE_DIR / "data" / "bilingual"
CS_JSON_PATH = BASE_DIR / "data" / "cultural_semantics" / "data.json"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)


# =========================
# Helpers: Bilingual PDFs
# =========================

def extract_blocks(pdf_path: Path):
    """
    Extract text spans with coordinates and font info.
    Returns sorted list of {text, x0, y0, font}.
    """
    blocks_all = []
    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            page_dict = page.get_text("dict")
            for block in page_dict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        txt = span.get("text", "").strip()
                        if not txt:
                            continue
                        x0, y0, _, _ = span["bbox"]
                        blocks_all.append({
                            "text": txt,
                            "x0": x0,
                            "y0": y0,
                            "font": span.get("font", ""),
                            "page": page_num,
                        })
    # sort: top-to-bottom, left-to-right
    blocks_all.sort(key=lambda b: (b["page"], b["y0"], b["x0"]))
    return blocks_all


def detect_language(text: str) -> str:
    """
    Rough language detection: Hindi via Unicode, else langdetect fallback.
    """
    if re.search(r'[\u0900-\u097F]', text):
        return "hi"
    try:
        lang = detect(text)
        if lang.startswith("hi"):
            return "hi"
        if lang.startswith("en"):
            return "en"
        return "en"
    except Exception:
        return "en"


def align_blocks(blocks, y_tolerance: float = 120.0):
    """
    Align English and Hindi spans by vertical proximity.
    Produces list of (en_text, hi_text, meta) pairs.
    meta will track pages / positions for traceability.
    """
    pairs = []
    pending_en = None

    for b in blocks:
        lang = detect_language(b["text"])
        if lang == "en":
            # flush any previous pending_en as orphan if never paired
            if pending_en:
                pairs.append((pending_en["text"], "", {
                    "page_en": pending_en["page"],
                    "page_hi": None
                }))
            pending_en = b

        elif lang == "hi":
            if pending_en and b["page"] == pending_en["page"] and abs(b["y0"] - pending_en["y0"]) <= y_tolerance:
                # good alignment
                pairs.append((pending_en["text"], b["text"], {
                    "page_en": pending_en["page"],
                    "page_hi": b["page"]
                }))
                pending_en = None
            else:
                # orphan Hindi
                pairs.append(("", b["text"], {
                    "page_en": None,
                    "page_hi": b["page"]
                }))

    # if last EN never got a pair
    if pending_en:
        pairs.append((pending_en["text"], "", {
            "page_en": pending_en["page"],
            "page_hi": None
        }))

    return pairs


def create_bilingual_chunks(pairs, source_name: str):
    """
    Turn aligned (EN, HI) pairs into larger chunks using RecursiveCharacterTextSplitter.
    Each chunk will contain some EN/HI pairs and metadata.
    """
    formatted_blocks = []
    meta_map = []

    for en, hi, meta in pairs:
        if not en and not hi:
            continue
        block_text = ""
        if en:
            block_text += f"EN: {en}"
        if hi:
            block_text += ("\n" if block_text else "") + f"HI: {hi}"
        formatted_blocks.append(block_text)
        meta_map.append(meta)

    if not formatted_blocks:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", "!", "?"]
    )

    docs = splitter.create_documents(formatted_blocks)

    chunks = []
    for i, d in enumerate(docs, start=1):
        text = d.page_content.strip()
        has_en = "EN:" in text
        has_hi = "HI:" in text
        alignment_status = "perfect" if has_en and has_hi else "partial"

        chunks.append({
            "chunk_id": f"{source_name}_chunk_{i}",
            "source": source_name,
            "language": "hi-en",
            "alignment_status": alignment_status,
            "length": len(text),
            "text": text
        })

    return chunks


def process_bilingual_pdfs():
    all_chunks = []

    if not BILINGUAL_DIR.exists():
        print(f"[WARN] Bilingual dir not found: {BILINGUAL_DIR}")
        return all_chunks

    pdf_paths = sorted(BILINGUAL_DIR.glob("*.pdf"))
    if not pdf_paths:
        print(f"[WARN] No PDFs found in {BILINGUAL_DIR}")
        return all_chunks

    for pdf_path in pdf_paths:
        source_name = pdf_path.stem
        print(f"\n📘 Processing bilingual PDF: {pdf_path.name}")
        blocks = extract_blocks(pdf_path)
        print(f"  - Extracted {len(blocks)} spans")
        pairs = align_blocks(blocks)
        print(f"  - Built {len(pairs)} EN/HI pairs (incl. partial/orphans)")
        chunks = create_bilingual_chunks(pairs, source_name)
        print(f"  - Created {len(chunks)} chunks")
        all_chunks.extend(chunks)

    # Save outputs
    if all_chunks:
        df = pd.DataFrame(all_chunks)
        csv_path = ARTIFACTS_DIR / "bilingual_chunks.csv"
        jsonl_path = ARTIFACTS_DIR / "bilingual_chunks.jsonl"

        df.to_csv(csv_path, index=False, encoding="utf-8")
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for row in all_chunks:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        print(f"\n✅ Bilingual chunks saved:")
        print(f"   - CSV:   {csv_path}")
        print(f"   - JSONL: {jsonl_path}")

        print("\n🔍 Sample bilingual chunks:")
        print(df[["chunk_id", "source", "alignment_status", "length"]].head(10).to_string(index=False))

    return all_chunks


# =========================
# Helpers: Cultural Semantics JSON
# =========================

def load_cultural_semantics():
    if not CS_JSON_PATH.exists():
        print(f"[WARN] Cultural semantics JSON not found: {CS_JSON_PATH}")
        return []

    with open(CS_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("entries", [])
    records = []

    for entry in entries:
        en_id = entry.get("id")
        native = entry.get("expression_native", "")
        translit = entry.get("expression_translit", "")
        literal = entry.get("literal_translation", "")
        clinical = entry.get("clinical_meaning", "")
        context = entry.get("cultural_context", "")
        synonyms = entry.get("synonyms_variants", [])
        disamb = entry.get("disambiguation_questions", [])
        category = entry.get("category", "")
        severity = entry.get("severity_hint", "")
        risk_flag = entry.get("risk_flag", False)
        lang_pair = entry.get("language_pair", "hi-en")

        canonical_text = (
            f"{native} ({translit})\n"
            f"Literal: {literal}\n"
            f"Meaning: {clinical}\n"
            f"Cultural context: {context}\n"
            f"Synonyms/variants: {', '.join(synonyms) if synonyms else 'N/A'}\n"
            f"Disambiguation questions: { ' | '.join(disamb) if disamb else 'N/A' }"
        ).strip()

        rec = {
            "id": en_id,
            "text": canonical_text,
            "metadata": {
                "source": "cultural_semantics",
                "language_pair": lang_pair,
                "category": category,
                "severity_hint": severity,
                "risk_flag": risk_flag,
            }
        }
        records.append(rec)

    # Save outputs
    if records:
        csv_path = ARTIFACTS_DIR / "cultural_semantics_entries.csv"
        jsonl_path = ARTIFACTS_DIR / "cultural_semantics_entries.jsonl"

        df = pd.DataFrame([
            {
                "id": r["id"],
                "text": r["text"],
                **r["metadata"]
            }
            for r in records
        ])
        df.to_csv(csv_path, index=False, encoding="utf-8")

        with open(jsonl_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        print(f"\n✅ Cultural semantics records saved:")
        print(f"   - CSV:   {csv_path}")
        print(f"   - JSONL: {jsonl_path}")

        print("\n🔍 Sample cultural semantics entries:")
        print(df[["id", "category", "risk_flag"]].head(10).to_string(index=False))

    return records


# =========================
# Main
# =========================

if __name__ == "__main__":
    print("🚀 Building chunks from bilingual PDFs and cultural semantics JSON...\n")
    bilingual_chunks = process_bilingual_pdfs()
    cs_records = load_cultural_semantics()
    print("\n🎉 Done. Inspect the 'artifacts' folder for outputs.\n")
