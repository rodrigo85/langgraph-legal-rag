"""
Integration tests for the unstructured data pipeline (requires the Silver corpus and an indexed Gold layer).
Validates:
1. Silver-layer extraction and lineage (JSONL)
2. Gold-layer chunk partitioning and enrichment
3. Readiness of the Gold-layer vector store
"""

import pytest

from legal_rag.pipeline.indexer import chunk_silver_documents, load_or_build_gold_vectorstore
from legal_rag.pipeline.parser import load_silver_documents

pytestmark = pytest.mark.integration


def test_silver_documents_metadata():
    """Validates that the Silver layer contains the required lineage metadata."""
    docs = load_silver_documents()
    assert len(docs) > 0, "The Silver layer has no extracted documents."

    first_doc = docs[0]
    assert "source_file" in first_doc.metadata
    assert "page" in first_doc.metadata
    assert "char_count" in first_doc.metadata
    assert "content_checksum" in first_doc.metadata
    assert first_doc.metadata["page"] > 0


def test_chunking_enrichment():
    """Validates that chunks are generated with a structured, docket-scoped chunk_id."""
    docs = load_silver_documents()
    sample_docs = docs[:5]
    chunks = chunk_silver_documents(sample_docs, chunk_size=500, chunk_overlap=100)

    assert len(chunks) >= len(sample_docs)
    for c in chunks:
        assert "chunk_id" in c.metadata
        docket = c.metadata.get("docket_number", 1033)
        assert c.metadata["chunk_id"].startswith(f"doc{docket}_p")


def test_gold_vectorstore_readiness():
    """Validates that the vector store responds to similarity queries."""
    vector_store = load_or_build_gold_vectorstore()
    retriever = vector_store.as_retriever(search_kwargs={"k": 2})
    results = retriever.invoke("Apple Google search default agreement")

    assert len(results) == 2
    for doc in results:
        assert "page" in doc.metadata
        assert len(doc.page_content) > 50
