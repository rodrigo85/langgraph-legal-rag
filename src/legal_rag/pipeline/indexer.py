"""
Gold Layer - Semantic Chunking and Vector Lake Load.
Runs the Silver -> Gold transformation:
1. Semantic text partitioning (RecursiveCharacterTextSplitter)
2. Preservation and propagation of lineage metadata (page, source_file, chunk_id)
3. Idempotent load into the configured vector store (ChromaDB locally, pgvector in the cloud).
"""

import logging
from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from legal_rag.config import CHUNK_OVERLAP, CHUNK_SIZE, settings
from legal_rag.pipeline.parser import load_silver_documents
from legal_rag.storage.vector_store import count_vectors, get_vector_store, reset_collection

logger = logging.getLogger(__name__)


def chunk_silver_documents(
    silver_docs: List[Document],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> List[Document]:
    """
    Splits Silver-layer documents into chunks calibrated for legal documents.
    Generates granular lineage metadata for each chunk.
    """
    logger.info("gold.chunking", extra={"chunk_size": chunk_size, "chunk_overlap": chunk_overlap})
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    
    raw_chunks = splitter.split_documents(silver_docs)
    enriched_chunks: List[Document] = []

    for idx, chunk in enumerate(raw_chunks, start=1):
        meta = dict(chunk.metadata)
        docket_tag = f"doc{meta.get('docket_number', 1033)}"
        meta["chunk_id"] = f"{docket_tag}_p{meta.get('page', 0)}_c{idx}"
        enriched_chunks.append(Document(page_content=chunk.page_content, metadata=meta))

    logger.info("gold.chunks_generated", extra={"chunks": len(enriched_chunks)})
    return enriched_chunks


def load_or_build_gold_vectorstore(
    chunks: Optional[List[Document]] = None,
    force_reindex: bool = False,
) -> VectorStore:
    """
    Idempotent load into the Gold layer:
    If the collection already exists and contains vectors, it is reused without reprocessing.
    If force_reindex=True or the collection is empty, embeddings are generated and indexed.
    """
    vector_store = get_vector_store()

    existing_count = count_vectors(vector_store)
    if existing_count > 0 and not force_reindex:
        logger.info("gold.ready", extra={"vectors": existing_count, "backend": settings.vector_store})
        return vector_store

    if existing_count > 0 and force_reindex:
        logger.info("gold.reindex", extra={"vectors": existing_count, "collection": settings.collection_name})
        vector_store = reset_collection(vector_store)

    if chunks is None:
        silver_docs = load_silver_documents()
        chunks = chunk_silver_documents(silver_docs)

    logger.info("gold.indexing", extra={"chunks": len(chunks), "backend": settings.vector_store})
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        batch_ids = [c.metadata.get("chunk_id", f"chunk_{i + j}") for j, c in enumerate(batch)]
        vector_store.add_documents(batch, ids=batch_ids)
        logger.info("gold.batch_indexed", extra={"done": min(i + batch_size, len(chunks)), "total": len(chunks)})

    logger.info("gold.load_completed", extra={"collection": settings.collection_name})
    return vector_store


def get_temporal_retriever(
    as_of_date: Optional[str] = None,
    k: int = 4,
    vector_store: Optional[VectorStore] = None,
):
    """
    Returns the Gold-layer vector retriever with a Point-in-Time filter.
    If as_of_date is provided (e.g. '2023-09-26'), only chunks with
    disclosure_date <= as_of_date are returned, preserving integrity and preventing lookahead bias.
    """
    if vector_store is None:
        vector_store = load_or_build_gold_vectorstore()

    if as_of_date:
        as_of_int = int(as_of_date.replace("-", ""))
        filter_expr = {"disclosure_date_int": {"$lte": as_of_int}}
        return vector_store.as_retriever(search_kwargs={"k": k, "filter": filter_expr})

    return vector_store.as_retriever(search_kwargs={"k": k})


if __name__ == "__main__":
    from legal_rag.observability import configure_logging

    configure_logging()
    load_or_build_gold_vectorstore()
