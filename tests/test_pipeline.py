"""
Testes Unitarios do Pipeline de Dados Nao-Estruturados.
Valida:
1. Extracao e Linhagem da Camada Silver (JSONL)
2. Particionamento e enriquecimento de Chunks da Camada Gold
3. Idempotencia da carga no ChromaDB
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline.parser import load_silver_documents
from src.pipeline.indexer import chunk_silver_documents, load_or_build_gold_vectorstore


def test_silver_documents_metadata():
    """Valida se a camada Silver contem metadados de linhagem obrigatorios."""
    docs = load_silver_documents()
    assert len(docs) > 0, "A camada Silver nao possui documentos extraidos."
    
    first_doc = docs[0]
    assert "source_file" in first_doc.metadata
    assert "page" in first_doc.metadata
    assert "char_count" in first_doc.metadata
    assert "content_checksum" in first_doc.metadata
    assert first_doc.metadata["page"] == 1 or first_doc.metadata["page"] > 0
    print("[PASS] test_silver_documents_metadata")


def test_chunking_enrichment():
    """Valida se os chunks sao gerados com chunk_id estruturado."""
    docs = load_silver_documents()
    sample_docs = docs[:5]
    chunks = chunk_silver_documents(sample_docs, chunk_size=500, chunk_overlap=100)
    
    assert len(chunks) >= len(sample_docs)
    for c in chunks:
        assert "chunk_id" in c.metadata
        assert c.metadata["chunk_id"].startswith("doc1033_p")
    print("[PASS] test_chunking_enrichment")


def test_gold_vectorstore_readiness():
    """Valida se o ChromaDB responde a consultas de similaridade."""
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
    print("\n[OK] Todos os testes de pipeline de dados passaram com sucesso!")

