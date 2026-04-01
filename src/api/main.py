"""
JurisIA — API FastAPI

Endpoints :
    POST /ask     → question juridique → réponse RAG + sources
    GET  /health  → vérification que l'API tourne
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path

# Permet d'importer src/retrieval/rag_pipeline depuis n'importe où
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.retrieval.rag_pipeline import ask, retrieve

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="JurisIA",
    description="Assistant juridique IA spécialisé en droit du travail français",
    version="0.1.0",
)

# ── Schémas ───────────────────────────────────────────────────────────────────

class QuestionRequest(BaseModel):
    question: str

class SourceItem(BaseModel):
    article_number: str
    title: str
    url: str

class AnswerResponse(BaseModel):
    answer: str
    sources: list[SourceItem]

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AnswerResponse)
def ask_question(body: QuestionRequest):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="La question ne peut pas être vide.")

    chunks = retrieve(body.question)
    answer = ask(body.question, chunks=chunks)

    sources = [
        SourceItem(
            article_number=c["article_number"],
            title=c["title"],
            url=c["url"],
        )
        for c in chunks
    ]

    return AnswerResponse(answer=answer, sources=sources)
