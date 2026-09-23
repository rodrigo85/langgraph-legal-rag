"""DAG nodes with every LLM chain replaced by a fake."""

from types import SimpleNamespace

import pytest
from langchain_core.documents import Document

from legal_rag.agent import nodes


class FakeChain:
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.calls = []

    def invoke(self, payload):
        self.calls.append(payload)
        if self.exc:
            raise self.exc
        return self.result


@pytest.fixture
def docs():
    return [
        Document(page_content="First chunk.", metadata={"page": 12}),
        Document(page_content="Second chunk.", metadata={"page": 40}),
        Document(page_content="Third chunk.", metadata={"page": 12}),
    ]


def test_fallback_node_abstains_citing_pages(docs):
    out = nodes.fallback_node({"documents": docs})
    assert "Paginas 12, 40)" in out["generation"]
    assert out["hallucination_verdict"] == "abstained"
    assert out["answer_verdict"] == "fallback"


def test_fallback_node_without_documents():
    assert "Paginas N/A" in nodes.fallback_node({"documents": []})["generation"]


def test_generate_node_formats_context_and_citations(monkeypatch, docs):
    chain = FakeChain("answer")
    monkeypatch.setattr(nodes, "create_generator", lambda: chain)

    out = nodes.generate_node({"question": "Q?", "documents": docs, "generation_attempts": 0})

    assert out == {"generation": "answer", "citations": ["12", "40"], "generation_attempts": 1}
    context = chain.calls[0]["context"]
    assert "--- [Pagina 12 da Sentenca] ---\nFirst chunk." in context
    assert "--- [Pagina 40 da Sentenca] ---\nSecond chunk." in context
    assert chain.calls[0]["question"] == "Q?"


def test_generate_node_reinforces_grounding_on_retry(monkeypatch, docs):
    chain = FakeChain("answer")
    monkeypatch.setattr(nodes, "create_generator", lambda: chain)

    out = nodes.generate_node({"question": "Q?", "documents": docs, "generation_attempts": 1})

    assert out["generation_attempts"] == 2
    assert chain.calls[0]["question"].startswith("Q? (ATENCAO")


def test_generate_node_without_documents_uses_placeholder(monkeypatch):
    chain = FakeChain("answer")
    monkeypatch.setattr(nodes, "create_generator", lambda: chain)

    out = nodes.generate_node({"question": "Q?", "documents": []})

    assert out["citations"] == []
    assert chain.calls[0]["context"].startswith("Nenhum documento")


def test_grade_documents_node_filters_by_relevant_indices(monkeypatch, docs):
    grader = FakeChain(SimpleNamespace(relevant_indices=[1, 3], rationale="on topic"))
    monkeypatch.setattr(nodes, "create_batch_doc_grader", lambda: grader)

    out = nodes.grade_documents_node({"question": "Q?", "documents": docs})

    assert out["documents"] == [docs[0], docs[2]]
    assert "Trecho [2] (Pag 40): Second chunk." in grader.calls[0]["documents_batch"]


def test_grade_documents_node_approves_all_on_grader_error(monkeypatch, docs):
    monkeypatch.setattr(nodes, "create_batch_doc_grader", lambda: FakeChain(exc=RuntimeError("timeout")))
    assert nodes.grade_documents_node({"question": "Q?", "documents": docs})["documents"] == docs


def test_grade_documents_node_skips_grader_without_documents(monkeypatch):
    grader = FakeChain(SimpleNamespace(relevant_indices=[]))
    monkeypatch.setattr(nodes, "create_batch_doc_grader", lambda: grader)
    assert nodes.grade_documents_node({"question": "Q?", "documents": []}) == {"documents": []}
    assert grader.calls == []


def test_rewrite_query_node_increments_cycle_and_resets_attempts(monkeypatch):
    rewriter = FakeChain(SimpleNamespace(improved_query="ISA revenue share", rationale=""))
    monkeypatch.setattr(nodes, "create_query_rewriter", lambda: rewriter)

    out = nodes.rewrite_query_node({"question": "Q?", "retry_count": 1})

    assert out == {"current_query": "ISA revenue share", "retry_count": 2, "generation_attempts": 0}
