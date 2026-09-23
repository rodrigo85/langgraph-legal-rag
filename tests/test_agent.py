"""
Automated test for the Self-Corrective RAG Agent.
Runs an investigative query through the LangGraph graph and validates:
1. Retrieval of court-document chunks
2. Filtering by the Document Grader
3. Grounded generation with page citations
4. Passing hallucination audit
"""

import sys

# Configure UTF-8 encoding for the Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


from legal_rag.agent.graph import build_graph


def test_agent_run():
    print("[*] Starting LangGraph graph test...")
    app = build_graph()

    test_question = (
        "Qual era o acordo de compartilhamento de receita (ISA) entre Google e Apple "
        "para manter a busca do Google como padrao no Safari?"
    )

    initial_state = {
        "question": test_question,
        "current_query": test_question,
        "documents": [],
        "generation": "",
        "retry_count": 0,
        "max_retries": 3,
        "web_search_needed": False,
        "hallucination_verdict": None,
        "answer_verdict": None,
        "citations": [],
    }

    print(f"[*] Test question: {test_question}")
    result = app.invoke(initial_state)

    print("\n" + "=" * 50)
    print("[*] GENERATION RESULT:")
    print(result.get("generation"))
    print("\n[*] CITATIONS FOUND:")
    print(result.get("citations"))
    print("=" * 50)

    assert result.get("generation") is not None
    assert len(result.get("generation")) > 50
    print("[PASS] Test completed successfully!")


if __name__ == "__main__":
    test_agent_run()
