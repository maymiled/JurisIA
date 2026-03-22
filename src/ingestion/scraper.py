"""
Scraper du Code du travail depuis Légifrance.

Stratégies disponibles (par ordre de simplicité) :
1. HuggingFace dataset (manu/dila_legifrance) — aucune auth, recommandé pour démarrer
2. API PISTE officielle DILA — nécessite des credentials OAuth2
3. Scraping HTML legifrance.gouv.fr — fallback
"""

import json
import time
from pathlib import Path

import requests
from tqdm import tqdm

RAW_DIR = Path(__file__).parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# API PISTE — base URL
PISTE_TOKEN_URL = "https://oauth.piste.gouv.fr/api/oauth/token"
PISTE_API_BASE = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app"
CODE_TRAVAIL_ID = "LEGITEXT000006072050"

HF_DATASET_ID = "manu/dila_legifrance"


# ── Stratégie 1 : HuggingFace dataset (recommandée) ─────────────────────────

def fetch_code_travail_huggingface(output_file: str = "code_travail_raw.json") -> Path:
    """
    Télécharge les articles du Code du travail depuis le dataset HuggingFace
    manu/dila_legifrance — aucune auth requise.

    Nécessite : pip install datasets
    """
    try:
        from datasets import load_dataset
    except ImportError:
        raise ImportError("Lance : pip install datasets")

    print(f"Chargement du dataset HuggingFace {HF_DATASET_ID}...")
    ds = load_dataset(HF_DATASET_ID, split="train", trust_remote_code=True)

    articles = []
    for item in tqdm(ds, desc="Filtrage Code du travail"):
        # Garder uniquement les articles du Code du travail
        nature = item.get("nature", "")
        titre = item.get("titre", item.get("title", ""))
        if "TRAVAIL" not in str(titre).upper() and "travail" not in str(nature).lower():
            # Filtrer par identifiant légifrance si disponible
            cid = item.get("cid", item.get("textId", ""))
            if CODE_TRAVAIL_ID not in str(cid):
                continue

        articles.append({
            "id": item.get("id", item.get("cid", "")),
            "number": item.get("num", item.get("numero", "")),
            "title": titre,
            "content": item.get("texte", item.get("text", item.get("content", ""))),
            "source": "huggingface_dila",
            "url": f"https://www.legifrance.gouv.fr/codes/article_lc/{item.get('num', '')}",
            "theme": item.get("section", ""),
        })

    out = RAW_DIR / output_file
    with open(out, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"\n{len(articles)} articles sauvegardés → {out}")
    return out


# ── Stratégie 2 : API PISTE officielle ──────────────────────────────────────

class PISTEScraper:
    """Scraper via l'API officielle PISTE de la DILA (nécessite credentials)."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token: str | None = None
        self.session = requests.Session()

    def authenticate(self) -> None:
        resp = self.session.post(
            PISTE_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "openid",
            },
        )
        resp.raise_for_status()
        self.token = resp.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        print("Authentification PISTE OK")

    def _post(self, endpoint: str, payload: dict) -> dict:
        resp = self.session.post(f"{PISTE_API_BASE}/{endpoint}", json=payload)
        resp.raise_for_status()
        return resp.json()

    def fetch_table_of_contents(self) -> dict:
        return self._post(
            "consult/code/tableMatieres",
            {"textId": CODE_TRAVAIL_ID, "date": "2024-01-01"},
        )

    def fetch_article(self, article_id: str) -> dict:
        return self._post("consult/getArticle", {"id": article_id})

    def scrape_all(self, output_file: str = "code_travail_raw.json") -> Path:
        """Parcourt tout le Code du travail et sauvegarde les articles."""
        if not self.token:
            self.authenticate()

        toc = self.fetch_table_of_contents()
        articles = []

        def traverse(sections: list) -> None:
            for section in sections:
                for article in section.get("articles", []):
                    try:
                        full = self.fetch_article(article["id"])
                        articles.append({
                            "id": full.get("id", ""),
                            "number": full.get("num", ""),
                            "title": full.get("titre", ""),
                            "content": full.get("texte", ""),
                            "source": "piste_api",
                            "url": f"https://www.legifrance.gouv.fr/codes/article_lc/{full.get('num', '')}",
                        })
                        time.sleep(0.1)
                    except Exception as e:
                        print(f"Erreur article {article.get('id')}: {e}")
                traverse(section.get("sections", []))

        traverse(toc.get("sections", []))

        out = RAW_DIR / output_file
        with open(out, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)

        print(f"{len(articles)} articles sauvegardés → {out}")
        return out


# ── Stratégie 3 : HuggingFace sans filtre (plus simple) ──────────────────────

def fetch_all_articles_hf_simple(output_file: str = "code_travail_raw.json") -> Path:
    """
    Charge les articles du Code du travail via la lib `datasets` HuggingFace
    en mode streaming — pas de credentials requis, gère la pagination automatiquement.

    Nécessite : pip install datasets
    Le dataset contient 2.3M entrées (tout DILA) — on filtre sur les IDs Code du travail.
    IDs du Code du travail : commencent par LEGIARTI et appartiennent au code LEGITEXT000006072050.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        raise ImportError("Lance d'abord : pip install datasets")

    import re

    # Pattern des articles du Code du travail dans le texte
    # Le texte contient généralement "Article L/R/D XXXX-X" ou l'ID LEGIARTI
    CODE_TRAVAIL_PATTERN = re.compile(
        r"Article\s+[LRD]\d{3,4}[- ]\d+|"
        r"Code du travail|"
        r"L\.\s*\d{4}[- ]\d+",
        re.IGNORECASE
    )

    articles = []
    print(f"Streaming du dataset {HF_DATASET_ID} (filtrage Code du travail)...")
    print("Note : dataset volumineux, filtrage en cours — peut prendre quelques minutes.")

    ds = load_dataset(HF_DATASET_ID, split="train", streaming=True, trust_remote_code=True)

    with tqdm(desc="Articles trouvés") as pbar:
        for item in ds:
            item_id = item.get("id", "")
            text = item.get("text", "")

            if not text:
                continue

            # Filtrer : garde uniquement les articles du Code du travail
            if not CODE_TRAVAIL_PATTERN.search(text[:500]):
                continue

            # Extraire le numéro d'article depuis le texte
            num_match = re.search(r'Article\s+([LRD]\d{3,4}[-]\d+(?:[-]\d+)?)', text)
            article_num = num_match.group(1) if num_match else item_id

            articles.append({
                "id": item_id,
                "number": article_num,
                "title": f"Article {article_num}",
                "content": text,
                "source": "huggingface_dila",
                "url": f"https://www.legifrance.gouv.fr/codes/article_lc/{article_num}",
            })
            pbar.update(1)

            # Objectif : ~3000 articles pour le livrable Jour 1-2
            if len(articles) >= 3500:
                break

    out = RAW_DIR / output_file
    with open(out, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"\n{len(articles)} articles sauvegardés → {out}")
    return out


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    client_id = os.getenv("PISTE_CLIENT_ID")
    client_secret = os.getenv("PISTE_CLIENT_SECRET")

    if client_id and client_secret:
        # Option 1 : API officielle PISTE
        print("Utilisation de l'API PISTE (credentials trouvés)...")
        scraper = PISTEScraper(client_id, client_secret)
        out_path = scraper.scrape_all()
    else:
        # Option 2 : HuggingFace sans credentials
        print("Pas de credentials PISTE — utilisation de HuggingFace...")
        out_path = fetch_all_articles_hf_simple()

    print(f"\nFichier créé : {out_path}")
