"""
Scraper du Code du travail depuis Légifrance.

Deux stratégies disponibles :
1. API PISTE (officielle DILA) — nécessite des credentials OAuth2
2. data.gouv.fr — dump XML open data, aucune auth requise (recommandé pour démarrer)
"""

import json
import os
import time
import zipfile
from pathlib import Path
from typing import Generator

import requests
from tqdm import tqdm

RAW_DIR = Path(__file__).parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# URL du dump XML du Code du travail sur data.gouv.fr (Légifrance open data)
LEGI_DUMP_URL = (
    "https://echanges.dila.gouv.fr/OPENDATA/LEGI/Freemium_legi_global_20171201-162124.tar.gz"
)

# API PISTE — base URL
PISTE_TOKEN_URL = "https://oauth.piste.gouv.fr/api/oauth/token"
PISTE_API_BASE = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app"

CODE_TRAVAIL_ID = "LEGITEXT000006072050"


# ── Stratégie 1 : API PISTE ──────────────────────────────────────────────────

class PISTEScraper:
    """Scraper via l'API officielle PISTE de la DILA."""

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

    def _get(self, endpoint: str, payload: dict) -> dict:
        resp = self.session.post(f"{PISTE_API_BASE}/{endpoint}", json=payload)
        resp.raise_for_status()
        return resp.json()

    def fetch_table_of_contents(self) -> dict:
        """Récupère la table des matières du Code du travail."""
        return self._get(
            "consult/code/tableMatieres",
            {"textId": CODE_TRAVAIL_ID, "date": "2024-01-01"},
        )

    def fetch_article(self, article_id: str) -> dict:
        """Récupère le contenu d'un article par son ID Légifrance."""
        return self._get("consult/getArticle", {"id": article_id})

    def fetch_section_articles(self, section_id: str) -> list[dict]:
        """Récupère tous les articles d'une section."""
        data = self._get(
            "consult/code/section/id",
            {"sectionId": section_id, "textId": CODE_TRAVAIL_ID, "date": "2024-01-01"},
        )
        return data.get("articles", [])

    def scrape_all_articles(self, output_file: str = "code_travail_articles.json") -> Path:
        """
        Parcourt tout le Code du travail et sauvegarde les articles en JSON.
        Retourne le chemin du fichier créé.
        """
        if not self.token:
            self.authenticate()

        toc = self.fetch_table_of_contents()
        articles = []

        def traverse_sections(sections: list) -> None:
            for section in sections:
                # Articles directs dans la section
                for article in section.get("articles", []):
                    try:
                        full = self.fetch_article(article["id"])
                        articles.append(full)
                        time.sleep(0.1)  # rate limiting
                    except Exception as e:
                        print(f"Erreur article {article.get('id')}: {e}")
                # Sous-sections récursives
                traverse_sections(section.get("sections", []))

        traverse_sections(toc.get("sections", []))

        out = RAW_DIR / output_file
        with open(out, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)

        print(f"{len(articles)} articles sauvegardés → {out}")
        return out


# ── Stratégie 2 : Scraping direct HTML Légifrance ────────────────────────────

class LegifranceScraper:
    """
    Scraper HTML de legifrance.gouv.fr.
    Fallback quand on n'a pas de credentials PISTE.
    """

    BASE_URL = "https://www.legifrance.gouv.fr"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; JurisIA-research-bot/1.0; "
            "+https://github.com/yourname/jurisia)"
        )
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def fetch_article_by_number(self, article_num: str) -> dict | None:
        """
        Récupère un article via l'URL de recherche Légifrance.
        Ex: article_num = "L1221-1"
        """
        url = f"{self.BASE_URL}/codes/article_lc/{article_num}"
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            return self._parse_article_html(resp.text, article_num)
        except requests.RequestException as e:
            print(f"Erreur HTTP pour {article_num}: {e}")
            return None

    def _parse_article_html(self, html: str, article_num: str) -> dict:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")

        # Contenu principal de l'article
        content_div = soup.find("div", class_="content-article")
        content = content_div.get_text(separator="\n", strip=True) if content_div else ""

        # Titre / numéro
        title_el = soup.find("h1", class_="title-article")
        title = title_el.get_text(strip=True) if title_el else article_num

        return {
            "id": article_num,
            "number": article_num,
            "title": title,
            "content": content,
            "source": "legifrance_html",
        }


# ── Stratégie 3 : Open Data LEGI (recommandée Day 1) ────────────────────────

def iter_articles_from_json_dump(dump_path: Path) -> Generator[dict, None, None]:
    """
    Itère sur les articles depuis un dump JSON pré-traité.
    Format attendu : liste d'objets avec au moins 'number', 'content', 'title'.
    """
    with open(dump_path, encoding="utf-8") as f:
        articles = json.load(f)
    for article in articles:
        yield article


def fetch_code_travail_opendata() -> Path:
    """
    Télécharge les articles du Code du travail depuis l'API ouverte
    de beta.gouv / data.economie.gouv ou équivalent.

    Alternative simple : utilise l'API non-officielle du Code du travail
    (https://github.com/SocialGouv/code-du-travail-numerique).
    """
    # API du Code du travail numérique (Ministère du Travail)
    # Endpoint public, pas d'auth requise
    API_URL = "https://api.code-du-travail.gouv.fr/api/v1/search"

    articles = []
    page = 0
    page_size = 100

    print("Téléchargement des articles via l'API Code du travail numérique...")

    with tqdm(desc="Articles") as pbar:
        while True:
            try:
                resp = requests.get(
                    API_URL,
                    params={
                        "q": "",
                        "sources": "code_du_travail",
                        "page": page,
                        "pageSize": page_size,
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()

                results = data.get("results", [])
                if not results:
                    break

                for item in results:
                    articles.append({
                        "id": item.get("id", ""),
                        "number": item.get("slug", ""),
                        "title": item.get("title", ""),
                        "content": item.get("text", ""),
                        "source": "code_du_travail_numerique",
                        "url": item.get("url", ""),
                        "theme": item.get("theme", ""),
                    })

                pbar.update(len(results))
                page += 1
                time.sleep(0.2)

                if len(results) < page_size:
                    break

            except Exception as e:
                print(f"\nErreur page {page}: {e}")
                break

    out = RAW_DIR / "code_travail_raw.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"\n{len(articles)} articles sauvegardés → {out}")
    return out


if __name__ == "__main__":
    # Lancement rapide : open data sans credentials
    out_path = fetch_code_travail_opendata()
    print(f"Fichier créé : {out_path}")
