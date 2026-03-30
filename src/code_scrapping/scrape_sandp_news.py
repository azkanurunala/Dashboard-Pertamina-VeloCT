import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from helpers.scraping_utils import normalize_to_iso_date


# Constants

SP_AUTH_URL      = "https://api.ci.spglobal.com/auth/api"
SP_SEARCH_URL    = "https://api.ci.spglobal.com/news-insights/v1/search/story"
SP_CONTENT_URL   = "https://api.ci.spglobal.com/news-insights/v1/content/{article_id}"

DEFAULT_PAGESIZE = 1000
REQUEST_TIMEOUT  = 30
SEARCH_TIMEOUT   = 60


# Authentication

def _login(username: str | None = None, password: str | None = None) -> str | None:
    """
    Authenticate with the S&P API using provided or environment credentials and return a Bearer token, or None on failure.
    """
    username = username or os.getenv("S&P_USERNAME")
    password = password or os.getenv("S&P_PASSWORD")

    if not username or not password:
        print("[Auth] Error: S&P_USERNAME or S&P_PASSWORD not found in environment.")
        return None

    print(f"[Auth] Logging in as '{username}'...")

    try:
        response = requests.post(
            SP_AUTH_URL,
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        token = response.json().get("access_token")

        if token:
            print("[Auth] Login successful — access token obtained.")
            return token

        print(f"[Auth] Login failed: access_token not in response: {response.json()}")
        return None

    except requests.RequestException as exc:
        print(f"[Auth] Request error: {exc}")
        if hasattr(exc, "response") and exc.response is not None:
            print(f"[Auth] Response {exc.response.status_code}: {exc.response.text}")
        return None


# HTML → Plain Text

def _html_to_text(html_content: str) -> str:
    """
    Convert HTML content to clean plain text by removing script/style tags and normalizing whitespace.
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    return " ".join(soup.get_text(separator=" ", strip=True).split())


# Article Content Fetching

def _fetch_article_content(access_token: str, article_id: str) -> str:
    """
    Fetch S&P article content using an access token and convert HTML body to clean plain text.
    """
    url = SP_CONTENT_URL.format(article_id=article_id)
    try:
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":  "application/json",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        body_html = (
            data.get("envelope", {})
                .get("content", {})
                .get("body", "")
        )
        return _html_to_text(body_html)

    except requests.RequestException as exc:
        print(f"[Content] Failed to fetch article {article_id}: {exc}")
        return ""


# News Search

def _search_news(
    access_token: str,
    query: str,
    start_date: str | None = None,
    end_date: str | None = None,
    pagesize: int = DEFAULT_PAGESIZE,
) -> list[dict]:
    """
    Search S&P Global news with optional date filtering and return articles enriched with full content.
    """
    params: dict = {"q": query, "pagesize": pagesize}

    if start_date and end_date:
        params["filter"] = f'updatedDate >= "{start_date}" AND updatedDate < "{end_date}"'

    print(f"\n[Search] Query   : '{query}'")
    if "filter" in params:
        print(f"[Search] Filter  : {params['filter']}")

    try:
        response = requests.get(
            SP_SEARCH_URL,
            params=params,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":  "application/json",
            },
            timeout=SEARCH_TIMEOUT,
        )
        print(f"[Search] Status  : {response.status_code}")
        response.raise_for_status()
        data = response.json()

    except requests.RequestException as exc:
        print(f"[Search] Request error: {exc}")
        if hasattr(exc, "response") and exc.response is not None:
            print(f"[Search] Response: {exc.response.text}")
        return []

    results  = data.get("results", [])
    metadata = data.get("metadata", {})
    print(f"[Search] Found {metadata.get('count', len(results))} article(s).")

    articles: list[dict] = []
    for i, item in enumerate(results, start=1):
        article_id   = item.get("id",          "")
        headline     = item.get("headline",     "")
        updated_date = item.get("updatedDate",  "")
        document_url = item.get("documentUrl",  "")

        # Normalise date — handles ISO 8601 timestamps from the API
        iso_date = normalize_to_iso_date(updated_date.split("T")[0]) if updated_date else ""

        print(f"  [{i}/{len(results)}] {headline[:50]}...")
        content = _fetch_article_content(access_token, article_id)

        articles.append({
            "title":   headline,
            "date":    iso_date,
            "url":     document_url,
            "content": content,
        })

    return articles


# Orchestration

def scrape_spglobal(
    keyword: str = "SAF",
    tanggal: str | None = None,
) -> list[dict]:
    """
    Authenticate with S&P Global and fetch news articles by keyword with optional single-day date filtering.
    """
    access_token = _login()
    if not access_token:
        print("[Scrape] Login failed — aborting.")
        return []

    start_date: str | None = None
    end_date:   str | None = None

    if tanggal is not None:
        iso_date = normalize_to_iso_date(str(tanggal))
        if not iso_date:
            print(f"[Scrape] Warning: could not normalise tanggal='{tanggal}' — ignoring date filter.")
        else:
            date_obj   = datetime.strptime(iso_date, "%Y-%m-%d")
            start_date = f"{iso_date} 00:00:00"
            end_date   = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")

    articles = _search_news(access_token, keyword, start_date, end_date)

    if not articles:
        print("[Scrape] No articles found.")
    else:
        print(f"\n[Scrape] {len(articles)} article(s) retrieved.")

    return articles


# Public Entry Point

def main_spglobal(
    keyword: str = "SAF",
    tanggal: str | None = None,
) -> pd.DataFrame | None:
    """
    Run the S&P Global scraping workflow for a keyword and optional date, returning a structured DataFrame or None if no results are found.
    """
    print("=" * 60)
    print("S&P Global Commodity Insights News Scraper")
    print("=" * 60)
    print(f"[Main] Keyword : '{keyword}'")
    print(f"[Main] Target  : {tanggal or '(no date filter)'}\n")

    articles = scrape_spglobal(keyword=keyword, tanggal=tanggal)

    if not articles:
        print("[Main] No articles to return.")
        return None

    df = pd.DataFrame(articles)[["title", "date", "url", "content"]]
    print(f"\n[Main] Successfully retrieved {len(df)} article(s).")
    return df


# Script Entry Point

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    keyword = "SAF"
    tanggal = "2025-01-08"

    result = main_spglobal(keyword=keyword, tanggal=tanggal)

    print("\n" + "=" * 60)
    print("HASIL")
    print("=" * 60)

    if result is not None:
        print(f"Total artikel: {len(result)}\n")
        for i, row in result.head(5).iterrows():
            print(f"[{i+1}] {row['title']}")
            print(f"     Date    : {row['date']}")
            print(f"     URL     : {row['url']}")
            content_preview = row["content"][:200] + "..." if row["content"] else "-"
            print(f"     Content : {content_preview}")
            print()

        filename = f"spglobal_{keyword}_{tanggal}.xlsx"
        result.to_excel(filename, index=False, engine="openpyxl")
        print(f"[Output] Saved to '{filename}'")
    else:
        print("Tidak ada artikel ditemukan.")

    print("=" * 60)
    print("SELESAI")
    print("=" * 60)