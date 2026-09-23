"""
Request/response contracts of the HTTP API (Pydantic v2).

The examples declared here are rendered in the OpenAPI schema (/docs, /openapi.json).
"""

from datetime import date
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=2000)]


class QueryRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "question": "Qual era a porcentagem da receita que o Google repassava para a Apple no contrato ISA?",
                    "as_of_date": "2024-08-05",
                }
            ]
        }
    )

    question: Question = Field(description="Investigative question about the U.S. v. Google opinion")
    as_of_date: Optional[date] = Field(
        default=None,
        description="Point-in-time cutoff (YYYY-MM-DD): only evidence available on this date is considered",
    )


class QueryResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "request_id": "3f2b9c1e8a4d4f6e9b7a0c1d2e3f4a5b",
                    "answer": "Under the ISA, Google paid Apple 36% of the net search advertising revenue...",
                    "citations": ["22", "23"],
                    "hallucination_verdict": "grounded",
                    "answer_verdict": "useful",
                    "retry_count": 0,
                    "fallback": False,
                    "latency_ms": 41250,
                }
            ]
        }
    )

    request_id: str = Field(description="Correlation id (echoed in the X-Request-ID header)")
    answer: str = Field(description="Audited answer, or a safe abstention when the agent falls back")
    citations: list[str] = Field(default_factory=list, description="Opinion page numbers supporting the answer")
    hallucination_verdict: Optional[str] = Field(default=None, description="'grounded', 'hallucinated' or 'abstained'")
    answer_verdict: Optional[str] = Field(default=None, description="'useful', 'not_useful' or 'fallback'")
    retry_count: int = Field(description="Number of self-correction cycles executed")
    fallback: bool = Field(description="True when the agent abstained instead of answering")
    latency_ms: int = Field(description="Server-side processing time in milliseconds")


class HealthResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "ok"}]})

    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "ready", "vectors": 1081}]})

    status: Literal["ready"] = "ready"
    vectors: int = Field(description="Number of vectors indexed in the Gold layer")


class NotReadyResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"status": "not_ready", "detail": "gold vector store is empty"}]}
    )

    status: Literal["not_ready"] = "not_ready"
    detail: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"detail": "internal error", "request_id": "3f2b9c1e8a4d4f6e9b7a0c1d2e3f4a5b"}]}
    )

    detail: str
    request_id: Optional[str] = None
