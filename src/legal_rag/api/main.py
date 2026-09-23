"""
FastAPI service exposing the self-correcting RAG agent over HTTP.

    GET  /health    liveness probe (no dependencies)
    GET  /ready     readiness probe (Gold vector store populated)
    POST /v1/query  runs the LangGraph agent for one question

Run locally with `legal-rag-api` (or `uvicorn legal_rag.api.main:app`). The same image runs on
AWS (ECS/Fargate behind an ALB) and Azure (Container Apps): configuration comes from env vars.
"""

import contextvars
import logging
import os
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Any, Callable, Optional

import anyio
import anyio.to_thread
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from starlette.concurrency import run_in_threadpool
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from legal_rag.agent.graph import build_graph
from legal_rag.api.schemas import (
    ErrorResponse,
    HealthResponse,
    NotReadyResponse,
    QueryRequest,
    QueryResponse,
    ReadyResponse,
)
from legal_rag.config import Settings, get_settings
from legal_rag.observability import configure_logging, configure_tracing, get_tracer, request_id_var

logger = logging.getLogger(__name__)
access_logger = logging.getLogger("legal_rag.api.access")

REQUEST_ID_HEADER = "X-Request-ID"
API_VERSION = "1.0.0"

ReadinessCheck = Callable[[], int]


