"""
Camada Silver - Extracao, Limpeza e Enriquecimento de Metadados.
Transforma dados brutos (Bronze PDF) em registros estruturados de texto (Silver JSONL)
preservando linhagem completa de dados (page, char_count, document_title).
"""

import sys
import json
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any
import pypdf
from langchain_core.documents import Document

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import OPINION_PDF_PATH, SILVER_CORPUS_JSONL


import re

WITNESS_DATES = {
    "nadella": "2023-09-26",
    "cue": "2023-09-26",
    "pichai": "2023-10-05",
    "raghavan": "2023-10-18",
    "parakhin": "2023-09-21",
    "dischler": "2023-09-18",
    "varian": "2023-09-27",
    "brin": "2023-10-03",
    "harrison": "2023-09-25",
    "mccallister": "2023-09-20",
    "whinston": "2023-09-28",
    "murphy": "2023-10-24",
}


def extract_page_temporal_metadata(text: str, page_num: int) -> dict:
    """Extrai metadados temporais, linhagem de datas e testemunhas citadas na pagina."""
    years = [int(y) for y in re.findall(r"\b(199\d|20[0-2]\d)\b", text)]
    min_year = min(years) if years else 2020
    max_year = max(years) if years else 2024

    found_witnesses = []
    witness_dates = []
    for w, dt in WITNESS_DATES.items():
        if re.search(r"\b" + w + r"\b", text, re.IGNORECASE):
            found_witnesses.append(w.capitalize())
            witness_dates.append(dt)

    if witness_dates:
        disclosure_date = min(witness_dates)
        trial_phase = "trial"
    elif "Tr. at" in text or "Trial Tr." in text or "UPX" in text:
        disclosure_date = "2023-10-15"
        trial_phase = "trial"
    elif page_num <= 40:
        disclosure_date = "2020-10-20"
        trial_phase = "pre_trial"
    else:
        disclosure_date = "2024-08-05"
        trial_phase = "verdict"

    disc_int = int(disclosure_date.replace("-", ""))
    filing_int = 20240805

    return {
        "event_year_min": min_year,
        "event_year_max": max_year,
        "witnesses": ",".join(sorted(found_witnesses)),
        "disclosure_date": disclosure_date,
        "disclosure_date_int": disc_int,
        "filing_date": "2024-08-05",
        "filing_date_int": filing_int,
        "trial_phase": trial_phase,
    }


from src.pipeline.downloader import LANDMARK_REGISTRY


def parse_and_clean_pdf(
    pdf_path: Optional[Path] = None,
    output_jsonl: Path = SILVER_CORPUS_JSONL
) -> List[Document]:
    """
    Processa todos os documentos marcos (Doc 1, Doc 1033, Doc 1062) presentes na camada Bronze,
    extrai metadados temporais e grava na camada Silver consolidada (JSONL).
    """
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    all_silver_docs: List[Document] = []
    all_jsonl_records = []

    # Se um PDF específico foi solicitado
    target_registry = dict(LANDMARK_REGISTRY)
    if pdf_path:
        target_registry = {
            "custom": {
                "title": f"Documento {pdf_path.name}",
                "docket_number": 1033,
                "filing_date": "2024-08-05",
                "target_path": pdf_path,
                "trial_phase": "verdict",
            }
        }

    for doc_key, doc_info in target_registry.items():
        doc_path = Path(doc_info["target_path"])
        if not doc_path.exists():
            print(f"[SILVER Alerta] Documento {doc_key} nao encontrado em: {doc_path.name}. Pulando.")
            continue

        print(f"[SILVER] Processando marco judicial [{doc_key}]: {doc_info['title']}")
        reader = pypdf.PdfReader(str(doc_path))
        total_raw_pages = len(reader.pages)
        docket_num = doc_info.get("docket_number", 1033)

        doc_pages_processed = 0
        for page_idx, page in enumerate(reader.pages, start=1):
            raw_text = page.extract_text() or ""
            clean_text = "\n".join([line.strip() for line in raw_text.splitlines() if line.strip()])
            
            # Filtro de qualidade de dados: ignorar paginas sem conteudo substancial
            if len(clean_text) < 50:
                continue

            page_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()[:16]
            temporal_meta = extract_page_temporal_metadata(clean_text, page_idx)
            
            # Metadados especificos do docket
            if docket_num == 1:
                temporal_meta["filing_date"] = "2020-10-20"
                temporal_meta["filing_date_int"] = 20201020
                temporal_meta["disclosure_date"] = "2020-10-20"
                temporal_meta["disclosure_date_int"] = 20201020
                temporal_meta["trial_phase"] = "pre_trial"
            elif docket_num == 1062:
                temporal_meta["filing_date"] = "2024-11-20"
                temporal_meta["filing_date_int"] = 20241120
                temporal_meta["disclosure_date"] = "2024-11-20"
                temporal_meta["disclosure_date_int"] = 20241120
                temporal_meta["trial_phase"] = "remedies"

            metadata = {
                "source_file": doc_path.name,
                "docket_number": docket_num,
                "document_title": doc_info["title"],
                "page": page_idx,
                "total_pages": total_raw_pages,
                "char_count": len(clean_text),
                "content_checksum": page_hash,
                **temporal_meta
            }

            doc = Document(page_content=clean_text, metadata=metadata)
            all_silver_docs.append(doc)
            doc_pages_processed += 1

            all_jsonl_records.append({
                "page": page_idx,
                "content": clean_text,
                "metadata": metadata
            })

        print(f"    [SILVER] {doc_pages_processed}/{total_raw_pages} paginas extraidas com sucesso.")

    # Persistir camada Silver consolidada em JSONL
    with open(output_jsonl, "w", encoding="utf-8") as f:
        for record in all_jsonl_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"[SILVER] Total consolidado: {len(all_silver_docs)} paginas persistidas em: {output_jsonl.name}")
    return all_silver_docs


def load_silver_documents(silver_jsonl: Path = SILVER_CORPUS_JSONL) -> List[Document]:
    """
    Carrega rapidamente os documentos pre-processados da camada Silver.
    Se nao existir, executa o parser automaticamente.
    """
    if not silver_jsonl.exists():
        return parse_and_clean_pdf()

    docs = []
    with open(silver_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            docs.append(Document(page_content=data["content"], metadata=data["metadata"]))
    
    return docs


if __name__ == "__main__":
    parse_and_clean_pdf()

