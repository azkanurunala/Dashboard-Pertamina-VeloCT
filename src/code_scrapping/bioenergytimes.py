import os
import sys
import time
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from helpers.scraping_utils import normalize_to_iso_date, rename_to_standard_columns


# Constants

BIOENERGYTIMES_BASE_URL = "https://bioenergytimes.com"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    )
}

REQUEST_TIMEOUT       = 15
PAGE_FETCH_DELAY      = 2.0   # seconds between paginated list requests
CONTENT_FETCH_DELAY   = 2.0   # seconds between article content fetches
MIN_CONTENT_LENGTH    = 10    # minimum <p> character length to include


# Search Results Page Fetching

def _fetch_search_page(keyword: str, page: int) -> list[dict]:
    """
    Fetch one Bioenergytimes search page and return parsed article metadata.    
    """
    kw_enc = keyword.replace(" ", "+")
    url    = (
        f"{BIOENERGYTIMES_BASE_URL}/?s={kw_enc}"
        if page == 1
        else f"{BIOENERGYTIMES_BASE_URL}/page/{page}/?s={kw_enc}"
    )

    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
    except Exception as exc:
        print(f"[Fetch] Failed to fetch page {page}: {exc}")
        return []

    articles: list[dict] = []

    for module in soup.select("div.tdb_module_loop.td_module_wrap"):
        try:
            title_elem = module.select_one("h3.entry-title.td-module-title a")
            if not title_elem:
                continue

            title = (title_elem.get("title") or title_elem.get_text(strip=True)).strip()
            link  = title_elem.get("href", "").strip()

            if not title or not link:
                continue

            # Parse date — Bioenergytimes uses "Month DD, YYYY" (e.g. "January 12, 2026")
            date_elem = (
                module.select_one("span.td-post-date time")
                or module.select_one("span.td-post-date")
            )
            raw_date = date_elem.get_text(strip=True) if date_elem else ""
            iso_date = normalize_to_iso_date(raw_date) or raw_date or "N/A"

            articles.append({"Judul": title, "Tanggal": iso_date, "Link": link})

        except Exception as exc:
            print(f"[Fetch] Error parsing article card: {exc}")
            continue

    return articles


# Article Content Fetching

def _fetch_article_content(url: str) -> str:
    """
    Fetch a Bioenergytimes article and return its paragraph text.
    """
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        article_body = soup.select_one("div.tdb_single_content div.tdb-block-inner")
        if not article_body:
            print(f"[Content] Content container not found: {url}")
            return "N/A"

        paragraphs = [
            p.get_text(strip=True)
            for p in article_body.find_all("p")
            if len(p.get_text(strip=True)) > MIN_CONTENT_LENGTH
        ]

        if not paragraphs:
            return "N/A"

        content = "\n\n".join(paragraphs)
        print(f"[Content] Extracted {len(content)} characters.")
        return content

    except Exception as exc:
        print(f"[Content] Failed to fetch content: {exc}")
        return "N/A"


# Orchestration

def scrape_bioenergytimes(
    keyword: str,
    tanggal: str | None = None,
) -> pd.DataFrame | None:
    """
    Scrape Bioenergytimes articles by keyword and optional publication date.
    """
    # Normalise filter date to ISO
    iso_filter: str | None = None
    filter_dt:  datetime | None = None

    if tanggal is not None:
        iso_filter = normalize_to_iso_date(str(tanggal))
        if not iso_filter:
            print(f"[Scrape] Warning: could not normalise tanggal='{tanggal}' — using as-is.")
            iso_filter = str(tanggal)
        try:
            filter_dt = datetime.strptime(iso_filter, "%Y-%m-%d")
            print(f"[Scrape] Date filter: {iso_filter}")
        except ValueError:
            print(f"[Scrape] Warning: could not parse normalised date '{iso_filter}'.")

    matched: list[dict] = []
    page       = 1
    stop_early = False

    while not stop_early:
        print(f"\n[Scrape] Fetching page {page}...")
        articles = _fetch_search_page(keyword, page)

        if not articles:
            print(f"[Scrape] No articles on page {page} — stopping.")
            break

        for article in articles:
            raw_tgl = article.get("Tanggal", "")

            # Parse the (already ISO-normalised) date for comparison
            try:
                article_dt = datetime.strptime(raw_tgl, "%Y-%m-%d") if raw_tgl not in ("N/A", "") else None
            except ValueError:
                article_dt = None

            if filter_dt and article_dt:
                if article_dt < filter_dt:
                    print(f"[Scrape] Article dated {raw_tgl} is older than target — stopping.")
                    stop_early = True
                    break
                elif article_dt == filter_dt:
                    matched.append(article)
                # else: article is newer than target — skip silently
            else:
                matched.append(article)

        if stop_early:
            break

        page += 1
        time.sleep(PAGE_FETCH_DELAY)

    print(f"\n[Scrape] {len(matched)} article(s) found.")

    if not matched:
        return None

    # --- Fetch full content for each matched article ---
    print(f"[Scrape] Fetching content for {len(matched)} article(s)...\n")
    for i, article in enumerate(matched, start=1):
        print(f"[Scrape] [{i}/{len(matched)}] {article['Judul'][:60]}...")
        article["Konten"] = _fetch_article_content(article["Link"])
        if i < len(matched):
            time.sleep(CONTENT_FETCH_DELAY)

    df = rename_to_standard_columns(pd.DataFrame(matched))
    return df


# Public Entry Point

def main_bioenergytimes(
    keyword: str = "SAF Indonesia",
    tanggal: str | None = "2026-01-12",
) -> pd.DataFrame | None:
    """
    Run Bioenergytimes scraping and return results as a DataFrame.
    """
    print(f"[Main] Keyword : '{keyword}'")
    print(f"[Main] Target  : {tanggal or '(no date filter)'}\n")

    df = scrape_bioenergytimes(keyword, tanggal=tanggal)

    if df is None or df.empty:
        print("[Main] No articles found.")
        return None

    print(f"[Main] Successfully scraped {len(df)} article(s).")
    return df


# Script Entry Point

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    result = main_bioenergytimes(keyword="SAF Indonesia", tanggal="2026-01-12")

    if result is not None:
        print(result)
        result.to_excel("bioenergytimes_results.xlsx", index=False, engine="openpyxl")
        print(f"\n[Output] Saved to 'bioenergytimes_results.xlsx'")
        print(f"[Output] Total articles : {len(result)}")
        print(f"[Output] Columns        : {', '.join(result.columns)}")
    else:
        print("\n[Output] No articles found.")