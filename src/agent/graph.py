"""
Orquestracao do DAG Cíclico no LangGraph.
Monta a arquitetura de maquina de estados finitos do Self-RAG
conectando nos de extracao, avaliacao de qualidade e ciclos de autocorrecao.
"""

import sys
from pathlib import Path
from langgraph.graph import StateGraph, END

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.state import AgentState
from src.agent.nodes import (
    retrieve_node,
    grade_documents_node,
    generate_node,
    rewrite_query_node,
    fallback_node,
)
from src.agent.edges import (
    decide_to_generate,
    grade_generation_v_documents_and_question,
)


def build_graph():
    """
    Compila o grafo LangGraph como um DAG com suporte a retroalimentacao ciclica
    e garantia matematica contra loops infinitos.
    """
    workflow = StateGraph(AgentState)

    # Registro dos nos de operacao
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade_documents", grade_documents_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("rewrite_query", rewrite_query_node)
    workflow.add_node("fallback", fallback_node)

    # Ponto de entrada e fluxo primario
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "grade_documents")

    # Aresta condicional pos-avaliacao de qualidade documental
    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate,
        {
            "rewrite_query": "rewrite_query",
            "generate": "generate",
            "fallback": "fallback",
        },
    )

    # Ciclo de retroalimentacao: reescrita reexecuta a busca vetorial
    workflow.add_edge("rewrite_query", "retrieve")

    # Aresta condicional pos-geracao: auditoria dupla com protecao anti-loop
    workflow.add_conditional_edges(
        "generate",
        grade_generation_v_documents_and_question,
        {
            "not_grounded": "generate",        # Gera novamente com maior restricao (max 1x por chunk set)
            "not_useful": "rewrite_query",     # Reformula e busca novos chunks
            "fallback": "fallback",            # Abstencao segura
            "useful": END,                     # Validado com sucesso
        },
    )

    # O no de fallback sempre finaliza no END com disclaimer auditado
    workflow.add_edge("fallback", END)

    return workflow.compile()


if __name__ == "__main__":
    app = build_graph()
    print("[OK] Grafo LangGraph compilado e validado com sucesso!")

