"""
Unit tests for the HTTP API (no network, no Ollama, no vector store).

The graph, readiness check and settings are injected through `create_app`.
"""

import threading

import pytest
from fastapi.testclient import TestClient

from legal_rag.api.main import create_app
from legal_rag.config import Settings

FINAL_STATE = {
    "generation": "Google paid Apple 36% of net search advertising revenue under the ISA.",
    "citations": ["22", "23"],
    "hallucination_verdict": "grounded",
    "answer_verdict": "useful",
    "retry_count": 1,
}


class FakeGraph:
    """Stands in for the compiled LangGraph: records the initial state and returns a canned final state."""

    def __init__(self, final_state=None, error=None, block=None):
        self.final_state = final_state or FINAL_STATE
        self.error = error
        self.block = block
        self.calls = []

    def invoke(self, state):
        self.calls.append(state)
        if self.block is not None:
            self.block.wait(timeout=10)
        if self.error is not None:
            raise self.error
        return {**state, **self.final_state}


def make_client(graph=None, readiness_check=lambda: 1081, **settings_overrides):
    settings = Settings(**{"api_key": None, "request_timeout_seconds": 30, **settings_overrides})
    graph = graph or FakeGraph()
    app = create_app(graph_factory=lambda: graph, readiness_check=readiness_check, settings=settings)
    return TestClient(app), graph


@pytest.fixture
def client():
    test_client, graph = make_client()
    with test_client:
        yield test_client, graph


def test_health(client):
    test_client, _ = client
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready(client):
    test_client, _ = client
    response = test_client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "vectors": 1081}


@pytest.mark.parametrize("check", [lambda: 0, lambda: (_ for _ in ()).throw(RuntimeError("db down"))])
def test_not_ready(check):
    test_client, _ = make_client(readiness_check=check)
    with test_client:
        response = test_client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert "db down" not in body["detail"]


def test_query_success(client):
    test_client, graph = client
    response = test_client.post("/v1/query", json={"question": "  Qual era a porcentagem do ISA?  "})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == FINAL_STATE["generation"]
    assert body["citations"] == ["22", "23"]
    assert body["hallucination_verdict"] == "grounded"
    assert body["answer_verdict"] == "useful"
    assert body["retry_count"] == 1
    assert body["fallback"] is False
    assert isinstance(body["latency_ms"], int)
    assert len(body["request_id"]) == 32
    assert response.headers["X-Request-ID"] == body["request_id"]

    state = graph.calls[0]
    assert state["question"] == state["current_query"] == "Qual era a porcentagem do ISA?"
    assert state["generation_attempts"] == 0
    assert state["retry_count"] == 0
    assert "as_of_date" not in state


def test_query_passes_as_of_date_and_flags_fallback():
    graph = FakeGraph(final_state={"generation": "abstained", "answer_verdict": "fallback", "citations": []})
    test_client, _ = make_client(graph=graph)
    with test_client:
        response = test_client.post("/v1/query", json={"question": "Pergunta?", "as_of_date": "2024-08-05"})
    assert response.status_code == 200
    assert response.json()["fallback"] is True
    assert graph.calls[0]["as_of_date"] == "2024-08-05"


def test_incoming_request_id_is_preserved(client):
    test_client, _ = client
    response = test_client.post("/v1/query", json={"question": "Pergunta?"}, headers={"X-Request-ID": "abc-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "abc-123"
    assert response.json()["request_id"] == "abc-123"


@pytest.mark.parametrize("payload", [{"question": "  a "}, {"question": "x" * 2001}, {}])
def test_query_validation(client, payload):
    test_client, graph = client
    response = test_client.post("/v1/query", json=payload)
    assert response.status_code == 422
    assert "X-Request-ID" in response.headers
    assert graph.calls == []


def test_api_key_enforced():
    test_client, _ = make_client(api_key="s3cret")
    with test_client:
        assert test_client.post("/v1/query", json={"question": "Pergunta?"}).status_code == 401
        wrong = test_client.post("/v1/query", json={"question": "Pergunta?"}, headers={"X-API-Key": "nope"})
        assert wrong.status_code == 401
        ok = test_client.post("/v1/query", json={"question": "Pergunta?"}, headers={"X-API-Key": "s3cret"})
        assert ok.status_code == 200
        # Probes stay unauthenticated for the load balancer
        assert test_client.get("/health").status_code == 200
        assert test_client.get("/ready").status_code == 200


def test_query_timeout_returns_504():
    release = threading.Event()
    test_client, _ = make_client(graph=FakeGraph(block=release), request_timeout_seconds=1)
    with test_client:
        try:
            response = test_client.post("/v1/query", json={"question": "Pergunta lenta?"})
        finally:
            release.set()  # let the abandoned worker thread finish before the event loop closes
    assert response.status_code == 504
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_graph_error_returns_500_without_traceback():
    test_client, _ = make_client(graph=FakeGraph(error=RuntimeError("secret internal detail")))
    with test_client:
        response = test_client.post("/v1/query", json={"question": "Pergunta?"})
    assert response.status_code == 500
    body = response.json()
    assert body == {"detail": "internal error", "request_id": response.headers["X-Request-ID"]}
    assert "Traceback" not in response.text
    assert "secret internal detail" not in response.text


def test_openapi_schema_has_examples(client):
    test_client, _ = client
    schema = test_client.get("/openapi.json").json()
    assert schema["info"]["version"] == "1.0.0"
    assert schema["components"]["schemas"]["QueryRequest"]["examples"]
