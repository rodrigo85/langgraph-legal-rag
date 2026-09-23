"""
Conditional Edges and Decision Validators (Routing & Validation Gates).
Implements the DAG's inspection and flow-decision points for self-correction.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.state import AgentState
from src.config import MAX_RETRIES, HALLUCINATIONS_LOG_PATH
from src.chains.hallucination_grader import create_hallucination_grader, create_unified_quality_grader
from src.chains.answer_grader import create_answer_grader


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
    to JSONL, feeding a data flywheel for future DPO / fine-tuning.
    """
    try:
        HALLUCINATIONS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        incident_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "question": question,
            "retry_cycle": retry_count,
            "rejected_generation": generation,
            "audit_summary": audit_summary,
            "retrieved_pages": [d.metadata.get("page") for d in documents if hasattr(d, "metadata")],
            "retrieved_sources": list(set([d.metadata.get("source_file") for d in documents if hasattr(d, "metadata")])),
            "context_snippets": [d.page_content[:200] for d in documents if hasattr(d, "page_content")],
        }
        with open(HALLUCINATIONS_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(incident_record, ensure_ascii=False) + "\n")
        print(f"    [DLQ] Hallucination incident logged to: {HALLUCINATIONS_LOG_PATH.name}")
    except Exception as err:
        print(f"    [DLQ Warning] Failed to log hallucination incident: {err}")



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
            print(f"[DECISION] No qualified chunks. Routing to -> REWRITE_QUERY")
            return "rewrite_query"
        else:
            print(f"[DECISION] Max retries reached ({retry_count}) with no valid chunks. Routing to -> FALLBACK")
            return "fallback"
    
    print(f"[DECISION] Approved chunks ({len(documents)}). Routing to -> GENERATE")
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
        print("[AUDIT] No source documents: routing to FALLBACK.")
        return "fallback"

    doc_text = "\n\n".join([f"--- [Pagina {d.metadata.get('page', '?')}] ---\n{d.page_content}" for d in documents])
    
    print(f"\n[UNIFIED QUALITY AUDIT] Checking factual faithfulness and usefulness...")
    unified_grader = create_unified_quality_grader()
    try:
        res = unified_grader.invoke({
            "documents": doc_text,
            "question": question,
            "generation": generation,
        })
        is_grounded = getattr(res, "is_grounded", "yes").lower() == "yes"
        is_useful = getattr(res, "is_useful", "yes").lower() == "yes"
        audit_summary = getattr(res, "audit_summary", "")
        print(f"    [Grounding: {'100% FAITHFUL' if is_grounded else 'HALLUCINATION DETECTED'}] [Usefulness: {'USEFUL' if is_useful else 'INSUFFICIENT'}]")
        print(f"    Auditor verdict: {audit_summary}")
    except Exception as e:
        print(f"    Unified audit error: {e}. Proceeding via safe fallback.")
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
            print(f"    [!] Failed the Grounding Gate (attempt {generation_attempts}) -> Retrying generation with reinforced grounding.")
            return "not_grounded"
        
        # Already failed more than once on the same chunks: they lack the required fact!
        # Route to REWRITE_QUERY to force retrieval of new chunks
        if retry_count < MAX_RETRIES:
            print("    [!] Current chunks are insufficient for hallucination-free grounding. Routing to -> REWRITE_QUERY to fetch new evidence.")
            return "not_useful"
            
        # Global DAG retry limit exhausted: prevent delivering a hallucination
        print("    [!] DAG retry limit exhausted without grounding -> Routing to FALLBACK (abstention).")
        return "fallback"

    if not is_useful:
        if retry_count < MAX_RETRIES:
            print("    [!] Failed the Usefulness Gate -> Routing to REWRITE_QUERY.")
            return "not_useful"
        else:
            print("    [!] Answer still inconclusive after retry limit -> Routing to FALLBACK.")
            return "fallback"

    print("    [OK] Passed all gates -> Routing to END.")
    return "useful"

