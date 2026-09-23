"""Routing gates and the anti-infinite-loop guarantee of the self-correcting DAG."""

from types import SimpleNamespace

import pytest
from langchain_core.documents import Document

from legal_rag.agent import edges, nodes
from legal_rag.agent.edges import decide_to_generate, grade_generation_v_documents_and_question
from legal_rag.agent.graph import build_graph

MAX = 3


@pytest.fixture(autouse=True)
def _fixed_max_retries(monkeypatch):
    monkeypatch.setattr(edges, "MAX_RETRIES", MAX)


@pytest.fixture
def docs():
    return [
        Document(
            page_content="Google paid Apple 36% of search revenue.", metadata={"page": 12, "source_file": "a.pdf"}
        ),
        Document(page_content="The ISA was renewed in 2016.", metadata={"page": 40, "source_file": "a.pdf"}),
    ]


class FakeGrader:
    def __init__(self, verdict=None, exc=None):
        self.verdict = verdict
        self.exc = exc
        self.calls = []

    def invoke(self, payload):
        self.calls.append(payload)
        if self.exc:
            raise self.exc
        return self.verdict


def audit(grounded="yes", useful="yes", summary="ok"):
    return SimpleNamespace(is_grounded=grounded, is_useful=useful, audit_summary=summary)


@pytest.fixture
def incidents(monkeypatch):
    records = []
    monkeypatch.setattr(edges, "log_incident", records.append)
    return records


def use_grader(monkeypatch, grader):
    monkeypatch.setattr(edges, "create_unified_quality_grader", lambda: grader)
    return grader


def state(docs, retry_count=0, generation_attempts=1):
    return {
        "question": "What did Google pay Apple?",
        "generation": "36% [Pag. 12]",
        "documents": docs,
        "retry_count": retry_count,
        "generation_attempts": generation_attempts,
    }


# --- decide_to_generate --------------------------------------------------------


def test_decide_no_docs_with_retries_left_rewrites():
    assert decide_to_generate({"documents": [], "retry_count": MAX - 1}) == "rewrite_query"


def test_decide_no_docs_retries_exhausted_falls_back():
    assert decide_to_generate({"documents": [], "retry_count": MAX}) == "fallback"


def test_decide_with_docs_generates(docs):
    assert decide_to_generate({"documents": docs, "retry_count": MAX}) == "generate"


# --- grade_generation_v_documents_and_question ---------------------------------


def test_grounded_and_useful_ends(monkeypatch, docs, incidents):
    grader = use_grader(monkeypatch, FakeGrader(audit()))
    assert grade_generation_v_documents_and_question(state(docs)) == "useful"
    assert "[Pagina 12]" in grader.calls[0]["documents"]
    assert incidents == []


def test_not_grounded_first_attempt_regenerates(monkeypatch, docs, incidents):
    use_grader(monkeypatch, FakeGrader(audit(grounded="no")))
    assert grade_generation_v_documents_and_question(state(docs, generation_attempts=1)) == "not_grounded"


def test_not_grounded_second_attempt_rewrites(monkeypatch, docs, incidents):
    use_grader(monkeypatch, FakeGrader(audit(grounded="no")))
    assert grade_generation_v_documents_and_question(state(docs, generation_attempts=2)) == "not_useful"


def test_not_grounded_retries_exhausted_falls_back(monkeypatch, docs, incidents):
    use_grader(monkeypatch, FakeGrader(audit(grounded="no")))
    result = grade_generation_v_documents_and_question(state(docs, retry_count=MAX, generation_attempts=1))
    assert result == "fallback"


@pytest.mark.parametrize(("retry_count", "expected"), [(0, "not_useful"), (MAX, "fallback")])
def test_not_useful(monkeypatch, docs, incidents, retry_count, expected):
    use_grader(monkeypatch, FakeGrader(audit(useful="no")))
    assert grade_generation_v_documents_and_question(state(docs, retry_count=retry_count)) == expected
    assert incidents == []  # unhelpful is not a hallucination


def test_no_documents_falls_back(monkeypatch, incidents):
    grader = use_grader(monkeypatch, FakeGrader(audit()))
    assert grade_generation_v_documents_and_question(state([])) == "fallback"
    assert grader.calls == []


def test_grader_error_fails_closed_with_retry(monkeypatch, docs, incidents):
    use_grader(monkeypatch, FakeGrader(exc=RuntimeError("LLM down")))
    assert grade_generation_v_documents_and_question(state(docs)) == "not_grounded"
    assert incidents == []


def test_grader_error_fails_closed_to_fallback_when_exhausted(monkeypatch, docs, incidents):
    use_grader(monkeypatch, FakeGrader(exc=RuntimeError("LLM down")))
    assert grade_generation_v_documents_and_question(state(docs, retry_count=MAX, generation_attempts=2)) == "fallback"
    assert incidents == []


def test_malformed_grader_output_fails_closed(monkeypatch, docs, incidents):
    use_grader(monkeypatch, FakeGrader(audit(grounded="maybe")))
    assert grade_generation_v_documents_and_question(state(docs)) == "not_grounded"
    assert incidents == []