# ==============================================================================
# Middleware: request correlation + structured access log
# ==============================================================================
class RequestContextMiddleware:
    """Pure ASGI middleware: propagates X-Request-ID, logs one access line and shields 500s."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope["headers"]).get(REQUEST_ID_HEADER.lower().encode())
        request_id = incoming.decode("latin-1")[:128] if incoming else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500
        response_started = False

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"x-request-id"]
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            # Safety net for anything the routes did not handle: never leak a stack trace to the client
            logger.exception("http.unhandled_error")
            if not response_started:
                response = JSONResponse(status_code=500, content={"detail": "internal error", "request_id": request_id})
                await response(scope, receive, send_with_request_id)
        finally:
            access_logger.info(
                "http.request",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            request_id_var.reset(token)


# ==============================================================================
# Dependencies
# ==============================================================================
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False, description="Required when API_KEY is set")


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def require_api_key(request: Request, api_key: Annotated[Optional[str], Security(_api_key_header)]) -> None:
    """Enforces X-API-Key only when an API key is configured (constant-time comparison)."""
    expected = get_app_settings(request).api_key
    if expected is None:
        return
    if api_key is None or not secrets.compare_digest(
        api_key.encode("utf-8"), expected.get_secret_value().encode("utf-8")
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or missing API key")


def vector_store_readiness(settings: Settings) -> ReadinessCheck:
    """Default readiness check: counts Gold vectors, caching the first positive result."""
    ready_count: Optional[int] = None

    def check() -> int:
        nonlocal ready_count
        if ready_count is None:
            from legal_rag.storage.vector_store import count_vectors, get_vector_store

            count = count_vectors(get_vector_store(settings))
            if count > 0:
                ready_count = count
            return count
        return ready_count

    return check


# ==============================================================================
# Application factory
# ==============================================================================
def create_app(
    graph_factory: Callable[[], Any] = build_graph,
    readiness_check: Optional[ReadinessCheck] = None,
    settings: Optional[Settings] = None,
) -> FastAPI:
    """Builds the FastAPI app. Tests inject a fake graph factory, readiness check and settings."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging(settings)
        # The graph is compiled once per process and shared by all requests (it is stateless)
        app.state.graph = graph_factory()
        logger.info("api.startup", extra={"version": API_VERSION, "auth": settings.api_key is not None})
        yield
        logger.info("api.shutdown")

    app = FastAPI(
        title="Legal RAG API",
        description=(
            "Self-correcting RAG (LangGraph) over the U.S. v. Google antitrust opinion. "
            "Answers are audited for grounding and cite opinion pages; the agent abstains instead of hallucinating."
        ),
        version=API_VERSION,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "ops", "description": "Liveness and readiness probes"},
            {"name": "query", "description": "Question answering over the opinion"},
        ],
    )
    app.state.settings = settings
    app.state.readiness_check = readiness_check or vector_store_readiness(settings)
    app.add_middleware(RequestContextMiddleware)

    # Tracing must be wired here, not in the lifespan: the OTel FastAPI instrumentation patches the
    # middleware stack, which Starlette builds on the first ASGI call (the lifespan call itself).
    configure_tracing(app, settings)

    @app.get("/health", response_model=HealthResponse, tags=["ops"], summary="Liveness probe")
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.get(
        "/ready",
        response_model=ReadyResponse,
        responses={503: {"model": NotReadyResponse}},
        tags=["ops"],
        summary="Readiness probe (Gold vector store populated)",
    )
    async def ready(request: Request):
        try:
            vectors = await run_in_threadpool(request.app.state.readiness_check)
        except Exception:
            logger.exception("api.readiness_failed")
            return _not_ready("vector store unavailable")
        if vectors <= 0:
            return _not_ready("gold vector store is empty")
        return ReadyResponse(vectors=vectors)

    router = APIRouter(prefix="/v1", tags=["query"], dependencies=[Depends(require_api_key)])

    @router.post(
        "/query",
        response_model=QueryResponse,
        responses={
            401: {"model": ErrorResponse, "description": "Missing or invalid API key"},
            500: {"model": ErrorResponse, "description": "Unexpected error"},
            504: {"model": ErrorResponse, "description": "Agent exceeded REQUEST_TIMEOUT_SECONDS"},
        },
        summary="Ask the self-correcting RAG agent a question",
    )
    async def query(body: QueryRequest, request: Request, app_settings: Annotated[Settings, Depends(get_app_settings)]):
        request_id = request_id_var.get()
        started = time.perf_counter()
        state = _initial_state(body, app_settings)
        graph = request.app.state.graph

        tracer = get_tracer(__name__)
        final_state: Optional[dict[str, Any]] = None
        try:
            with tracer.start_as_current_span("graph.invoke") as span:
                if span is not None:
                    span.set_attribute("request_id", request_id)
                # Copy the context so the request id and the active span are visible inside the worker thread
                ctx = contextvars.copy_context()
                with anyio.move_on_after(app_settings.request_timeout_seconds):
                    # abandon_on_cancel: answer 504 right away; the blocking invoke finishes in the background
                    final_state = await anyio.to_thread.run_sync(ctx.run, graph.invoke, state, abandon_on_cancel=True)
                if span is not None and final_state is not None:
                    span.set_attribute("retry_count", int(final_state.get("retry_count", 0) or 0))
                    span.set_attribute("answer_verdict", str(final_state.get("answer_verdict")))
        except Exception:
            logger.exception("api.query_failed")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "internal error", "request_id": request_id},
            )
        if final_state is None:
            logger.warning("api.query_timeout", extra={"timeout_s": app_settings.request_timeout_seconds})
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={"detail": "agent timed out", "request_id": request_id},
            )

        answer_verdict = final_state.get("answer_verdict")
        response = QueryResponse(
            request_id=request_id,
            answer=final_state.get("generation") or "",
            citations=[str(c) for c in final_state.get("citations") or []],
            hallucination_verdict=final_state.get("hallucination_verdict"),
            answer_verdict=answer_verdict,
            retry_count=int(final_state.get("retry_count", 0) or 0),
            fallback=answer_verdict == "fallback",
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        logger.info(
            "api.query_completed",
            extra={
                "answer_verdict": answer_verdict,
                "retry_count": response.retry_count,
                "citations": len(response.citations),
                "latency_ms": response.latency_ms,
            },
        )
        return response

    app.include_router(router)
    return app


def _not_ready(detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=NotReadyResponse(detail=detail).model_dump()
    )


def _initial_state(body: QueryRequest, settings: Settings) -> dict[str, Any]:
    """Same initial state as the CLI, plus the optional point-in-time cutoff."""
    state: dict[str, Any] = {
        "question": body.question,
        "current_query": body.question,
        "documents": [],
        "generation": "",
        "generation_attempts": 0,
        "retry_count": 0,
        "max_retries": settings.max_retries,
        "web_search_needed": False,
        "hallucination_verdict": None,
        "answer_verdict": None,
        "citations": [],
    }
    if body.as_of_date is not None:
        state["as_of_date"] = body.as_of_date.isoformat()
    return state


app = create_app()


def run() -> None:
    """Console entry point (`legal-rag-api`): serves the app with uvicorn on 0.0.0.0:$PORT."""
    import uvicorn

    configure_logging()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        log_config=None,  # keep our structured root handler instead of uvicorn's formatters
        access_log=False,  # RequestContextMiddleware already emits one access line per request
        proxy_headers=True,  # honor X-Forwarded-* from the ALB / Container Apps ingress
    )


if __name__ == "__main__":
    run()
