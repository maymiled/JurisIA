#!/bin/bash
set -e

# Télécharge les embeddings depuis HuggingFace Hub si absents
if [ ! -f "data/embeddings/chroma/chroma.sqlite3" ]; then
  echo "Téléchargement des embeddings depuis HuggingFace Hub..."
  python -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='mayoutathecat/jurisia-embeddings',
    repo_type='dataset',
    local_dir='data/embeddings',
    token='${HF_TOKEN}'
)
print('Embeddings prêts.')
"
fi

exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000
