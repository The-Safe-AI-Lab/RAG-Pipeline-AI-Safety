#!/usr/bin/env python3
# pip install wikipedia-api tqdm orjson

import re, uuid, pathlib, orjson
from tqdm import tqdm
import wikipediaapi

# ---------------------------
# CONFIG
# ---------------------------
LANG = "en"
OUT_PATH = "wiki_domain_top3paras.jsonl"
TOP_N_PARAS = 3

# Only three domains: legal, cybersecurity, finance
DOMAIN_SEEDS = {
    "legal": [
        "Caselaw Access Project", "PACER", "United States Code",
        "Code of Federal Regulations", "Court opinion", "Case citation"
    ],
    "cybersecurity": [
        "MITRE ATT&CK", "Common Vulnerabilities and Exposures", "Zero-day (computing)",
        "Malware", "Penetration test", "Intrusion detection system"
    ],
    "finance": [
        "EDGAR", "SEC filing", "Form 10-K", "Form 10-Q",
        "International Securities Identification Number", "Fama–French three-factor model"
    ],
}

# ---------------------------
# HELPERS
# ---------------------------
def clean(txt: str) -> str:
    # collapse whitespace and strip footnote markers like [1], [2] (simple heuristic)
    txt = re.sub(r"\s+", " ", txt).strip()
    txt = re.sub(r"\[\d+\]", "", txt)
    return txt

def top_paragraphs(full_text: str, n: int = TOP_N_PARAS):
    """
    Return the first n non-empty paragraphs from the lead of the page.
    wikipedia-api's page.text is plain text with paragraphs separated by blank lines.
    """
    # Split on blank lines, keep non-empty
    paras = [p.strip() for p in re.split(r"\n\s*\n", full_text) if p.strip()]
    # Take the first n
    return paras[:n]

def write_jsonl(records, path):
    with open(path, "wb") as f:
        for r in records:
            f.write(orjson.dumps(r) + b"\n")

# ---------------------------
# MAIN
# ---------------------------
def build_wiki_top3_paras(domain_to_titles=DOMAIN_SEEDS, out_path=OUT_PATH):
    wiki = wikipediaapi.Wikipedia(
        language=LANG,
        user_agent="RAG-Corpus-Builder/0.2 (academic)",
        extract_format=wikipediaapi.ExtractFormat.WIKI
    )
    out = []
    for domain, titles in domain_to_titles.items():
        print(f"\n== {domain.upper()} ==")
        for title in tqdm(titles):
            page = wiki.page(title)
            if not page.exists():
                # soft fallback: try capitalized title
                alt = wiki.page(title.capitalize())
                if not alt.exists():
                    print(f"  ! missing: {title}")
                    continue
                page = alt

            url = page.fullurl
            # Use the full text and extract the first N paragraphs
            paras = top_paragraphs(page.text, n=TOP_N_PARAS)
            if not paras:
                continue

            for i, para in enumerate(paras):
                text = clean(para)
                if not text or len(text.split()) < 20:
                    # skip trivially short paragraphs
                    continue
                out.append({
                    "id": str(uuid.uuid4()),
                    "domain": domain,
                    "title": page.title,
                    "section": "lead",          # we're taking from the lead
                    "para_index": i,            # 0,1,2 (top-3)
                    "url": url,
                    "contents": text,           # keep 'contents' for Pyserini compatibility
                    "source": "wikipedia",
                })

    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(out, out_path)
    print(f"\nWrote {len(out):,} paragraphs → {out_path}")

if __name__ == "__main__":
    build_wiki_top3_paras()