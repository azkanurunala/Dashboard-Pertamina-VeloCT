import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from news.google_news import scrape_google_news_with_content
from helpers.scraping_helper import fetch_xml
from helpers.scraping_utils import (
    NS_NEWS,
    NS_SITEMAP,
    dedup_by_key,
    extract_news_sitemap_entry,
    normalize_to_iso_date,
)


# Constants

CNBC_SITEMAP_URL = "https://www.cnbc.com/sitemap_news.xml"

REQUEST_HEADERS  = {"User-Agent": "Mozilla/5.0"}
REQUEST_TIMEOUT  = 25

# Delay in seconds between article content fetches (sitemap source)
CONTENT_FETCH_DELAY = 0.5

# Minimum paragraph character length to include in extracted content
MIN_PARAGRAPH_LENGTH = 30


# Sitemap Parsing

def _parse_sitemap_entry(url_tag: ET.Element) -> dict | None:
    """
    Parse a CNBC sitemap entry into article metadata, using URL slug as a title fallback when needed.
    """
    info = extract_news_sitemap_entry(url_tag)
    print(info)
    
    if not info:
        return None

    title = info["title"]
    url   = info["link"]
    date  = info["date"]

    # CNBC-specific fallback: derive title from URL slug if absent
    # e.g. "https://cnbc.com/.../geopolitical-risks-2025.html"
    #      -> "Geopolitical Risks 2025"
    if not title or title == "(No Title)":
        title = url.rstrip("/").split("/")[-1].replace("-", " ").title()

    return {"title": title, "url": url, "date": date}


# Article Content Fetching

def _fetch_article_content(url: str) -> str:
    """
    Fetch a CNBC article page, remove common non-content elements, and return the extracted body text or "N/A" if unavailable.
    """
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        soup     = BeautifulSoup(response.text, "html.parser")

        containers = soup.select(
            "div.ArticleBody-articleBody, "
            "section#ArticleBody, "
            'div[class*="article-body"]'
        ) or [soup]

        # Noise selectors — collect and decompose (two-pass to avoid stale refs)
        noise_css = (
            "script, style, iframe, figure, "
            'div[class*="ad"], div[data-module="mps-slot"], '
            'span[class*="share"], aside, '
            "div.RelatedContent-collapsibleContent, "
            'div[class*="RelatedContent"], div[class*="related"]'
        )

        text_lines: list[str] = []
        for container in containers:
            for bad in container.select(noise_css):
                bad.decompose()

            for el in container.find_all(["p", "li", "h2"]):
                text = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
                if len(text) > MIN_PARAGRAPH_LENGTH:
                    text_lines.append(text)

        # Full-page fallback if no content found in known containers
        if not text_lines:
            for p in soup.find_all("p"):
                text = re.sub(r"\s+", " ", p.get_text(" ", strip=True))
                if len(text) > MIN_PARAGRAPH_LENGTH:
                    text_lines.append(text)

        return "\n\n".join(text_lines) if text_lines else "N/A"

    except Exception as exc:
        print(f"[Content] Failed to fetch content: {exc}")
        return "N/A"


# Sitemap Source

def _scrape_cnbc_sitemap(
    keyword: str,
    tanggal: str | None = None,
    fetch_content: bool = True,
) -> list[dict]:
    """
    Fetch CNBC sitemap articles with optional date filtering, optionally enrich them with content, and return those matching the keyword.
    """
    raw_xml = fetch_xml(CNBC_SITEMAP_URL)
    if not raw_xml:
        print("[Sitemap] Failed to fetch CNBC sitemap.")
        return []

    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError as exc:
        print(f"[Sitemap] Failed to parse CNBC sitemap XML: {exc}")
        return []

    # Collect all entries, applying optional date filter
    candidates: list[dict] = []
    for url_tag in root.findall(".//sm:url", NS_SITEMAP):
        info = _parse_sitemap_entry(url_tag)
        if not info:
            continue
        if tanggal and info["date"] != tanggal:
            continue
        candidates.append(info)

    print(f"[Sitemap] {len(candidates)} article(s) after date filter.")

    # Fetch content and apply keyword filter
    keyword_pattern = re.compile(
        r"\b" + re.escape(keyword.strip().lower()) + r"\b"
    )
    results: list[dict] = []

    for article in candidates:
        content = "N/A"
        if fetch_content:
            content = _fetch_article_content(article["url"])
            time.sleep(CONTENT_FETCH_DELAY)

        article["content"] = content

        title_lower   = article["title"].lower()
        url_lower     = article["url"].lower()
        content_lower = content.lower() if fetch_content else ""

        if (
            keyword_pattern.search(title_lower)
            or keyword_pattern.search(url_lower)
            or (fetch_content and keyword_pattern.search(content_lower))
        ):
            results.append(article)

    print(f"[Sitemap] {len(results)} article(s) matched keyword '{keyword}'.")
    return results


# Public Entry Point

def main_google_news_cnbc(
    keyword: str,
    tanggal: str | None = None,
) -> list[dict]:
    """
    Collect CNBC articles from Google News and sitemap sources, then merge and deduplicate the results.
    """
    # Normalise date once — pass ISO string downstream to both sources
    iso_date = normalize_to_iso_date(tanggal) if tanggal else None
    if tanggal and not iso_date:
        print(f"[Main] Warning: could not normalise tanggal='{tanggal}' — ignoring date filter.")

    # --- Source 1: Google News ---
    print("=" * 70)
    print("STEP 1: Google News (CNBC only) + Content")
    print("=" * 70)
    google_articles = scrape_google_news_with_content(
        keyword,
        filter_date=iso_date,
        filter_platform="CNBC",
        use_selenium_fallback=True,
    )
    print(f"[Google News] {len(google_articles)} CNBC article(s) found.")

    # --- Source 2: CNBC Sitemap ---
    print("\n" + "=" * 70)
    print("STEP 2: CNBC Sitemap + Content")
    print("=" * 70)
    sitemap_articles = _scrape_cnbc_sitemap(keyword, tanggal=iso_date, fetch_content=True)
    print(f"[Sitemap] {len(sitemap_articles)} article(s) found.")

    # --- Merge and deduplicate ---
    print("\n" + "=" * 70)
    print("STEP 3: Merge + Deduplicate")
    print("=" * 70)
    combined = google_articles + sitemap_articles
    print(f"[Merge] Before dedup: {len(combined)}")
    unique = dedup_by_key(combined, key="url")
    print(f"[Merge] After dedup : {len(unique)}")

    return unique


# Script Entry Point

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    keyword = "market"
    print(f"Scraping CNBC (Google News + Sitemap) — keyword: '{keyword}'\n")

    results = main_google_news_cnbc(keyword=keyword, tanggal="2026-04-29")
    print([r["url"] for r in results[:5]])
    
    # print(f"\n[Output] Total: {len(results)} article(s)")

    # if results:
    #     df       = pd.DataFrame(results)
    #     filename = f"cnbc_combined_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    #     print(df)
    #     df.to_excel(filename, index=False, engine="openpyxl")
    #     print(f"[Output] Saved to '{filename}'")
    # else:
    #     print("[Output] No articles found.")