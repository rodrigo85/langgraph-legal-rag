.PHONY: help install bronze silver gold pipeline specialize evolution test benchmark run clean

help:
	@echo "Available commands (data pipeline and RAG agent):"
	@echo "  make install      - Install all dependencies (run inside a virtual environment)"
	@echo "  make bronze       - Raw ingestion (download the court PDFs into data/raw)"
	@echo "  make silver       - Parsing, cleaning and lineage metadata (data/processed)"
	@echo "  make gold         - Chunking and idempotent indexing into ChromaDB"
	@echo "  make pipeline     - Run the full data pipeline (Bronze -> Silver -> Gold)"
	@echo "  make specialize   - Generate datasets and register the Modelfile-specialized models in Ollama"
	@echo "  make evolution    - Run the 3-generation A/B benchmark and write the evolution report"
	@echo "  make test         - Run the test suite (requires Ollama and the Gold index)"
	@echo "  make benchmark    - Run the Naive RAG vs Self-RAG benchmark"
	@echo "  make run          - Start the interactive CLI"
	@echo "  make clean        - Remove Python caches"

install:
	pip install -r requirements-dev.txt

bronze:
	python src/pipeline/downloader.py

silver:
	python src/pipeline/parser.py

gold:
	python src/pipeline/indexer.py

pipeline: bronze silver gold
	@echo "[OK] Data pipeline finished."

specialize:
	python src/training/dataset_generator.py
	python src/training/register_models.py

evolution:
	python src/evaluation/eval_3_generations.py

test:
	python -m pytest tests -v -s

benchmark:
	python src/evaluation/benchmark.py

run:
	python src/cli.py

clean:
	find . -name __pycache__ -type d -not -path "./.venv/*" -prune -exec rm -rf {} +
	rm -rf .pytest_cache
