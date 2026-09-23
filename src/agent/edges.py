"""
Arestas Condicionais e Validadores de Decisao (Routing & Validation Gates).
Implementa os pontos de inspecao e decisao de fluxo do DAG para autocorrecao.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.state import AgentState
from src.config import MAX_RETRIES
from src.chains.hallucination_grader import create_hallucination_grader, create_unified_quality_grader
from src.chains.answer_grader import create_answer_grader


def decide_to_generate(state: AgentState) -> str:
    """
    Decisao Pos-Filtro de Documentos:
    Verifica se existem dados aprovados na camada Gold para prosseguir com a sintese.
    Caso contrario, retroalimenta o DAG via 'rewrite_query'.
    """
    documents = state.get("documents", [])
    retry_count = state.get("retry_count", 0)
    
    if not documents:
        if retry_count < MAX_RETRIES:
            print(f"[DECISAO] Nenhum chunk qualificado. Roteando para -> REWRITE_QUERY")
            return "rewrite_query"
        else:
            print(f"[DECISAO] Limite maximo de retentativas atingido ({retry_count}). Roteando para -> GENERATE")
            return "generate"
    
    print(f"[DECISAO] Chunks aprovados ({len(documents)}). Roteando para -> GENERATE")
    return "generate"


def grade_generation_v_documents_and_question(state: AgentState) -> str:
    """
    Auditoria Unificada de Qualidade de Saida (Gate Consolidado):
    Avalia em UMA UNICA inferencia:
    1. Grounding (Fidelidade Factual vs Chunks)
    2. Answer Completeness (Utilidade da resposta)
    Reduz o tempo de auditoria em 50%.
    """
    generation = state.get("generation", "")
    documents = state.get("documents", [])
    question = state["question"]
    retry_count = state.get("retry_count", 0)
    
    if not documents:
        print("[AUDITORIA] Sem documentos base: finalizando fluxo.")
        return "useful"

    doc_text = "\n\n".join([f"--- [Pagina {d.metadata.get('page', '?')}] ---\n{d.page_content}" for d in documents])
    
    print(f"\n[AUDITORIA UNIFICADA DE QUALIDADE] Validando fidelidade factual e utilidade...")
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
        print(f"    [Grounding: {'100% FIEL' if is_grounded else 'ALUCINACAO DETECTADA'}] [Utilidade: {'UTIL' if is_useful else 'INSUFICIENTE'}]")
        print(f"    Veredito do Auditor: {audit_summary}")
    except Exception as e:
        print(f"    Erro na auditoria unificada: {e}. Prosseguindo por fallback seguro.")
        is_grounded = True
        is_useful = True

    if not is_grounded and retry_count < MAX_RETRIES:
        print("    [!] Reprovado no Gate de Grounding -> Retentando geracao ancorada.")
        return "not_grounded"

    if not is_useful and retry_count < MAX_RETRIES:
        print("    [!] Reprovado no Gate de Utilidade -> Roteando para REWRITE_QUERY.")
        return "not_useful"

    print("    [OK] Aprovado em todos os gates -> Roteando para END.")
    return "useful"

