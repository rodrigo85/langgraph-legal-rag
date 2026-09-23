.PHONY: help install bronze silver gold pipeline test benchmark run clean

help:
	@echo "Comandos disponiveis no Pipeline de Dados e Agente RAG:"
	@echo "  make install      - Instala todas as dependencias em ambiente virtual"
	@echo "  make bronze       - Ingestao bruta (Download do PDF judicial para data/raw)"
	@echo "  make silver       - Processamento, limpeza e metadados de linhagem (data/processed)"
	@echo "  make gold         - Chunking semantico e indexacao idempotente no ChromaDB"
	@echo "  make pipeline     - Executa o pipeline de dados completo (Bronze -> Silver -> Gold)"
	@echo "  make train        - Treina/especializa o modelo no Ollama com aceleracao GPU RTX"
	@echo "  make evolution    - Executa o benchmark A/B e gera relatorio de evolucao de inteligencia"
	@echo "  make test         - Executa a suite de testes unitarios e de integracao"
	@echo "  make benchmark    - Executa o benchmark comparativo Naive RAG vs Self-RAG"
	@echo "  make run          - Inicia a interface CLI interativa"
	@echo "  make clean        - Remove caches e temporarios de compilacao"

install:
	pip install -r requirements-dev.txt

bronze:
	python src/pipeline/downloader.py

silver:
	python src/pipeline/parser.py

gold:
	python src/pipeline/indexer.py

pipeline: bronze silver gold
	@echo "[OK] Pipeline de dados executado com sucesso!"

train:
	python src/training/dataset_generator.py
	python src/training/train.py

evolution:
	python src/evaluation/eval_evolution.py

test:
	python tests/test_pipeline.py
	python tests/test_agent.py

benchmark:
	python src/evaluation/benchmark.py

run:
	python src/cli.py

clean:
	rm -rf __pycache__ src/**/__pycache__ tests/__pycache__ .pytest_cache

