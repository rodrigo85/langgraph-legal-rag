"""
Centralized, typed configuration (12-factor).

Every value can be overridden through environment variables (or a local `.env`).
In the cloud, secrets are injected as environment variables by the platform
(AWS Secrets Manager -> ECS task secrets, Azure Key Vault -> Container Apps secretRef),
so the application code never talks to a secret store directly.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_APP_HOME = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Paths -----------------------------------------------------------------
    app_home: Path = Field(default=_DEFAULT_APP_HOME, description="Root folder holding data/ and reports/")

    # --- LLM / embedding providers -----------------------------------------------
    llm_provider: Literal["ollama", "bedrock", "azure_openai"] = "ollama"
    embedding_provider: Literal["ollama", "bedrock", "azure_openai"] = "ollama"

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_llm_model: str = "antitrust-specialist-v2"
    ollama_embed_model: str = "nomic-embed-text:latest"
    ollama_keep_alive: str = "24h"

    aws_region: str = "us-east-1"
    bedrock_llm_model_id: str = "anthropic.claude-opus-5"  # exact ID / inference profile depends on the AWS region
    bedrock_embed_model_id: str = "amazon.titan-embed-text-v2:0"

    azure_openai_endpoint: Optional[str] = None
    azure_openai_api_key: Optional[SecretStr] = None
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_chat_deployment: str = "gpt-4o-mini"
    azure_openai_embed_deployment: str = "text-embedding-3-small"

    # --- Vector store (Gold layer) -----------------------------------------------
    vector_store: Literal["chroma", "pgvector"] = "chroma"
    collection_name: str = "antitrust_google_opinion"
    pgvector_dsn: SecretStr = SecretStr("postgresql+psycopg://rag:rag@localhost:5432/rag")

    # --- Dead-letter queue for hallucination incidents ---------------------------
    dlq_backend: Literal["jsonl", "s3", "azure_blob"] = "jsonl"
    dlq_s3_bucket: str = "legal-rag-dlq"
    aws_endpoint_url: Optional[str] = Field(default=None, description="LocalStack endpoint for local simulation")
    dlq_azure_container: str = "legal-rag-dlq"
    azure_storage_connection_string: Optional[SecretStr] = None

    # --- RAG hyperparameters -----------------------------------------------------
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k_documents: int = 4
    max_retries: int = 3

    # --- API & observability -----------------------------------------------------
    api_key: Optional[SecretStr] = Field(default=None, description="If set, required in the X-API-Key header")
    request_timeout_seconds: int = 180
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "text"
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    otel_service_name: str = "legal-rag-api"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# ==============================================================================
# Derived paths (Medallion architecture) and module-level aliases
# ==============================================================================
PROJECT_ROOT = settings.app_home
PACKAGE_DIR = Path(__file__).resolve().parent

# Bronze layer: immutable raw data
BRONZE_RAW_DIR = PROJECT_ROOT / "data" / "raw"
OPINION_PDF_PATH = BRONZE_RAW_DIR / "us_v_google_opinion_1033.pdf"
COMPLAINT_PDF_PATH = BRONZE_RAW_DIR / "us_v_google_complaint_doc1.pdf"
REMEDIES_PDF_PATH = BRONZE_RAW_DIR / "us_v_google_remedies_doc1062.pdf"
DOCKETS_REGISTRY_PATH = PROJECT_ROOT / "data" / "metadata" / "dockets_registry.json"

# Silver layer: processed, cleaned, metadata-enriched data
SILVER_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SILVER_CORPUS_JSONL = SILVER_PROCESSED_DIR / "opinion_pages.jsonl"

# Gold layer: vector store indexed for semantic search
GOLD_CHROMA_DIR = PROJECT_ROOT / "chroma_db"
GOLD_COLLECTION_NAME = settings.collection_name

# Evaluation dataset (golden benchmark), training datasets and reports
SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"
BENCHMARK_DATASET_PATH = SAMPLES_DIR / "qa_benchmark.json"
TRAINING_DATA_DIR = PROJECT_ROOT / "data" / "training"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Dead-Letter Queue (DLQ) for hallucination auditing (jsonl backend)
DATA_LOGS_DIR = PROJECT_ROOT / "data" / "logs"
HALLUCINATIONS_LOG_PATH = DATA_LOGS_DIR / "hallucination_incidents.jsonl"

# Model settings
OLLAMA_BASE_URL = settings.ollama_base_url
OLLAMA_LLM_MODEL = settings.ollama_llm_model
OLLAMA_EMBED_MODEL = settings.ollama_embed_model
OLLAMA_KEEP_ALIVE = settings.ollama_keep_alive  # Keep the model resident in GPU VRAM

# Data engineering & RAG hyperparameters
CHUNK_SIZE = settings.chunk_size
CHUNK_OVERLAP = settings.chunk_overlap
TOP_K_DOCUMENTS = settings.top_k_documents
MAX_RETRIES = settings.max_retries
