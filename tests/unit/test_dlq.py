"""Dead-letter queue: record shape and the jsonl / S3 / Azure Blob sinks."""

import json
from datetime import datetime
from unittest.mock import MagicMock

import boto3
import pytest
from langchain_core.documents import Document
from moto import mock_aws
from pydantic import SecretStr

from legal_rag.config import Settings
from legal_rag.storage import dlq
from legal_rag.storage.dlq import AzureBlobSink, JsonlSink, S3Sink, build_incident_record, build_sink, log_incident


@pytest.fixture
def record():
    docs = [
        Document(page_content="x" * 500, metadata={"page": 3, "source_file": "b.pdf"}),
        Document(page_content="short", metadata={"page": 7, "source_file": "a.pdf"}),
        Document(page_content="dup", metadata={"page": 8, "source_file": "a.pdf"}),
        Document(page_content="no source", metadata={"page": 9}),
    ]
    return build_incident_record("Q?", "bad answer", docs, "invented number", retry_count=2)


def test_build_incident_record(record):
    assert len(record["incident_id"]) == 32
    assert datetime.fromisoformat(record["timestamp"]).tzinfo is not None
    assert record["question"] == "Q?"
    assert record["rejected_generation"] == "bad answer"
    assert record["audit_summary"] == "invented number"
    assert record["retry_cycle"] == 2
    assert record["retrieved_pages"] == [3, 7, 8, 9]
    assert record["retrieved_sources"] == ["a.pdf", "b.pdf"]
    assert len(record["context_snippets"][0]) == 200
    assert record["context_snippets"][1] == "short"


def test_incident_ids_are_unique():
    assert (
        build_incident_record("q", "g", [], "", 0)["incident_id"]
        != build_incident_record("q", "g", [], "", 0)["incident_id"]
    )


def test_jsonl_sink_appends(tmp_path, record):
    path = tmp_path / "nested" / "incidents.jsonl"
    sink = JsonlSink(path)

    assert sink.write(record) == str(path)
    sink.write({**record, "incident_id": "second"})

    lines = path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["incident_id"] for line in lines] == [record["incident_id"], "second"]


def _expected_key(record):
    ts = datetime.fromisoformat(record["timestamp"])
    return f"incidents/{ts:%Y/%m/%d}/{record['incident_id']}.json"


@pytest.fixture
def aws(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")


def test_s3_sink_writes_date_partitioned_object(aws, record):
    aws.create_bucket(Bucket="dlq-test")
    sink = S3Sink("dlq-test", region="us-east-1")

    location = sink.write(record)

    key = _expected_key(record)
    assert location == f"s3://dlq-test/{key}"
    obj = aws.get_object(Bucket="dlq-test", Key=key)
    assert obj["ContentType"] == "application/json"
    assert json.loads(obj["Body"].read()) == record


def test_azure_blob_sink_uploads_blob(record):
    service = MagicMock()
    sink = AzureBlobSink("unused", "dlq-container", service_client=service)

    location = sink.write(record)

    key = _expected_key(record)
    service.get_container_client.assert_called_once_with("dlq-container")
    upload = service.get_container_client.return_value.upload_blob
    upload.assert_called_once()
    kwargs = upload.call_args.kwargs
    assert kwargs["name"] == key
    assert json.loads(kwargs["data"]) == record
    assert kwargs["overwrite"] is False
    assert location == f"azure://dlq-container/{key}"


def test_build_sink_defaults_to_jsonl():
    assert isinstance(build_sink(Settings(_env_file=None, dlq_backend="jsonl")), JsonlSink)


def test_build_sink_s3(aws):
    sink = build_sink(Settings(_env_file=None, dlq_backend="s3", dlq_s3_bucket="bucket-x"))
    assert isinstance(sink, S3Sink)
    assert sink.bucket == "bucket-x"


def test_build_sink_azure_blob(monkeypatch):
    service = MagicMock()
    from azure.storage.blob import BlobServiceClient

    monkeypatch.setattr(BlobServiceClient, "from_connection_string", MagicMock(return_value=service))
    settings = Settings(
        _env_file=None,
        dlq_backend="azure_blob",
        dlq_azure_container="c1",
        azure_storage_connection_string=SecretStr("UseDevelopmentStorage=true"),
    )

    sink = build_sink(settings)

    assert isinstance(sink, AzureBlobSink)
    BlobServiceClient.from_connection_string.assert_called_once_with("UseDevelopmentStorage=true")
    service.get_container_client.assert_called_once_with("c1")


def test_build_sink_azure_blob_requires_connection_string():
    with pytest.raises(ValueError, match="AZURE_STORAGE_CONNECTION_STRING"):
        build_sink(Settings(_env_file=None, dlq_backend="azure_blob", azure_storage_connection_string=None))


def test_log_incident_writes_to_given_sink(record):
    sink = MagicMock()
    log_incident(record, sink=sink)
    sink.write.assert_called_once_with(record)


def test_log_incident_uses_configured_sink(_isolated_dlq, record):
    log_incident(record)
    assert json.loads(_isolated_dlq.path.read_text(encoding="utf-8"))["incident_id"] == record["incident_id"]


def test_log_incident_swallows_sink_errors(monkeypatch, record):
    failing = MagicMock()
    failing.write.side_effect = ConnectionError("S3 unavailable")
    log_incident(record, sink=failing)  # must not raise

    monkeypatch.setattr(dlq, "get_sink", MagicMock(side_effect=ValueError("bad config")))
    log_incident(record)  # misconfigured backend must not raise either
