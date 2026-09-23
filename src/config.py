import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# 1. Project Paths & Medallion Architecture
# ==============================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Bronze layer: immutable raw data
BRONZE_RAW_DIR = PROJECT_ROOT / "data" / "raw"
OPINION_PDF_PATH = BRONZE_RAW_DIR / "us_v_google_opinion_1033.pdf"
COMPLAINT_PDF_PATH = BRONZE_RAW_DIR / "us_v_google_complaint_doc1.pdf"
REMEDIES_PDF_PATH = BRONZE_RAW_DIR / "us_v_google_remedies_doc1062.pdf"

# Silver layer: processed, cleaned, metadata-enriched data
SILVER_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SILVER_CORPUS_JSONL = SILVER_PROCESSED_DIR / "opinion_pages.jsonl"

# Gold layer: vector store indexed for semantic search
GOLD_CHROMA_DIR = PROJECT_ROOT / "chroma_db"
GOLD_COLLECTION_NAME = "antitrust_google_opinion"

# Evaluation dataset (golden benchmark)
SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"
BENCHMARK_DATASET_PATH = SAMPLES_DIR / "qa_benchmark.json"

# Observability and Dead-Letter Queue (DLQ) for hallucination auditing
DATA_LOGS_DIR = PROJECT_ROOT / "data" / "logs"
HALLUCINATIONS_LOG_PATH = DATA_LOGS_DIR / "hallucination_incidents.jsonl"

# ==============================================================================
# 2. Model Settings (Local Ollama / RTX GPU)
# ==============================================================================
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "antitrust-specialist-v2")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "24h")  # Keep the model resident in GPU VRAM for 24h without unloading

# ==============================================================================
# 3. Data Engineering & RAG Hyperparameters
# ==============================================================================
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
TOP_K_DOCUMENTS = int(os.getenv("TOP_K_DOCUMENTS", "4"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
