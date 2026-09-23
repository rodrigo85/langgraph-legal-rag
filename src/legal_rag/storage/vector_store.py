"""
Gold-layer vector store factory.

    VECTOR_STORE = chroma    -> embedded ChromaDB on local disk (development)
    VECTOR_STORE = pgvector  -> PostgreSQL + pgvector (Amazon RDS / Azure Database for PostgreSQL)

pgvector is the portable production choice: the same code and SQL run on both
clouds, and the index lives next to transactional data with standard backups.
"""

from langchain_core.vectorstores import VectorStore

from legal_rag.config import GOLD_CHROMA_DIR, Settings, get_settings
from legal_rag.providers import get_embeddings


def get_vector_store(settings: Settings | None = None) -> VectorStore:
    settings = settings or get_settings()
    embeddings = get_embeddings(settings)

    if settings.vector_store == "pgvector":
        from langchain_postgres import PGVector

        return PGVector(
            embeddings=embeddings,
            collection_name=settings.collection_name,
            connection=settings.pgvector_dsn.get_secret_value(),
            use_jsonb=True,
        )

    from langchain_chroma import Chroma

    GOLD_CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=settings.collection_name,
        embedding_function=embeddings,
        persist_directory=str(GOLD_CHROMA_DIR),
    )


def count_vectors(store: VectorStore) -> int:
    """Number of vectors in the active collection (backend-specific)."""
    if hasattr(store, "_collection"):  # Chroma
        return store._collection.count()

    # PGVector: count rows of the collection
    from sqlalchemy import func, select

    with store._make_sync_session() as session:
        collection = store.get_collection(session)
        if collection is None:
            return 0
        return session.execute(
            select(func.count()).select_from(store.EmbeddingStore).where(
                store.EmbeddingStore.collection_id == collection.uuid
            )
        ).scalar_one()


def reset_collection(store: VectorStore) -> VectorStore:
    """Drops and recreates the active collection."""
    if hasattr(store, "_collection"):  # Chroma
        store._client.delete_collection(store._collection.name)
        return get_vector_store()
    store.delete_collection()
    store.create_collection()
    return store


def fetch_all_chunks(store: VectorStore) -> tuple[list[dict], list[str]]:
    """Returns (metadatas, documents) for every chunk in the collection, for audits."""
    if hasattr(store, "_collection"):  # Chroma
        data = store._collection.get(include=["metadatas", "documents"])
        return data.get("metadatas", []), data.get("documents", [])

    from sqlalchemy import select

    with store._make_sync_session() as session:
        collection = store.get_collection(session)
        if collection is None:
            return [], []
        rows = session.execute(
            select(store.EmbeddingStore.cmetadata, store.EmbeddingStore.document).where(
                store.EmbeddingStore.collection_id == collection.uuid
            )
        ).all()
    return [r[0] or {} for r in rows], [r[1] or "" for r in rows]
