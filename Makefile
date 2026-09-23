.PHONY: help install lint format test test-integration bronze silver gold pipeline specialize evolution benchmark audit run api up up-azure index down logs clean

help:
	@echo "Development"
	@echo "  make install           Install the package with all extras (run inside a virtualenv)"
	@echo "  make lint | format     Ruff lint / format"
	@echo "  make test              Unit tests (no Ollama, no Docker)"
	@echo "  make test-integration  Integration tests (requires Ollama and an indexed Gold layer)"
	@echo "Data pipeline"
	@echo "  make pipeline          Bronze (download) -> Silver (parse) -> Gold (index)"
	@echo "  make specialize        Generate datasets and register the Modelfile-specialized models in Ollama"
	@echo "  make evolution         3-generation A/B benchmark and evolution report"
	@echo "  make benchmark         Naive RAG vs Self-RAG benchmark"
	@echo "  make audit             Cross-layer data quality audit"
	@echo "Run"
	@echo "  make run               Interactive CLI"
	@echo "  make api               FastAPI on http://localhost:8000/docs"
	@echo "Local production simulation (Docker)"
	@echo "  make up                API + pgvector + LocalStack S3 + Jaeger (AWS-like)"
	@echo "  make up-azure          Same stack with the DLQ on Azurite Blob (Azure-like)"
	@echo "  make index             Build the Gold layer inside pgvector"
	@echo "  make logs | down       Follow API logs / stop the stack"

install:
	pip install -e ".[dev]"

lint:
	ruff check src tests

format:
	ruff format src tests

test:
	pytest -q

test-integration:
	pytest -q -m integration

bronze:
	python -m legal_rag.pipeline.downloader

silver:
	python -m legal_rag.pipeline.parser

gold:
	python -m legal_rag.pipeline.indexer

pipeline: bronze silver gold

specialize:
	python -m legal_rag.training.dataset_generator
	python -m legal_rag.training.register_models

evolution:
	python -m legal_rag.evaluation.eval_3_generations

benchmark:
	python -m legal_rag.evaluation.benchmark

audit:
	python -m legal_rag.evaluation.data_quality_audit

run:
	legal-rag

api:
	legal-rag-api

up:
	docker compose up -d --build

up-azure:
	DLQ_BACKEND=azure_blob docker compose up -d --build

index:
	docker compose --profile jobs run --rm indexer

logs:
	docker compose logs -f api

down:
	docker compose down

clean:
	find . -name __pycache__ -type d -not -path "./.venv/*" -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache
