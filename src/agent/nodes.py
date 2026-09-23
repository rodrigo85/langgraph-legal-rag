"""
Nos de Execucao do DAG (LangGraph Nodes).
Cada no representa uma etapa deterministica de processamento, filtragem ou geracao.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
from langchain_core.documents import Document

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.state import AgentState
from src.config import TOP_K_DOCUMENTS, MAX_RETRIES
from src.pipeline.indexer import load_or_build_gold_vectorstore
from src.chains.doc_grader import create_doc_grader
from src.chains.query_rewriter import create_query_rewriter
from src.chains.generator import create_generator


def retrieve_node(state: AgentState) -> Dict[str, Any]:
    """
    No 1: Recuperacao Vetorial (Gold Layer Query).
    Executa busca por similaridade semantica no ChromaDB para a query corrente.
    """
    query = state.get("current_query") or state["question"]
    print(f"\n[NO: RETRIEVE] Executando busca vetorial para: '{query}'")
    
    vector_store = load_or_build_gold_vectorstore()
    retriever = vector_store.as_retriever(search_kwargs={"k": TOP_K_DOCUMENTS})
    docs = retriever.invoke(query)
    
    print(f"[NO: RETRIEVE] {len(docs)} chunks extraidos da camada Gold.")
    return {"documents": docs}


def grade_documents_node(state: AgentState) -> Dict[str, Any]:
    """
    No 2: Data Quality Gate (Document Relevance Grader).
    Filtra ruído e chunks irrelevantes atraves de classificacao binaria estruturada.
    """
    question = state["question"]
    documents = state.get("documents", [])
    print(f"\n[NO: GRADE_DOCS] Validando qualidade de {len(documents)} chunks...")
    
    grader = create_doc_grader()
    filtered_docs: List[Document] = []
    
    for idx, doc in enumerate(documents, start=1):
        page = doc.metadata.get("page", "?")
        try:
            res = grader.invoke({"question": question, "document": doc.page_content})
            score = getattr(res, "binary_score", "yes").lower()
            reason = getattr(res, "reason", "")
        except Exception as e:
            print(f"    Chunk {idx} (Pag {page}): Fallback de seguranca ativado ({e}).")
            score = "yes"
            reason = "fallback"

        if score == "yes":
            print(f"    [+] Chunk {idx} (Pag {page}): APROVADO. {reason}")
            filtered_docs.append(doc)
        else:
            print(f"    [-] Chunk {idx} (Pag {page}): DESCARTADO (Ruido). {reason}")

    return {"documents": filtered_docs}


def rewrite_query_node(state: AgentState) -> Dict[str, Any]:
    """
    No 3: Query Optimization (Query Rewriter).
    Aplica engenharia de termos para converter consultas informais em termos tecnicos contratuais.
    """
    question = state["question"]
    retry_count = state.get("retry_count", 0) + 1
    print(f"\n[NO: REWRITE_QUERY] Ciclo de Autocorrecao {retry_count}/{MAX_RETRIES}...")
    
    rewriter = create_query_rewriter()
    try:
        res = rewriter.invoke({"question": question})
        improved_query = getattr(res, "improved_query", question)
        rationale = getattr(res, "rationale", "")
        print(f"    [->] Query Otimizada: '{improved_query}'")
        print(f"    [->] Rationale Tecnico: {rationale}")
    except Exception as e:
        print(f"    Erro ao reescrever query: {e}. Aplicando expansao deterministica.")
        improved_query = f"{question} Google Apple ISA search agreement antitrust"

    return {
        "current_query": improved_query,
        "retry_count": retry_count,
    }


def generate_node(state: AgentState) -> Dict[str, Any]:
    """
    No 4: Sintese Ancorada (Fact-Grounded Generation).
    Gera a resposta estritamente ancorada com citacao mandatoria da linhagem de paginas.
    """
    question = state["question"]
    documents = state.get("documents", [])
    print(f"\n[NO: GENERATE] Sintetizando resposta baseada em {len(documents)} trechos aprovados...")
    
    formatted_context_parts = []
    pages_cited = set()
    for doc in documents:
        page = doc.metadata.get("page", "?")
        pages_cited.add(str(page))
        formatted_context_parts.append(f"--- [Pagina {page} da Sentenca] ---\n{doc.page_content}")
    
    context_str = "\n\n".join(formatted_context_parts)
    if not context_str.strip():
        context_str = "Nenhum documento com relevancia suficiente foi localizado na base judicial."

    generator = create_generator()
    generation = generator.invoke({"context": context_str, "question": question})
    
    return {
        "generation": generation,
        "citations": sorted(list(pages_cited)),
    }

