FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias do sistema necessarias para C-extensions e compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV OLLAMA_BASE_URL=http://host.docker.internal:11434

CMD ["python", "src/cli.py"]

