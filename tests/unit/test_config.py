"""Typed 12-factor settings: environment overrides, validation and secret masking."""

import pytest
from pydantic import SecretStr, ValidationError

from legal_rag.config import Settings, get_settings


def test_defaults_are_local_stack():
    s = Settings(_env_file=None)
    assert (s.llm_provider, s.embedding_provider, s.vector_store, s.dlq_backend) == (
        "ollama",
        "ollama",
        "chroma",
        "jsonl",
    )
    assert s.max_retries == 3


def test_env_overrides_produce_typed_settings(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")
    monkeypatch.setenv("VECTOR_STORE", "pgvector")
    monkeypatch.setenv("MAX_RETRIES", "5")
    monkeypatch.setenv("OTEL_ENABLED", "true")
    monkeypatch.setenv("PGVECTOR_DSN", "postgresql+psycopg://u:p@db:5432/rag")

    s = Settings(_env_file=None)

    assert s.llm_provider == "bedrock"
    assert s.vector_store == "pgvector"
    assert s.max_retries == 5
    assert s.otel_enabled is True
    assert isinstance(s.pgvector_dsn, SecretStr)
    assert s.pgvector_dsn.get_secret_value() == "postgresql+psycopg://u:p@db:5432/rag"


def test_env_names_are_case_insensitive(monkeypatch):
    monkeypatch.setenv("dlq_backend", "s3")
    assert Settings(_env_file=None).dlq_backend == "s3"


def test_get_settings_is_cached_and_reads_env(monkeypatch):
    monkeypatch.setenv("TOP_K_DOCUMENTS", "7")
    assert get_settings().top_k_documents == 7
    assert get_settings() is get_settings()


@pytest.mark.parametrize(
    ("var", "value"), [("LLM_PROVIDER", "openai"), ("VECTOR_STORE", "faiss"), ("MAX_RETRIES", "many")]
)
def test_invalid_values_raise(monkeypatch, var, value):
    monkeypatch.setenv(var, value)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_secrets_do_not_leak_in_repr(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "sk-super-secret")
    monkeypatch.setenv("API_KEY", "api-super-secret")
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "AccountKey=conn-super-secret")

    s = Settings(_env_file=None)
    rendered = repr(s) + str(s) + s.model_dump_json()

    for secret in ("sk-super-secret", "api-super-secret", "conn-super-secret", "rag:rag@"):
        assert secret not in rendered
    assert s.azure_openai_api_key.get_secret_value() == "sk-super-secret"
