"""
Modulo de Ingestao e Indexacao Vetorial.
Processa o PDF oficial da Sentenca Antitruste (286 paginas),
preserva a numeracao de pagina judicial e indexa no ChromaDB com nomic-embed-text.
"""

import sys
from pathlib import Path
from typing import List

# Assegura que a raiz do projeto esteja no sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pypdf
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

from langchain_ollama import OllamaEmbeddings

from src.config import (
    OPINION_PDF_PATH,
    CHROMA_PERSIST_DIR,
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)


def load_pdf_pages(pdf_path: Path = OPINION_PDF_PATH) -> List[Document]:
    """
    Carrega o PDF extraindo texto pagina por pagina,
    registrando metadados estritos de pagina (1 a 286).
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"Arquivo PDF nao encontrado em: {pdf_path}")

    print(f"[*] Extraindo texto de {pdf_path.name}...")
    reader = pypdf.PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    print(f"[*] Total de paginas identificadas: {total_pages}")

    docs: List[Document] = []
    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if len(text) < 50:
            continue  # Pular paginas vazias ou apenas capas em branco
        
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "source": pdf_path.name,
                    "page": idx,
                    "document_title": "U.S. v. Google LLC - Memorandum Opinion (Doc 1033)",
                },
            )
        )

    print(f"[OK] {len(docs)} paginas com conteudo extraidas com sucesso.")
    return docs


def split_documents(docs: List[Document]) -> List[Document]:
    """
    Divide os documentos em chunks mantendo os metadados de pagina judicial.
    """
    print(f"[*] Dividindo em chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = text_splitter.split_documents(docs)
    print(f"[OK] Criados {len(chunks)} chunks para indexacao.")
    return chunks


def build_vector_store(chunks: List[Document], persist_dir: Path = CHROMA_PERSIST_DIR) -> Chroma:
    """
    Gera embeddings locais via Ollama (nomic-embed-text) e persiste no ChromaDB.
    """
    print(f"[*] Inicializando embeddings com modelo '{OLLAMA_EMBED_MODEL}' no Ollama...")
    embeddings = OllamaEmbeddings(
        model=OLLAMA_EMBED_MODEL,
        base_url=OLLAMA_BASE_URL,
    )

    persist_dir.mkdir(parents=True, exist_ok=True)
    print(f"[*] Indexando {len(chunks)} chunks no ChromaDB ({persist_dir})...")
    
    # Processa em lotes para evitar sobrecarga de requisicoes no Ollama
    batch_size = 100
    vector_store = Chroma(
        collection_name="antitrust_google_opinion",
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        vector_store.add_documents(batch)
        print(f"    Indexados {min(i + batch_size, len(chunks))}/{len(chunks)} chunks...")

    print("[OK] Vector Store criado e persistido com sucesso!")
    return vector_store


def get_vector_store(persist_dir: Path = CHROMA_PERSIST_DIR) -> Chroma:
    """
    Carrega o ChromaDB existente ou orienta a criacao.
    """
    embeddings = OllamaEmbeddings(
        model=OLLAMA_EMBED_MODEL,
        base_url=OLLAMA_BASE_URL,
    )
    return Chroma(
        collection_name="antitrust_google_opinion",
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )


if __name__ == "__main__":
    docs = load_pdf_pages()
    chunks = split_documents(docs)
    build_vector_store(chunks)
