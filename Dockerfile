FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY src/ src/
COPY start.sh .
# cache-bust: fa8d822
RUN chmod +x start.sh

RUN mkdir -p data/embeddings

ENV CHROMA_PERSIST_DIR=data/embeddings/chroma
ENV EMBEDDING_MODEL=intfloat/multilingual-e5-base

EXPOSE 8000

CMD ["./start.sh"]
