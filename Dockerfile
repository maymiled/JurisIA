FROM python:3.11-slim

WORKDIR /app

# Dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Code source
COPY src/ src/

# Base vectorielle ChromaDB (embeddings pré-calculés)
COPY data/embeddings/ data/embeddings/

ENV CHROMA_PERSIST_DIR=data/embeddings/chroma
ENV EMBEDDING_MODEL=intfloat/multilingual-e5-base

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
