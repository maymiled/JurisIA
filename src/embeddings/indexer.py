"""
JurisIA — Embedding & Indexation (Jour 2)

Lit les chunks produits par chunker.py et :
1. Génère les embeddings avec intfloat/multilingual-e5-base
2. Indexe dans ChromaDB (local, persisté sur disque)

Usage :
    python src/embeddings/indexer.py
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

PROCESSED_DIR = Path(__file__).parents[2] / "data" / "processed"
CHROMA_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", "data/embeddings/chroma"))
# MiniLM multilingual : 4x plus rapide que e5-base sur CPU, qualité très proche
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
COLLECTION_NAME = "code_travail"
BATCH_SIZE = 64


def load_chunks(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_index(chunks_path: Path = PROCESSED_DIR / "code_travail_chunks.json") -> None:
    """Génère les embeddings et indexe tous les chunks dans ChromaDB."""
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    chunks = load_chunks(chunks_path)
    print(f"{len(chunks)} chunks chargés depuis {chunks_path}")

    # Embedding function — multilingual-e5-base est optimisé pour le français
    print(f"Chargement du modèle d'embedding : {EMBEDDING_MODEL}")
    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL,
        device="cpu",
    )

    # ChromaDB client persisté sur disque
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Supprimer la collection si elle existe déjà (re-indexation propre)
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Collection '{COLLECTION_NAME}' existante supprimée.")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )

    # Indexation par batch
    total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in tqdm(range(0, len(chunks), BATCH_SIZE), total=total_batches, desc="Indexation"):
        batch = chunks[i : i + BATCH_SIZE]

        # IDs uniques : on ajoute l'index global pour éviter les doublons
        ids = [f"{c['chunk_id']}_{i + j}" for j, c in enumerate(batch)]
        documents = [c["text"] for c in batch]
        metadatas = [
            {
                "article_number": c.get("article_number", ""),
                "title": c.get("title", ""),
                "url": c.get("url", ""),
                "theme": c.get("theme") or "",
                "source": c.get("source", ""),
                "part_index": c.get("part_index", 0),
                "total_parts": c.get("total_parts", 1),
                "token_estimate": c.get("token_estimate", 0),
            }
            for c in batch
        ]

        collection.add(ids=ids, documents=documents, metadatas=metadatas)

    print(f"\nIndexation terminée : {collection.count()} chunks dans ChromaDB")
    print(f"Base vectorielle persistée → {CHROMA_DIR}")


def test_query(query: str = "licenciement sans cause réelle et sérieuse", top_k: int = 3) -> None:
    """Test rapide : cherche les articles les plus pertinents pour une question."""
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL, device="cpu"
    )
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(COLLECTION_NAME, embedding_function=embedding_fn)

    results = collection.query(query_texts=[query], n_results=top_k)

    print(f"\nQuery : « {query} »\n")
    for i, (doc, meta) in enumerate(
        zip(results["documents"][0], results["metadatas"][0])
    ):
        print(f"── Résultat {i+1} : Article {meta['article_number']}")
        print(f"   {doc[:200]}...")
        print()


if __name__ == "__main__":
    build_index()
    test_query()
