import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# 1. Caminhos do Projeto & Arquitetura Medallion
# ==============================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Camada Bronze: Dados brutos imutáveis
BRONZE_RAW_DIR = PROJECT_ROOT / "data" / "raw"
OPINION_PDF_PATH = BRONZE_RAW_DIR / "us_v_google_opinion_1033.pdf"
COMPLAINT_PDF_PATH = BRONZE_RAW_DIR / "us_v_google_complaint_doc1.pdf"
REMEDIES_PDF_PATH = BRONZE_RAW_DIR / "us_v_google_remedies_doc1062.pdf"

# Camada Silver: Dados processados, limpos e enriquecidos com metadados
SILVER_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SILVER_CORPUS_JSONL = SILVER_PROCESSED_DIR / "opinion_pages.jsonl"

# Camada Gold: Vector Store indexado para busca semântica
GOLD_CHROMA_DIR = PROJECT_ROOT / "chroma_db"
GOLD_COLLECTION_NAME = "antitrust_google_opinion"

# Dataset de Avaliação (Golden benchmark)
SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"
BENCHMARK_DATASET_PATH = SAMPLES_DIR / "qa_benchmark.json"

# Observabilidade e Dead-Letter Queue (DLQ) para Auditoria de Alucinações
DATA_LOGS_DIR = PROJECT_ROOT / "data" / "logs"
HALLUCINATIONS_LOG_PATH = DATA_LOGS_DIR / "hallucination_incidents.jsonl"

# ==============================================================================
# 2. Configurações de Modelos (Ollama Local / GPU RTX)
# ==============================================================================
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "antitrust-specialist-v2")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "24h")  # Trava 24h na VRAM da GPU sem descarregar

# ==============================================================================
# 3. Hiperparâmetros de Engenharia de Dados & RAG
# ==============================================================================
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
TOP_K_DOCUMENTS = int(os.getenv("TOP_K_DOCUMENTS", "4"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
