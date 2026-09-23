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
from src.chains.hallucination_grader import create_hallucination_grader
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
    Auditoria Dupla de Qualidade de Saida:
    Gate 1: Grounding Check (Detector de Alucinacao vs Chunks).
    Gate 2: Answer Completeness Check (Avaliacao de utilidade da resposta).
    """
    generation = state.get("generation", "")
    documents = state.get("documents", [])
    question = state["question"]
    retry_count = state.get("retry_count", 0)
    
    if not documents:
        print("[AUDITORIA] Sem documentos base: finalizando fluxo.")
        return "useful"

    doc_text = "\n\n".join([d.page_content for d in documents])
    
    # Gate 1: Hallucination Check
    print(f"\n[GATE 1: AUDITORIA DE ALUCINACAO] Testando fidelidade aos fatos...")
    hallucination_grader = create_hallucination_grader()
    try:
        h_res = hallucination_grader.invoke({"documents": doc_text, "generation": generation})
        is_grounded = getattr(h_res, "binary_score", "yes").lower() == "yes"
        explanation = getattr(h_res, "explanation", "")
        print(f"    Resultado: {'100% FIEL AOS DOCUMENTOS' if is_grounded else 'ALUCINACAO DETECTADA'} ({explanation})")
    except Exception as e:
        print(f"    Erro no auditor de alucinacao: {e}. Prosseguindo por fallback.")
        is_grounded = True

    if not is_grounded and retry_count < MAX_RETRIES:
        print("    [!] Reprovado no Gate 1 -> Retentando geracao ancorada.")
        return "not_grounded"

    # Gate 2: Answer Completeness Check
    print(f"\n[GATE 2: AUDITORIA DE UTILIDADE] Verificando resolucao da questao...")
    answer_grader = create_answer_grader()
    try:
        a_res = answer_grader.invoke({"question": question, "generation": generation})
        is_useful = getattr(a_res, "binary_score", "yes").lower() == "yes"
        explanation = getattr(a_res, "explanation", "")
        print(f"    Resultado: {'UTIL E COMPLETA' if is_useful else 'RESPOSTA INSUFICIENTE'} ({explanation})")
    except Exception as e:
        print(f"    Erro no auditor de utilidade: {e}. Prosseguindo por fallback.")
        is_useful = True

    if is_useful:
        print("    [OK] Aprovado em todos os gates -> Roteando para END.")
        return "useful"
    else:
        if retry_count < MAX_RETRIES:
            print("    [!] Reprovado no Gate 2 -> Roteando para REWRITE_QUERY.")
            return "not_useful"
        return "useful"

