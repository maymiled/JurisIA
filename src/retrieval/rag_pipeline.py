"""
JurisIA — Pipeline RAG (Jour 3)

Chaîne complète : question → retrieval → prompt augmenté → réponse LLM

Flux :
    question utilisateur
        → embedding de la question
        → top-k chunks les plus proches dans ChromaDB
        → prompt système juridique + chunks + question
        → LLM (Claude) génère une réponse en citant les articles
"""

import os
from pathlib import Path

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", "data/embeddings/chroma"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
LLM_MODEL = "llama-3.3-70b-versatile"
COLLECTION_NAME = "code_travail"
TOP_K = 5  # Nombre d'articles récupérés par requête

SYSTEM_PROMPT = """Tu es JurisIA, un assistant juridique spécialisé en droit du travail français.

Règles absolues :
- Tu réponds UNIQUEMENT en te basant sur les articles du Code du travail fournis dans le contexte.
- Tu cites systématiquement les articles entre crochets : [Article L1234-1].
- Si les articles fournis ne permettent pas de répondre, tu le dis explicitement.
- Tu ne donnes jamais de conseil juridique personnalisé — tu informes sur le droit.
- Tes réponses sont claires, structurées et accessibles à un non-juriste.
"""


def get_collection():
    """Charge la collection ChromaDB avec le modèle d'embedding."""
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    ef = SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL, device="cpu"
    )
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION_NAME, embedding_function=ef)


def retrieve(question: str, top_k: int = TOP_K) -> list[dict]:
    """
    Retrouve les chunks les plus pertinents pour une question.
    Retourne une liste de dicts avec 'text', 'article_number', 'url'.
    """
    collection = get_collection()
    results = collection.query(query_texts=[question], n_results=top_k)

    chunks = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append({
            "text": doc,
            "article_number": meta.get("article_number", ""),
            "title": meta.get("title", ""),
            "url": meta.get("url", ""),
        })
    return chunks


def build_prompt(question: str, chunks: list[dict]) -> str:
    """Construit le prompt augmenté avec les articles récupérés."""
    context = ""
    for i, chunk in enumerate(chunks, 1):
        num = chunk["article_number"]
        context += f"[Article {num}]\n{chunk['text']}\n\n"

    return f"""Voici les articles du Code du travail pertinents pour répondre à la question :

{context}
---
Question : {question}

Réponds en citant les articles entre crochets [Article XXX]."""


def ask(question: str, stream: bool = False) -> str:
    """
    Pipeline RAG complet : question → articles → réponse LLM.

    Args:
        question: La question juridique de l'utilisateur
        stream: Si True, affiche la réponse en streaming dans le terminal

    Returns:
        La réponse complète sous forme de string
    """
    # 1. Retrieval
    chunks = retrieve(question)

    if not chunks:
        return "Aucun article pertinent trouvé dans le Code du travail."

    # 2. Prompt augmenté
    user_prompt = build_prompt(question, chunks)

    # 3. Génération LLM (Groq)
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    if stream:
        print("\nJurisIA : ", end="", flush=True)
        response_text = ""
        stream_response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
        )
        for chunk in stream_response:
            text = chunk.choices[0].delta.content or ""
            print(text, end="", flush=True)
            response_text += text
        print("\n")
        return response_text
    else:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content


def show_sources(chunks: list[dict]) -> None:
    """Affiche les sources utilisées pour une réponse."""
    print("\n── Sources ──────────────────────────────")
    for chunk in chunks:
        print(f"  Article {chunk['article_number']} — {chunk['url']}")


if __name__ == "__main__":
    questions = [
        "Quelles sont les conditions d'un licenciement pour motif personnel ?",
        "Combien de temps dure le préavis en cas de licenciement ?",
        "Quels sont les droits d'un salarié en cas de harcèlement moral ?",
    ]

    for question in questions:
        print(f"\n{'='*60}")
        print(f"Question : {question}")
        print("="*60)

        chunks = retrieve(question)
        answer = ask(question, stream=True)
        show_sources(chunks)
