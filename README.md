# JurisIA

Assistant juridique IA spécialisé en droit du travail français.

**Stack** : RAG + Fine-tuning (LoRA/QLoRA) + DPO + FastAPI + Streamlit

## Architecture

```
JurisIA/
├── data/
│   ├── raw/          # Articles bruts scrapés depuis Légifrance
│   ├── processed/    # Chunks avec métadonnées
│   ├── embeddings/   # Base vectorielle (ChromaDB)
│   └── eval/         # Jeu de données d'évaluation
├── src/
│   ├── ingestion/    # Scraping + chunking (Jour 1-2)
│   ├── embeddings/   # Génération embeddings + indexation (Jour 1-2)
│   ├── retrieval/    # Pipeline RAG (Jour 3-4)
│   ├── finetuning/   # SFT + DPO (Jour 5-8)
│   ├── evaluation/   # Métriques (Jour 7-8)
│   └── api/          # FastAPI (Jour 9-10)
├── app/              # Interface Streamlit/Gradio (Jour 9-10)
├── notebooks/        # Exploration & expérimentations
├── models/           # Adaptateurs LoRA sauvegardés
└── docker/           # Dockerfile + docker-compose
```

## Roadmap (10 jours)

| Jours | Phase | Livrable |
|-------|-------|----------|
| 1-2 | RAG Ingestion | Base vectorielle ~3000 articles Code du travail |
| 3-4 | RAG Retrieval | Pipeline RAG fonctionnel avec citations |
| 5-6 | Fine-tuning SFT | Modèle Mistral-7B fine-tuné avec LoRA |
| 7-8 | DPO + Éval | Comparatif RAG vs SFT vs DPO |
| 9-10 | Déploiement | API + Interface + Docker |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Remplir les clés API dans .env
```

## Lancer le scraper (Jour 1)

```bash
python src/ingestion/scraper.py
```
