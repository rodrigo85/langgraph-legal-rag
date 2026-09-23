"""Shared fixtures: isolate cached settings/sinks and keep the repository's DLQ file untouched."""

import pytest

from legal_rag import config
from legal_rag.storage import dlq

# Captured at import time so cache_clear still works while a test has monkeypatched them.
_get_settings = config.get_settings
_get_sink = dlq.get_sink


@pytest.fixture(autouse=True)
def _reset_caches():
    _get_settings.cache_clear()
    _get_sink.cache_clear()
    yield
    _get_settings.cache_clear()
    _get_sink.cache_clear()


@pytest.fixture(autouse=True)
def _isolated_dlq(tmp_path, monkeypatch):
    """Routes incidents to a per-test JSONL file instead of data/logs/."""
    sink = dlq.JsonlSink(tmp_path / "dlq" / "incidents.jsonl")
    monkeypatch.setattr(dlq, "get_sink", lambda: sink)
    return sink
