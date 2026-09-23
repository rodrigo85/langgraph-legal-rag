"""
Bronze Layer - Raw Data Ingestion (Multi-Document Landmark Lakehouse).
Handles idempotent download and integrity validation
of the official court documents in U.S. v. Google LLC (2020 to 2025):
1. Doc 1 (2020-10-20): DOJ Complaint
2. Doc 1033 (2024-08-05): Liability Ruling and Verdict (Memorandum Opinion)
3. Doc 1062-1 (2024-11-20): Proposed Remedies & Divestiture (Proposed Final Judgment)
"""

import sys
import urllib.request
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    BRONZE_RAW_DIR,
    OPINION_PDF_PATH,
    COMPLAINT_PDF_PATH,
    REMEDIES_PDF_PATH,
)

LANDMARK_REGISTRY: Dict[str, Dict[str, Any]] = {
    "doc1": {
        "title": "U.S. v. Google LLC - DOJ Complaint (Doc 1)",
        "docket_number": 1,
        "filing_date": "2020-10-20",
        "url": "https://www.justice.gov/atr/case-document/file/1329131/dl",
        "target_path": COMPLAINT_PDF_PATH,
        "trial_phase": "pre_trial",
    },
    "doc1033": {
        "title": "U.S. v. Google LLC - Memorandum Opinion (Doc 1033)",
        "docket_number": 1033,
        "filing_date": "2024-08-05",
        "url": "https://storage.courtlistener.com/recap/gov.uscourts.dcd.223205/gov.uscourts.dcd.223205.1033.0_5.pdf",
        "target_path": OPINION_PDF_PATH,
        "trial_phase": "verdict",
    },
    "doc1062": {
        "title": "U.S. v. Google LLC - Plaintiffs' Proposed Final Judgment on Remedies (Doc 1062-1)",
        "docket_number": 1062,
        "filing_date": "2024-11-20",
        "url": "https://www.justice.gov/atr/media/1378036/dl",
        "target_path": REMEDIES_PDF_PATH,
        "trial_phase": "remedies",
    },
}


def download_single_document(doc_info: Dict[str, Any]) -> Path:
    """Idempotent download with %PDF- magic-byte validation."""
    target_path = Path(doc_info["target_path"])
    url = doc_info["url"]
    title = doc_info["title"]
    
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.exists() and target_path.stat().st_size > 100_000:
        size_mb = target_path.stat().st_size / (1024 * 1024)
        print(f"[BRONZE] {title} already present: {target_path.name} ({size_mb:.2f} MB)")
        return target_path

    print(f"[BRONZE] Downloading: {title}")
    print(f"         URL: {url}")
    print(f"         Destination: {target_path.name}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DataEngineeringPipeline/1.0"
    }

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response, open(target_path, "wb") as out_file:
        total_size = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 64 * 1024

        while True:
            buffer = response.read(chunk_size)
            if not buffer:
                break
            downloaded += len(buffer)
            out_file.write(buffer)
            if total_size > 0:
                percent = (downloaded / total_size) * 100
                mb = downloaded / (1024 * 1024)
                sys.stdout.write(f"\r    [Progress] {percent:.1f}% ({mb:.2f} MB)")
                sys.stdout.flush()

    print("\n    [BRONZE] Download complete.")

    # File-format magic signature validation
    with open(target_path, "rb") as f:
        header = f.read(5)
        if header != b"%PDF-":
            raise ValueError(f"[DATA ERROR] Corrupted or invalid file. Header: {header}")

    size_mb = target_path.stat().st_size / (1024 * 1024)
    print(f"    [BRONZE] %PDF- signature validated successfully ({size_mb:.2f} MB).")
    return target_path


def download_court_opinion() -> Path:
    """Legacy function kept for backward compatibility."""
    return download_single_document(LANDMARK_REGISTRY["doc1033"])


def download_all_landmarks() -> Dict[str, Path]:
    """Downloads all landmark court documents into the Bronze layer."""
    print("=" * 70)
    print("BRONZE LAYER - LANDMARK DOCUMENT INGESTION (U.S. v. Google)")
    print("=" * 70)
    results = {}
    for doc_id, doc_info in LANDMARK_REGISTRY.items():
        results[doc_id] = download_single_document(doc_info)
    print("\n[OK] All Bronze-layer documents are ready and validated.")
    return results


if __name__ == "__main__":
    download_all_landmarks()
