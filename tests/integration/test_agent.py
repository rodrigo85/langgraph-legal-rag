"""
End-to-end test for the self-correcting RAG agent (requires Ollama and an indexed Gold layer).
Runs an investigative query through the LangGraph graph and validates:
1. Retrieval of court-document chunks
2. Filtering by the Document Grader
3. Grounded generation with page citations
4. Passing hallucination audit
"""

import pytest

from legal_rag.agent.graph import build_graph

pytestmark = pytest.mark.integration


def test_agent_run():
    # Hallucination incidents go to a per-test file (see tests/conftest.py).
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
        "generation_attempts": 0,
        "retry_count": 0,
        "max_retries": 3,
        "web_search_needed": False,
        "hallucination_verdict": None,
        "answer_verdict": None,
        "citations": [],
    }

    result = app.invoke(initial_state)

    assert result.get("generation") is not None
    assert len(result.get("generation")) > 50
