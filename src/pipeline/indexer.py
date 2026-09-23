"""
Camada Gold - Chunking Semantico e Carga no Vector Lake.
Executa a transformacao Silver -> Gold:
1. Particionamento semantico de texto (RecursiveCharacterTextSplitter)
2. Preservacao e propagacao de metadados de linhagem (page, source_file, chunk_id)
3. Carga idempotente no ChromaDB com embeddings vetoriais (nomic-embed-text).
"""

import sys
from pathlib import Path
from typing import List, Optional
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

from langchain_ollama import OllamaEmbeddings
from src.config import (
    GOLD_CHROMA_DIR,
    GOLD_COLLECTION_NAME,
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)
from src.pipeline.parser import load_silver_documents


def get_embedding_function() -> OllamaEmbeddings:
    """Retorna a funcao de embeddings configurada."""
    return OllamaEmbeddings(
        model=OLLAMA_EMBED_MODEL,
        base_url=OLLAMA_BASE_URL,
    )


def chunk_silver_documents(
    silver_docs: List[Document],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> List[Document]:
    """
    Particiona documentos da camada Silver em chunks calibrados para contratos legais.
    Gera metadados granulares de linhagem para cada chunk.
    """
    print(f"[GOLD] Iniciando chunking semantico (size={chunk_size}, overlap={chunk_overlap})...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    
    raw_chunks = splitter.split_documents(silver_docs)
    enriched_chunks: List[Document] = []

    for idx, chunk in enumerate(raw_chunks, start=1):
        meta = dict(chunk.metadata)
        meta["chunk_id"] = f"doc1033_p{meta.get('page', 0)}_c{idx}"
        enriched_chunks.append(Document(page_content=chunk.page_content, metadata=meta))

    print(f"[GOLD] Total de chunks enriquecidos gerados: {len(enriched_chunks)}")
    return enriched_chunks


def load_or_build_gold_vectorstore(
    chunks: Optional[List[Document]] = None,
    persist_dir: Path = GOLD_CHROMA_DIR,
    collection_name: str = GOLD_COLLECTION_NAME,
    force_reindex: bool = False,
) -> Chroma:
    """
    Carga idempotente na camada Gold:
    Se a colecao ja existir e contiver vetores, reutiliza diretamente sem reprocessar.
    Se force_reindex=True ou estiver vazia, gera embeddings e indexa.
    """
    embeddings = get_embedding_function()
    persist_dir.mkdir(parents=True, exist_ok=True)

    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )

    existing_count = vector_store._collection.count()
    if existing_count > 0 and not force_reindex:
        print(f"[GOLD] Vector Lake operacional com {existing_count} vetores indexados em: {persist_dir.name}")
        return vector_store

    if existing_count > 0 and force_reindex:
        print(f"[GOLD] Reindexacao forcada: resetando colecao '{collection_name}' ({existing_count} vetores)...")
        vector_store._client.delete_collection(collection_name)
        vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=str(persist_dir),
        )

    if chunks is None:
        silver_docs = load_silver_documents()
        chunks = chunk_silver_documents(silver_docs)

    print(f"[GOLD] Indexando {len(chunks)} chunks no ChromaDB com IDs deterministicos...")
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        batch_ids = [c.metadata.get("chunk_id", f"doc1033_chunk_{i+j}") for j, c in enumerate(batch)]
        vector_store.add_documents(batch, ids=batch_ids)
        print(f"    [GOLD] Lote indexado: {min(i + batch_size, len(chunks))}/{len(chunks)}")

    print(f"[GOLD] Carga concluida com sucesso. Colecao '{collection_name}' ativa.")
    return vector_store


def get_temporal_retriever(
    as_of_date: Optional[str] = None,
    k: int = 4,
    vector_store: Optional[Chroma] = None,
):
    """
    Retorna o retriever vetorial da camada Gold com filtro Point-in-Time.
    Se as_of_date for fornecido (ex: '2023-09-26'), filtra apenas chunks com
    disclosure_date <= as_of_date, garantindo integridade e prevenindo Lookahead Bias.
    """
    if vector_store is None:
        vector_store = load_or_build_gold_vectorstore()

    if as_of_date:
        as_of_int = int(as_of_date.replace("-", ""))
        filter_expr = {"disclosure_date_int": {"$lte": as_of_int}}
        return vector_store.as_retriever(
            search_kwargs={"k": k, "filter": filter_expr}
        )

    return vector_store.as_retriever(search_kwargs={"k": k})


if __name__ == "__main__":
    load_or_build_gold_vectorstore()