def test_dict_grader_output_is_supported(monkeypatch, docs, incidents):
    use_grader(monkeypatch, FakeGrader({"is_grounded": "yes", "is_useful": "yes", "audit_summary": "ok"}))
    assert grade_generation_v_documents_and_question(state(docs)) == "useful"


def test_state_max_retries_overrides_default(monkeypatch, docs, incidents):
    use_grader(monkeypatch, FakeGrader(audit(grounded="no")))
    per_request = {**state(docs, retry_count=1, generation_attempts=2), "max_retries": 1}
    assert grade_generation_v_documents_and_question(per_request) == "fallback"


def test_hallucination_is_written_to_dlq(monkeypatch, docs, incidents):
    use_grader(monkeypatch, FakeGrader(audit(grounded="no", summary="36% not in context")))
    grade_generation_v_documents_and_question(state(docs, retry_count=1))

    assert len(incidents) == 1
    record = incidents[0]
    assert record["question"] == "What did Google pay Apple?"
    assert record["rejected_generation"] == "36% [Pag. 12]"
    assert record["audit_summary"] == "36% not in context"
    assert record["retry_cycle"] == 1
    assert record["retrieved_pages"] == [12, 40]
    assert record["retrieved_sources"] == ["a.pdf"]
    assert record["incident_id"] and record["timestamp"]


# --- Whole-graph loop bound ------------------------------------------------------


class FakeRetriever:
    def __init__(self, docs):
        self.docs = docs

    def invoke(self, _query):
        return list(self.docs)


@pytest.mark.parametrize("max_retries", [0, 1, 3])
def test_graph_always_terminates_in_fallback_when_never_grounded(monkeypatch, docs, incidents, max_retries):
    monkeypatch.setattr(edges, "MAX_RETRIES", max_retries)
    store = SimpleNamespace(as_retriever=lambda **_: FakeRetriever(docs))
    monkeypatch.setattr(nodes, "load_or_build_gold_vectorstore", lambda: store)
    monkeypatch.setattr(nodes, "get_temporal_retriever", lambda **_: FakeRetriever(docs))
    monkeypatch.setattr(
        nodes, "create_batch_doc_grader", lambda: FakeGrader(SimpleNamespace(relevant_indices=[1, 2], rationale=""))
    )
    monkeypatch.setattr(
        nodes,
        "create_query_rewriter",
        lambda: FakeGrader(SimpleNamespace(improved_query="ISA revenue share", rationale="")),
    )
    monkeypatch.setattr(nodes, "create_generator", lambda: FakeGrader("Invented answer."))
    grader = use_grader(monkeypatch, FakeGrader(audit(grounded="no")))

    result = build_graph().invoke(
        {
            "question": "q",
            "current_query": "q",
            "documents": [],
            "generation": "",
            "generation_attempts": 0,
            "retry_count": 0,
        },
        {"recursion_limit": 50},
    )

    assert result["answer_verdict"] == "fallback"
    assert result["hallucination_verdict"] == "abstained"
    assert result["retry_count"] == max_retries
    # Two generations per chunk set while retries remain, plus one on the final set.
    assert len(grader.calls) == 2 * max_retries + 1
    assert len(incidents) == len(grader.calls)


@pytest.mark.parametrize("max_retries", [0, 2])
def test_graph_terminates_when_retrieval_never_finds_chunks(monkeypatch, incidents, max_retries):
    monkeypatch.setattr(edges, "MAX_RETRIES", max_retries)
    store = SimpleNamespace(as_retriever=lambda **_: FakeRetriever([]))
    monkeypatch.setattr(nodes, "load_or_build_gold_vectorstore", lambda: store)
    rewriter = FakeGrader(SimpleNamespace(improved_query="ISA revenue share", rationale=""))
    monkeypatch.setattr(nodes, "create_query_rewriter", lambda: rewriter)
    grader = use_grader(monkeypatch, FakeGrader(audit()))

    result = build_graph().invoke({"question": "q", "current_query": "q", "retry_count": 0}, {"recursion_limit": 50})

    assert result["answer_verdict"] == "fallback"
    assert result["retry_count"] == max_retries
    assert len(rewriter.calls) == max_retries
    assert grader.calls == []


def test_graph_records_verdicts_when_answer_passes(monkeypatch, docs, incidents):
    retriever = SimpleNamespace(invoke=lambda query: docs)
    monkeypatch.setattr(
        nodes, "load_or_build_gold_vectorstore", lambda: SimpleNamespace(as_retriever=lambda **_: retriever)
    )
    monkeypatch.setattr(
        nodes, "create_batch_doc_grader", lambda: FakeGrader(SimpleNamespace(relevant_indices=[1, 2], rationale="ok"))
    )
    monkeypatch.setattr(nodes, "create_generator", lambda: SimpleNamespace(invoke=lambda payload: "36% [Pag. 12]"))
    use_grader(monkeypatch, FakeGrader(audit()))

    result = build_graph().invoke(
        {"question": "What did Google pay Apple?", "retry_count": 0, "generation_attempts": 0}
    )

    assert result["hallucination_verdict"] == "grounded"
    assert result["answer_verdict"] == "useful"
    assert result["citations"] == ["12", "40"]
