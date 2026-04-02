import html
import json
import os
import re
import sys
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from helpers.scraping_utils import (
    NS_NEWS,
    NS_SITEMAP,
    extract_news_sitemap_entry,
    normalize_to_iso_date,
    rename_to_standard_columns,
)


# Constants

OILPRICE_SITEMAP_URL = "https://oilprice.com/googlenews.xml"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    )
}
REQUEST_TIMEOUT    = 15
MIN_CONTENT_LENGTH = 10    # minimum <p> character length to include


# Sitemap Parsing

def _parse_sitemap(
    keyword: str | None = None,
    iso_date: str | None = None,
) -> list[dict]:
    """
    Parse the OilPrice sitemap with optional keyword and date filters, returning matching article metadata.
    """
    import xml.etree.ElementTree as ET

    print(f"[Sitemap] Fetching {OILPRICE_SITEMAP_URL}")
    try:
        response = requests.get(OILPRICE_SITEMAP_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except Exception as exc:
        print(f"[Sitemap] Failed to fetch/parse XML: {exc}")
        return []

    url_tags = root.findall(".//sm:url", NS_SITEMAP)
    print(f"[Sitemap] {len(url_tags)} total entries in sitemap.")

    keyword_lower = keyword.lower() if keyword else None
    articles: list[dict] = []

    for url_tag in url_tags:
        info = extract_news_sitemap_entry(url_tag)
        if not info:
            continue

        # Date filter
        if iso_date and info["date"] != iso_date:
            continue

        # Keyword filter — substring match against title and keywords fields
        if keyword_lower:
            if (
                keyword_lower not in info["title"].lower()
                and keyword_lower not in info["keywords"].lower()
            ):
                continue

        articles.append({
            "Judul":   info["title"],
            "Tanggal": info["date"],
            "Link":    info["link"],
        })

    # Log applied filters
    active_filters = []
    if keyword:
        active_filters.append(f"keyword='{keyword}'")
    if iso_date:
        active_filters.append(f"date={iso_date}")
    filter_text = f" with {', '.join(active_filters)}" if active_filters else ""
    print(f"[Sitemap] {len(articles)} matching article(s){filter_text}.")

    return articles


# Article Content Fetching

def _fetch_article_content(url: str) -> str:
    """
    Fetch an OilPrice article and return cleaned body text using JSON-LD first, with HTML parsing as fallback.
    """
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # --- Strategy 1: JSON-LD NewsArticle.articleBody ---
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue

            if isinstance(data, dict) and data.get("@type") == "NewsArticle":
                article_body = data.get("articleBody", "")
                if article_body:
                    # Unescape HTML entities and normalise whitespace
                    article_body = html.unescape(article_body)
                    article_body = re.sub(r"\s+", " ", article_body).strip()
                    print(f"[Content] JSON-LD: extracted {len(article_body)} characters.")
                    return article_body

        # --- Strategy 2: HTML fallback ---
        print(f"[Content] No JSON-LD found — falling back to HTML parsing.")
        article_body = soup.select_one("div#article-content.wysiwyg.clear")
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
        print(f"[Content] HTML: extracted {len(content)} characters.")
        return content

    except Exception as exc:
        print(f"[Content] Failed to fetch content: {exc}")
        return "N/A"


# Orchestration

def scrape_oilprice(
    keyword: str | None = None,
    tanggal: str | None = None,
) -> pd.DataFrame | None:
    """
    Scrape OilPrice articles via sitemap with optional keyword and date filtering, returning a DataFrame with full content.
    """
    iso_date = normalize_to_iso_date(str(tanggal)) if tanggal else None
    if tanggal and not iso_date:
        print(f"[Scrape] Warning: could not normalise tanggal='{tanggal}' — ignoring date filter.")

    articles = _parse_sitemap(keyword=keyword, iso_date=iso_date)

    if not articles:
        print("[Scrape] No articles found.")
        return None

    for i, article in enumerate(articles, start=1):
        print(f"\n[Scrape] [{i}/{len(articles)}] {article['Judul'][:60]}...")
        article["Konten"] = _fetch_article_content(article["Link"])

    df = rename_to_standard_columns(pd.DataFrame(articles))
    return df


# Public Entry Point

def main_oilprice(
    keyword: str | None = None,
    tanggal: str | None = None,
) -> pd.DataFrame | None:
    """
    Run the OilPrice scraping workflow with optional keyword and date filters, returning a DataFrame or None if no results are found.
    """
    print(f"\n{'=' * 60}")
    print("OilPrice.com News Scraper")
    print(f"{'=' * 60}")
    print(f"[Main] Keyword : {keyword or '(no keyword filter)'}")
    print(f"[Main] Target  : {tanggal or '(no date filter)'}\n")

    df = scrape_oilprice(keyword=keyword, tanggal=tanggal)

    if df is None or df.empty:
        print("[Main] No articles found.")
        return None

    print(f"\n{'=' * 60}")
    print(f"[Main] Successfully scraped {len(df)} article(s).")
    print(f"{'=' * 60}")
    print("\nPreview:")
    print(df[["title", "date"]].to_string(index=False))

    return df


# Script Entry Point

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    result = main_oilprice(keyword="Oil Price", tanggal="2026-03-06")

    if result is not None:
        kw_slug  = (result.iloc[0]["title"][:20].replace(" ", "_") if not result.empty else "results")
        filename = (
            f"oilprice_{result.iloc[0].get('date', 'unknown')}.xlsx"
            if not result.empty
            else "oilprice_results.xlsx"
        )
        result.to_excel(filename, index=False, engine="openpyxl")
        print(f"\n[Output] Saved to '{filename}'")
        print(f"[Output] Total articles : {len(result)}")
        print(f"[Output] Columns        : {', '.join(result.columns)}")
        print(f"\n{'=' * 60}")
        print("Content preview (first article):")
        print(f"{'=' * 60}")
        print(result.iloc[0]["content"][:500] + "...")