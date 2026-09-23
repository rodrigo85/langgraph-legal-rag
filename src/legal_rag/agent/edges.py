"""
Conditional Edges and Decision Validators (Routing & Validation Gates).
Implements the DAG's inspection and flow-decision points for self-correction.
"""

import logging

from legal_rag.agent.state import AgentState
from legal_rag.chains.hallucination_grader import create_unified_quality_grader
from legal_rag.config import MAX_RETRIES
from legal_rag.storage.dlq import build_incident_record, log_incident

logger = logging.getLogger(__name__)


def log_hallucination_incident(
    question: str,
    generation: str,
    documents: list,
    audit_summary: str,
    retry_count: int,
) -> None:
    """
    Dead-Letter Queue (DLQ) for hallucination auditing:
    Persists the incident (rejected draft, document context, and auditor verdict)
    to the configured sink (JSONL / S3 / Azure Blob), feeding a data flywheel
    for future DPO / fine-tuning.
    """
    record = build_incident_record(question, generation, documents, audit_summary, retry_count)
    log_incident(record)


def decide_to_generate(state: AgentState) -> str:
    """
    Post-document-filter decision:
    Checks whether approved Gold-layer data exists to proceed with synthesis.
    Otherwise, loops back through 'rewrite_query' or falls back.
    """
    documents = state.get("documents", [])
    retry_count = state.get("retry_count", 0)
    
    if not documents:
        if retry_count < MAX_RETRIES:
            logger.info("route.decision", extra={"reason": "no_qualified_chunks", "next": "rewrite_query"})
            return "rewrite_query"
        else:
            logger.info("route.decision", extra={"reason": "max_retries_no_chunks", "retry_count": retry_count, "next": "fallback"})
            return "fallback"
    
    logger.info("route.decision", extra={"approved_chunks": len(documents), "next": "generate"})
    return "generate"


def grade_generation_v_documents_and_question(state: AgentState) -> str:
    """
    Unified output quality audit (consolidated gate with anti-loop protection):
    Evaluates in A SINGLE inference:
    1. Grounding (factual faithfulness vs. chunks)
    2. Answer completeness (usefulness of the answer)
    Guarantees the DAG can never enter an infinite loop.
    """
    generation = state.get("generation", "")
    documents = state.get("documents", [])
    question = state["question"]
    retry_count = state.get("retry_count", 0)
    generation_attempts = state.get("generation_attempts", 1)
    
    if not documents:
        logger.info("audit.no_documents", extra={"next": "fallback"})
        return "fallback"

    doc_text = "\n\n".join([f"--- [Pagina {d.metadata.get('page', '?')}] ---\n{d.page_content}" for d in documents])
    
    unified_grader = create_unified_quality_grader()
    audit_summary = ""
    try:
        res = unified_grader.invoke({
            "documents": doc_text,
            "question": question,
            "generation": generation,
        })
        is_grounded = getattr(res, "is_grounded", "yes").lower() == "yes"
        is_useful = getattr(res, "is_useful", "yes").lower() == "yes"
        audit_summary = getattr(res, "audit_summary", "")
        logger.info(
            "audit.verdict",
            extra={"grounded": is_grounded, "useful": is_useful, "summary": audit_summary},
        )
    except Exception as e:
        logger.warning("audit.error", extra={"error": str(e)})
        is_grounded = True
        is_useful = True

    if not is_grounded:
        log_hallucination_incident(
            question=question,
            generation=generation,
            documents=documents,
            audit_summary=audit_summary,
            retry_count=retry_count,
        )
        # First attempt on this chunk set and the DAG still has retry budget
        if generation_attempts < 2 and retry_count < MAX_RETRIES:
            logger.info("route.decision", extra={"reason": "not_grounded", "attempt": generation_attempts, "next": "generate"})
            return "not_grounded"
        
        # Already failed more than once on the same chunks: they lack the required fact!
        # Route to REWRITE_QUERY to force retrieval of new chunks
        if retry_count < MAX_RETRIES:
            logger.info("route.decision", extra={"reason": "insufficient_chunks", "next": "rewrite_query"})
            return "not_useful"
            
        # Global DAG retry limit exhausted: prevent delivering a hallucination
        logger.info("route.decision", extra={"reason": "retries_exhausted_not_grounded", "next": "fallback"})
        return "fallback"

    if not is_useful:
        if retry_count < MAX_RETRIES:
            logger.info("route.decision", extra={"reason": "not_useful", "next": "rewrite_query"})
            return "not_useful"
        else:
            logger.info("route.decision", extra={"reason": "retries_exhausted_not_useful", "next": "fallback"})
            return "fallback"

    logger.info("route.decision", extra={"reason": "passed_all_gates", "next": "end"})
    return "useful"

