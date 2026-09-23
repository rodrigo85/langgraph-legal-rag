"""
Cyclic DAG orchestration in LangGraph.
Assembles the Self-RAG finite state machine, wiring together retrieval,
quality-grading, and self-correction loop nodes.
"""

from langgraph.graph import StateGraph, END


from legal_rag.agent.state import AgentState
from legal_rag.agent.nodes import (
    retrieve_node,
    grade_documents_node,
    generate_node,
    rewrite_query_node,
    fallback_node,
)
from legal_rag.agent.edges import (
    decide_to_generate,
    grade_generation_v_documents_and_question,
)


def build_graph():
    """
    Compiles the LangGraph graph as a DAG with cyclic feedback support
    and a guaranteed bound against infinite loops.
    """
    workflow = StateGraph(AgentState)

    # Register operation nodes
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade_documents", grade_documents_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("rewrite_query", rewrite_query_node)
    workflow.add_node("fallback", fallback_node)

    # Entry point and primary flow
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "grade_documents")

    # Conditional edge after document quality grading
    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate,
        {
            "rewrite_query": "rewrite_query",
            "generate": "generate",
            "fallback": "fallback",
        },
    )

    # Feedback loop: rewriting re-runs the vector search
    workflow.add_edge("rewrite_query", "retrieve")

    # Post-generation conditional edge: dual audit with anti-loop protection
    workflow.add_conditional_edges(
        "generate",
        grade_generation_v_documents_and_question,
        {
            "not_grounded": "generate",        # Regenerate with stricter constraints (max 1x per chunk set)
            "not_useful": "rewrite_query",     # Rewrite and retrieve new chunks
            "fallback": "fallback",            # Safe abstention
            "useful": END,                     # Successfully validated
        },
    )

    # The fallback node always ends at END with an audited disclaimer
    workflow.add_edge("fallback", END)

    return workflow.compile()


if __name__ == "__main__":
    app = build_graph()
    print("[OK] LangGraph graph compiled and validated successfully!")

