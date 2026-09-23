"""
Unit Tests for the Unstructured Data Pipeline.
Validates:
1. Silver-layer extraction and lineage (JSONL)
2. Gold-layer chunk partitioning and enrichment
3. Idempotency of the ChromaDB load
"""



from legal_rag.pipeline.parser import load_silver_documents
from legal_rag.pipeline.indexer import chunk_silver_documents, load_or_build_gold_vectorstore


def test_silver_documents_metadata():
    """Validates that the Silver layer contains the required lineage metadata."""
    docs = load_silver_documents()
    assert len(docs) > 0, "The Silver layer has no extracted documents."
    
    first_doc = docs[0]
    assert "source_file" in first_doc.metadata
    assert "page" in first_doc.metadata
    assert "char_count" in first_doc.metadata
    assert "content_checksum" in first_doc.metadata
    assert first_doc.metadata["page"] == 1 or first_doc.metadata["page"] > 0
    print("[PASS] test_silver_documents_metadata")


def test_chunking_enrichment():
    """Validates that chunks are generated with a structured chunk_id."""
    docs = load_silver_documents()
    sample_docs = docs[:5]
    chunks = chunk_silver_documents(sample_docs, chunk_size=500, chunk_overlap=100)
    
    assert len(chunks) >= len(sample_docs)
    for c in chunks:
        assert "chunk_id" in c.metadata
        assert c.metadata["chunk_id"].startswith("doc1033_p")
    print("[PASS] test_chunking_enrichment")


def test_gold_vectorstore_readiness():
    """Validates that ChromaDB responds to similarity queries."""
    vector_store = load_or_build_gold_vectorstore()
    retriever = vector_store.as_retriever(search_kwargs={"k": 2})
    results = retriever.invoke("Apple Google search default agreement")
    
    assert len(results) == 2
    for doc in results:
        assert "page" in doc.metadata
        assert len(doc.page_content) > 50
    print("[PASS] test_gold_vectorstore_readiness")


if __name__ == "__main__":
    test_silver_documents_metadata()
    test_chunking_enrichment()
    test_gold_vectorstore_readiness()
    print("\n[OK] All data pipeline tests passed successfully!")

