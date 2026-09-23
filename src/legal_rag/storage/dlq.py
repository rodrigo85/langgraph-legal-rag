"""
Dead-Letter Queue (DLQ) for hallucination incidents.

Each rejected draft is persisted as an immutable JSON record so it can be audited
and later turned into DPO preference pairs. The sink is chosen by configuration:

    DLQ_BACKEND = jsonl       -> local append-only file (development)
    DLQ_BACKEND = s3          -> Amazon S3 (LocalStack locally)
    DLQ_BACKEND = azure_blob  -> Azure Blob Storage (Azurite locally)

Object-storage sinks write one object per incident, partitioned by date
(incidents/YYYY/MM/DD/<id>.json), which is query-friendly for Athena / Synapse.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Protocol

from legal_rag.config import HALLUCINATIONS_LOG_PATH, Settings, get_settings

logger = logging.getLogger(__name__)


class IncidentSink(Protocol):
    def write(self, record: Dict[str, Any]) -> str:
        """Persists one incident and returns its location."""


def _object_key(record: Dict[str, Any]) -> str:
    ts = datetime.fromisoformat(record["timestamp"])
    return f"incidents/{ts:%Y/%m/%d}/{record['incident_id']}.json"


class JsonlSink:
    def __init__(self, path: Path):
        self.path = path

    def write(self, record: Dict[str, Any]) -> str:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return str(self.path)


class S3Sink:
    def __init__(self, bucket: str, region: str, endpoint_url: str | None = None, client=None):
        if client is None:
            import boto3

            client = boto3.client("s3", region_name=region, endpoint_url=endpoint_url)
        self.client = client
        self.bucket = bucket

    def write(self, record: Dict[str, Any]) -> str:
        key = _object_key(record)
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(record, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )
        return f"s3://{self.bucket}/{key}"


class AzureBlobSink:
    def __init__(self, connection_string: str, container: str, service_client=None):
        if service_client is None:
            from azure.storage.blob import BlobServiceClient

            service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_client = service_client.get_container_client(container)
        self.container = container

    def write(self, record: Dict[str, Any]) -> str:
        key = _object_key(record)
        self.container_client.upload_blob(
            name=key,
            data=json.dumps(record, ensure_ascii=False).encode("utf-8"),
            overwrite=False,
        )
        return f"azure://{self.container}/{key}"


def build_sink(settings: Settings | None = None) -> IncidentSink:
    settings = settings or get_settings()
    if settings.dlq_backend == "s3":
        return S3Sink(settings.dlq_s3_bucket, settings.aws_region, settings.aws_endpoint_url)
    if settings.dlq_backend == "azure_blob":
        if settings.azure_storage_connection_string is None:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING is required for the azure_blob DLQ backend")
        return AzureBlobSink(
            settings.azure_storage_connection_string.get_secret_value(),
            settings.dlq_azure_container,
        )
    return JsonlSink(HALLUCINATIONS_LOG_PATH)


@lru_cache
def get_sink() -> IncidentSink:
    return build_sink()


def build_incident_record(
    question: str,
    generation: str,
    documents: list,
    audit_summary: str,
    retry_count: int,
) -> Dict[str, Any]:
    return {
        "incident_id": uuid.uuid4().hex,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "retry_cycle": retry_count,
        "rejected_generation": generation,
        "audit_summary": audit_summary,
        "retrieved_pages": [d.metadata.get("page") for d in documents if hasattr(d, "metadata")],
        "retrieved_sources": sorted({d.metadata.get("source_file") for d in documents if hasattr(d, "metadata")} - {None}),
        "context_snippets": [d.page_content[:200] for d in documents if hasattr(d, "page_content")],
    }


def log_incident(record: Dict[str, Any], sink: IncidentSink | None = None) -> None:
    """Writes an incident without ever breaking the request path."""
    try:
        location = (sink or get_sink()).write(record)
        logger.info("dlq.incident_logged", extra={"incident_id": record["incident_id"], "location": location})
    except Exception:
        logger.exception("dlq.write_failed", extra={"incident_id": record.get("incident_id")})
