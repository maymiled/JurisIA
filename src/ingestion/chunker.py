"""
JurisIA — Chunking Pipeline (Giuliano Darwish)

Lit les articles bruts produits par scraper.py (data/raw/code_travail_raw.json)
et les découpe en chunks structurés avec métadonnées, prêts pour l'embedding.

Stratégie de chunking :
  1. Si l'article tient dans max_tokens → 1 chunk = 1 article (préférable pour la citation exacte)
  2. Si l'article est trop long → découpe par paragraphes avec overlap pour éviter les coupures sémantiques
  3. Chaque chunk conserve ses métadonnées (numéro, titre, thème, url, source)

Output : data/processed/code_travail_chunks.json
"""

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from tqdm import tqdm

RAW_DIR = Path(__file__).parents[2] / "data" / "raw"
PROCESSED_DIR = Path(__file__).parents[2] / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ArticleChunk:
    """Chunk d'article juridique avec métadonnées complètes."""
    chunk_id: str           # ex: "L1221-1" ou "L1221-1_p2" si article découpé
    article_id: str         # id Légifrance brut
    article_number: str     # numéro/slug lisible (ex: "L1221-1")
    title: str
    text: str               # contenu du chunk
    theme: Optional[str]
    url: Optional[str]
    source: str
    part_index: int         # 0 si article entier, sinon index du sous-chunk
    total_parts: int        # 1 si article entier
    char_count: int = field(init=False)
    token_estimate: int = field(init=False)

    def __post_init__(self):
        self.char_count = len(self.text)
        # Approximation : 1 token ≈ 4 caractères pour le français
        self.token_estimate = self.char_count // 4


class LegalChunker:
    """
    Chunker intelligent pour le Code du travail français.

    Args:
        max_tokens: Taille maximale d'un chunk (en tokens estimés).
                    512 = bon compromis pour les modèles d'embedding (camembert, e5).
        overlap_sentences: Nombre de phrases à répéter entre deux chunks consécutifs
                           d'un même article, pour préserver le contexte.
    """

    def __init__(self, max_tokens: int = 512, overlap_sentences: int = 2):
        self.max_tokens = max_tokens
        self.overlap_sentences = overlap_sentences
        # Approximation chars → tokens pour le français
        self._max_chars = max_tokens * 4

    # ── API publique ─────────────────────────────────────────────────────────

    def chunk_file(
        self,
        input_path: Path = RAW_DIR / "code_travail_raw.json",
        output_path: Path = PROCESSED_DIR / "code_travail_chunks.json",
    ) -> Path:
        """
        Pipeline complet : lit le JSON brut de May → chunk → sauvegarde.
        Retourne le chemin du fichier produit.
        """
        print(f"Lecture des articles bruts : {input_path}")
        with open(input_path, encoding="utf-8") as f:
            articles = json.load(f)

        print(f"{len(articles)} articles à chunker...")
        chunks = self.chunk_articles(articles)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in chunks], f, ensure_ascii=False, indent=2)

        print(f"{len(chunks)} chunks sauvegardés → {output_path}")
        return output_path

    def chunk_articles(self, articles: list[dict]) -> list[ArticleChunk]:
        """Transforme une liste d'articles bruts en chunks structurés."""
        all_chunks = []
        for article in tqdm(articles, desc="Chunking"):
            chunks = self._process_article(article)
            all_chunks.extend(chunks)
        return all_chunks

    # ── Logique interne ──────────────────────────────────────────────────────

    def _process_article(self, article: dict) -> list[ArticleChunk]:
        """Découpe un article brut en 1 ou plusieurs chunks."""
        text = (article.get("content") or article.get("text") or "").strip()
        if not text:
            return []

        article_id = article.get("id", "")
        number = article.get("number") or article_id
        title = article.get("title", "")
        theme = article.get("theme")
        url = article.get("url")
        source = article.get("source", "code_du_travail")

        # Cas 1 : article court → chunk unique
        if len(text) <= self._max_chars:
            return [ArticleChunk(
                chunk_id=number,
                article_id=article_id,
                article_number=number,
                title=title,
                text=text,
                theme=theme,
                url=url,
                source=source,
                part_index=0,
                total_parts=1,
            )]

        # Cas 2 : article long → découpe par paragraphes avec overlap
        sub_texts = self._split_with_overlap(text)
        total = len(sub_texts)
        return [
            ArticleChunk(
                chunk_id=f"{number}_p{i + 1}",
                article_id=article_id,
                article_number=number,
                title=title,
                text=sub,
                theme=theme,
                url=url,
                source=source,
                part_index=i,
                total_parts=total,
            )
            for i, sub in enumerate(sub_texts)
        ]

    def _split_with_overlap(self, text: str) -> list[str]:
        """
        Découpe un texte long en chunks de max_chars caractères,
        avec overlap de quelques phrases pour préserver la cohérence sémantique.
        """
        # Découpe en phrases (point/point-virgule/retour à la ligne)
        sentences = re.split(r"(?<=[.;])\s+|\n+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        current: list[str] = []
        current_len = 0

        for sent in sentences:
            sent_len = len(sent)

            if current_len + sent_len + 1 > self._max_chars and current:
                chunks.append(" ".join(current))
                # Overlap : on reprend les dernières phrases
                current = current[-self.overlap_sentences:]
                current_len = sum(len(s) for s in current)

            current.append(sent)
            current_len += sent_len + 1  # +1 pour l'espace

        if current:
            chunks.append(" ".join(current))

        return chunks


# ── Point d'entrée ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    chunker = LegalChunker(max_tokens=512, overlap_sentences=2)
    output = chunker.chunk_file()
    print(f"\nTerminé. Fichier prêt pour l'embedding : {output}")
