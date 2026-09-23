"""
DAG Execution Nodes (LangGraph Nodes).
Each node is a deterministic processing, filtering, or generation step.
"""

import logging
from typing import Any, Dict

from legal_rag.agent.state import AgentState
from legal_rag.chains.doc_grader import create_batch_doc_grader
from legal_rag.chains.generator import create_generator
from legal_rag.chains.query_rewriter import create_query_rewriter
from legal_rag.config import MAX_RETRIES, TOP_K_DOCUMENTS
from legal_rag.pipeline.indexer import get_temporal_retriever, load_or_build_gold_vectorstore

logger = logging.getLogger(__name__)


def retrieve_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 1: Vector Retrieval (Gold Layer Query).
    Runs a semantic similarity search in ChromaDB for the current query,
    honoring the as_of_date filter to prevent lookahead bias.
    """
    query = state.get("current_query") or state["question"]
    as_of_date = state.get("as_of_date")
    
    if as_of_date:
        logger.info("node.retrieve", extra={"query": query, "as_of_date": as_of_date})
        retriever = get_temporal_retriever(as_of_date=as_of_date, k=TOP_K_DOCUMENTS)
    else:
        logger.info("node.retrieve", extra={"query": query})
        vector_store = load_or_build_gold_vectorstore()
        retriever = vector_store.as_retriever(search_kwargs={"k": TOP_K_DOCUMENTS})

    docs = retriever.invoke(query)
    logger.info("node.retrieve.done", extra={"chunks": len(docs)})
    return {"documents": docs}


def grade_documents_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 2: Data Quality Gate (Batch Document Relevance Grader).
    Filters out noise and irrelevant chunks in A SINGLE optimized inference (4x faster).
    """
    question = state["question"]
    documents = state.get("documents", [])
    logger.info("node.grade_documents", extra={"chunks": len(documents)})
    
    if not documents:
        return {"documents": []}

    batch_parts = []
    for idx, doc in enumerate(documents, start=1):
        page = doc.metadata.get("page", "?")
        preview = doc.page_content[:300].replace("\n", " ")
        batch_parts.append(f"Trecho [{idx}] (Pag {page}): {preview}")
    documents_batch_str = "\n\n".join(batch_parts)

    batch_grader = create_batch_doc_grader()
    try:
        res = batch_grader.invoke({
            "question": question,
            "documents_batch": documents_batch_str,
        })
        relevant_indices = getattr(res, "relevant_indices", list(range(1, len(documents) + 1)))
        rationale = getattr(res, "rationale", "")
        logger.info("node.grade_documents.done", extra={"approved": relevant_indices, "rationale": rationale})
        
        filtered_docs = [
            doc for idx, doc in enumerate(documents, start=1)
            if idx in relevant_indices
        ]
        if not filtered_docs and documents:
            logger.info("node.grade_documents.none_approved")
    except Exception as e:
        logger.warning("node.grade_documents.error", extra={"error": str(e), "action": "approve_all"})
        filtered_docs = documents

    return {"documents": filtered_docs}


def rewrite_query_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 3: Query Optimization (Query Rewriter).
    Rewrites informal queries into technical, contract-level terminology.
    """
    question = state["question"]
    retry_count = state.get("retry_count", 0) + 1
    logger.info("node.rewrite_query", extra={"cycle": retry_count, "max_retries": MAX_RETRIES})
    
    rewriter = create_query_rewriter()
    try:
        res = rewriter.invoke({"question": question})
        improved_query = getattr(res, "improved_query", question)
        rationale = getattr(res, "rationale", "")
        logger.info("node.rewrite_query.done", extra={"improved_query": improved_query, "rationale": rationale})
    except Exception as e:
        logger.warning("node.rewrite_query.error", extra={"error": str(e), "action": "deterministic_expansion"})
        improved_query = f"{question} Google Apple ISA search agreement antitrust"

    return {
        "current_query": improved_query,
        "retry_count": retry_count,
        "generation_attempts": 0,
    }


def generate_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 4: Fact-Grounded Generation.
    Generates a strictly grounded answer with mandatory page-lineage citations.
    """
    question = state["question"]
    documents = state.get("documents", [])
    generation_attempts = state.get("generation_attempts", 0) + 1
    
    if generation_attempts > 1:
        logger.info("node.generate", extra={"attempt": generation_attempts, "mode": "reinforced_grounding"})
        effective_question = (
            f"{question} (ATENCAO: Seja estritamente literal ao texto fornecido. "
            "Se os fatos exatos nao constarem expressamente nos trechos, afirme que a evidencia e inconclusiva.)"
        )
    else:
        logger.info("node.generate", extra={"attempt": generation_attempts, "chunks": len(documents)})
        effective_question = question
    
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
    generation = generator.invoke({"context": context_str, "question": effective_question})
    
    return {
        "generation": generation,
        "citations": sorted(list(pages_cited)),
        "generation_attempts": generation_attempts,
    }


def fallback_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 5: Graceful Abstention (Graceful Degradation).
    Triggered when DAG retries are exhausted without reaching 100% factual grounding.
    Ensures no hallucination is delivered to the end user.
    """
    logger.info("node.fallback")
    documents = state.get("documents", [])
    pages = sorted(list(set([str(d.metadata.get("page", "?")) for d in documents])))
    pages_str = ", ".join(pages) if pages else "N/A"
    disclaimer = (
        f"Com base estritamente nos trechos documentais analisados da Sentenca Judicial (Paginas {pages_str}), "
        "as evidencias recuperadas nao contem dados suficientes para responder a questao com certeza factual absoluta "
        "sem recorrer a inferencias externas. Em conformidade com o protocolo pericial antitruste, "
        "a resposta foi suspensa para evitar alucinacoes. Recomenda-se refinar a pergunta com termos judiciais mais especificos."
    )
    return {
        "generation": disclaimer,
        "hallucination_verdict": "abstained",
        "answer_verdict": "fallback",
    }

