# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projet

JurisIA — assistant juridique IA spécialisé en droit du travail français.
Pipeline complet : scraping Légifrance → RAG → fine-tuning (LoRA/QLoRA) → DPO → déploiement FastAPI.

## Commandes utiles

```bash
# Environnement
source .venv/bin/activate

# Scraping (Jour 1) — nécessite PISTE_CLIENT_ID et PISTE_CLIENT_SECRET dans .env
python src/ingestion/scraper.py
# → data/raw/code_travail_raw.json

# Chunking (Jour 1) — à faire après le scraping
python src/ingestion/chunker.py
# → data/processed/chunks.json
```

## Architecture

Le pipeline se lit de gauche à droite :

```
Légifrance (PISTE API)
  → src/ingestion/scraper.py      # Récupère les articles bruts → data/raw/
  → src/ingestion/chunker.py      # Découpe + métadonnées → data/processed/
  → src/embeddings/indexer.py     # Génère embeddings + indexe dans ChromaDB → data/embeddings/
  → src/retrieval/rag_pipeline.py # query → top-k articles → prompt augmenté → LLM
  → src/finetuning/sft_trainer.py # Fine-tuning Mistral-7B avec QLoRA/PEFT
  → src/finetuning/dpo_trainer.py # Alignment avec DPO via TRL
  → src/api/main.py               # FastAPI endpoint /ask
  → app/demo.py                   # Interface Streamlit
```

## Format des données

**Articles bruts** (`data/raw/code_travail_raw.json`) — liste de dicts :
```json
{ "id": "LEGIARTI...", "number": "L1221-1", "title": "...", "content": "...", "source": "piste_api", "url": "..." }
```

**Chunks** (`data/processed/chunks.json`) — même structure + métadonnées hiérarchiques :
```json
{ "chunk_id": "...", "article_number": "L1221-1", "partie": "Première partie...", "livre": "...", "section": "...", "char_count": 420 }
```

## Branches git

- `main` — structure de base stable
- `feature/scraping` — scraper PISTE API (cette branche)
- `feature/chunking` — chunking (Giuliano)

PRs à merger dans `main` à la fin de chaque phase.

## Credentials

Configurés dans `.env` (jamais commité) :
- `PISTE_CLIENT_ID` / `PISTE_CLIENT_SECRET` — API Légifrance officielle
- `ANTHROPIC_API_KEY` — LLM baseline pour le RAG (Jour 3-4)

## Stack par phase

| Phase | Librairies clés |
|-------|----------------|
| Ingestion | `requests`, `beautifulsoup4` |
| Embeddings | `sentence-transformers` (`intfloat/multilingual-e5-base`) |
| Vector DB | `chromadb` (local, persisté dans `data/embeddings/chroma/`) |
| RAG | `langchain`, `langchain-anthropic` |
| Fine-tuning | `transformers`, `peft`, `trl`, `bitsandbytes` (QLoRA 4-bit) |
| API | `fastapi`, `uvicorn` |
| Interface | `streamlit` |
