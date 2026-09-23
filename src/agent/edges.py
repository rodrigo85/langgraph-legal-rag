"""
Arestas Condicionais e Validadores de Decisao (Routing & Validation Gates).
Implementa os pontos de inspecao e decisao de fluxo do DAG para autocorrecao.
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
    Dead-Letter Queue (DLQ) para Auditoria de Alucinacoes:
    Persiste o incidente com o rascunho rejeitado, contexto documental e parecer
    do auditor em JSONL, alimentando o Data Flywheel para DPO e fine-tuning.
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
        print(f"    [DLQ] Incidente de alucinacao arquivado com sucesso em: {HALLUCINATIONS_LOG_PATH.name}")
    except Exception as err:
        print(f"    [DLQ Alerta] Falha ao arquivar incidente de alucinacao: {err}")



def decide_to_generate(state: AgentState) -> str:
    """
    Decisao Pos-Filtro de Documentos:
    Verifica se existem dados aprovados na camada Gold para prosseguir com a sintese.
    Caso contrario, retroalimenta o DAG via 'rewrite_query' ou cai em fallback.
    """
    documents = state.get("documents", [])
    retry_count = state.get("retry_count", 0)
    
    if not documents:
        if retry_count < MAX_RETRIES:
            print(f"[DECISAO] Nenhum chunk qualificado. Roteando para -> REWRITE_QUERY")
            return "rewrite_query"
        else:
            print(f"[DECISAO] Limite maximo de retentativas atingido ({retry_count}) sem chunks validos. Roteando para -> FALLBACK")
            return "fallback"
    
    print(f"[DECISAO] Chunks aprovados ({len(documents)}). Roteando para -> GENERATE")
    return "generate"


def grade_generation_v_documents_and_question(state: AgentState) -> str:
    """
    Auditoria Unificada de Qualidade de Saida (Gate Consolidado com Protecao Anti-Loop):
    Avalia em UMA UNICA inferencia:
    1. Grounding (Fidelidade Factual vs Chunks)
    2. Answer Completeness (Utilidade da resposta)
    Garante matematicamente que o DAG nunca entre em loop infinito.
    """
    generation = state.get("generation", "")
    documents = state.get("documents", [])
    question = state["question"]
    retry_count = state.get("retry_count", 0)
    generation_attempts = state.get("generation_attempts", 1)
    
    if not documents:
        print("[AUDITORIA] Sem documentos base: roteando para FALLBACK.")
        return "fallback"

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

    if not is_grounded:
        log_hallucination_incident(
            question=question,
            generation=generation,
            documents=documents,
            audit_summary=audit_summary,
            retry_count=retry_count,
        )
        # Se for a 1ª tentativa no mesmo conjunto de chunks e temos margem no DAG
        if generation_attempts < 2 and retry_count < MAX_RETRIES:
            print(f"    [!] Reprovado no Gate de Grounding (Tentativa {generation_attempts}) -> Retentando geracao com ancoragem reforcada.")
            return "not_grounded"
        
        # Se já falhou mais de uma vez nos mesmos chunks, os chunks não possuem o fato necessário!
        # Roteia para REWRITE_QUERY para forçar a busca de novos chunks
        if retry_count < MAX_RETRIES:
            print("    [!] Chunks atuais insuficientes para ancoragem factual sem alucinacao. Roteando para -> REWRITE_QUERY para buscar novas evidencias.")
            return "not_useful"
            
        # Esgotou o limite global de retentativas do DAG: previne entrega de alucinação
        print("    [!] Limite de retentativas do DAG esgotado sem ancoragem -> Roteando para FALLBACK (Abstencao).")
        return "fallback"

    if not is_useful:
        if retry_count < MAX_RETRIES:
            print("    [!] Reprovado no Gate de Utilidade -> Roteando para REWRITE_QUERY.")
            return "not_useful"
        else:
            print("    [!] Resposta inconclusiva apos limite de retentativas -> Roteando para FALLBACK.")
            return "fallback"

    print("    [OK] Aprovado em todos os gates -> Roteando para END.")
    return "useful"

