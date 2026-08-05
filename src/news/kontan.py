import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Allow importing shared utilities from the sibling 'helpers' directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from helpers.scraping_helper import fetch_xml
from helpers.scraping_utils import (
    NS_SITEMAP,
    clean_scraped_text,
    extract_news_sitemap_entry,
    normalize_to_iso_date,
)


# Constants

KONTAN_SITEMAP_URL = "https://www.kontan.co.id/sitemap.xml"

# HTTP headers sent with every article content request
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# HTTP request timeout in seconds
REQUEST_TIMEOUT = 15

# Delay in seconds between sitemap fetch requests (rate-limit courtesy)
SITEMAP_FETCH_DELAY = 0.15

# Delay in seconds between article content fetches
CONTENT_FETCH_DELAY = 1.0

# Ordered list of CSS selectors tried when locating the article body container.
# The first selector that yields non-empty <p> content is used.
KONTAN_CONTENT_SELECTORS = [
    "div.article-detail-content",
    "div.detail-content",
    "div.content-article",
    "div.article-content",
    "div#article-content",
    "article div.content",
    "div.post-content",
    "div.read__content",
]

# Minimum number of <p> tags required to accept a full-page fallback
FALLBACK_MIN_PARAGRAPHS = 3

EXCLUDED_SUBDOMAINS = ["insight.kontan.co.id"]

KONTAN_ALLOWED_SUBDOMAINS: set[str] = {
    "nasional", "keuangan", "investasi", "industri",
    "internasional", "finansial", "global", "analisis",
    "fokus", "aktual", "pressrelease", "tabloid",
    "pusatdata",
}

# Sitemap Traversal

def _collect_sub_sitemaps(root: ET.Element) -> list[str]:
    """
    Extract and deduplicate sub-sitemap URLs from a sitemap index by collecting valid sitemap links from <loc> elements.
    """
    links: list[str] = []
    seen:  set[str]  = set()

    for loc in root.findall(".//sm:loc", NS_SITEMAP):
        href = (loc.text or "").strip()
        if not href:
            continue

        is_sitemap_url = (
            href.endswith(".xml")
            or href.endswith(".xml.gz")
            or "sitemap" in href
            or "/sitemaps/" in href
        )

        if is_sitemap_url and href not in seen:
            subdomain = href.split("//")[1].split(".kontan")[0]
            if subdomain not in KONTAN_ALLOWED_SUBDOMAINS:
                continue
            seen.add(href)
            links.append(href)

    return links


# Content Fetching

def _fetch_article_content(url: str) -> str:
    """
    Fetch and extract cleaned article text from a Kontan URL using prioritized selectors with a full-page fallback if needed.
    """
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # --- Try each known content container selector in order ---
        content: str | None = None

        for selector in KONTAN_CONTENT_SELECTORS:
            div = soup.select_one(selector)
            if not div:
                continue
            paragraphs = [p.get_text(strip=True) for p in div.find_all("p") if p.get_text(strip=True)]
            if paragraphs:
                content = "\n\n".join(paragraphs)
                break

        # --- Full-page fallback: collect all <p> tags ---
        if not content:
            paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
            if len(paragraphs) > FALLBACK_MIN_PARAGRAPHS:
                content = "\n\n".join(paragraphs)

        return clean_scraped_text(content) if content else "N/A"

    except Exception:
        return "N/A"


# Keyword Search

# Per-process cache: the sitemap tree + entries are re-crawled on every
# keyword call otherwise, and a single run searches ~25 keywords against the
# same live sitemap. Caching turns O(keywords x sub-sitemaps) network fetches
# into O(sub-sitemaps) — keyword filtering afterward is in-memory.
_SUB_SITEMAPS_CACHE: list[str] | None = None
_SITEMAP_ENTRIES_CACHE: dict[str, list[dict]] = {}


def _get_sub_sitemaps() -> list[str]:
    """Return the list of relevant sub-sitemap URLs, crawling once per process."""
    global _SUB_SITEMAPS_CACHE
    if _SUB_SITEMAPS_CACHE is not None:
        return _SUB_SITEMAPS_CACHE

    try:
        root = ET.fromstring(fetch_xml(KONTAN_SITEMAP_URL))
    except Exception as exc:
        print(f"[Sitemap] Failed to fetch main sitemap: {exc}")
        _SUB_SITEMAPS_CACHE = []
        return _SUB_SITEMAPS_CACHE

    _SUB_SITEMAPS_CACHE = _collect_sub_sitemaps(root)
    print(f"[Sitemap] Found {len(_SUB_SITEMAPS_CACHE)} sub-sitemap(s).")
    return _SUB_SITEMAPS_CACHE


def _get_sitemap_entries(sub_url: str) -> list[dict]:
    """Return parsed entries for one sub-sitemap, fetching once per process."""
    if sub_url in _SITEMAP_ENTRIES_CACHE:
        return _SITEMAP_ENTRIES_CACHE[sub_url]

    entries: list[dict] = []
    try:
        content = fetch_xml(sub_url)
        subroot = ET.fromstring(content)
        for url_tag in subroot.findall(".//sm:url", NS_SITEMAP):
            info = extract_news_sitemap_entry(url_tag)
            if info and info.get("link"):
                entries.append(info)
    except Exception:
        # Skip unreachable or malformed sub-sitemaps silently
        pass

    time.sleep(SITEMAP_FETCH_DELAY)
    _SITEMAP_ENTRIES_CACHE[sub_url] = entries
    return entries


def _find_articles_by_keyword(keyword: str) -> list[dict]:
    """
    Crawl Kontan sitemaps to find and return articles whose title or URL matches the given keyword using case-insensitive pattern matching.
    """
    sub_sitemaps = _get_sub_sitemaps()
    print(f"[Search] Searching {len(sub_sitemaps)} cached sub-sitemap(s) for '{keyword}'...")

    keyword_lower = keyword.lower()
    keyword_pattern = re.compile(r"\b" + re.escape(keyword_lower) + r"\b")
    results: list[dict] = []

    for sub_url in sub_sitemaps:
        for info in _get_sitemap_entries(sub_url):
            title = (info.get("title") or "").lower()
            link  = (info.get("link")  or "").lower()

            # Kontan uses substring match (not whole-word) to also catch
            # keyword appearances in URL slugs
            if keyword_pattern.search(title) or keyword_pattern.search(link):
                results.append({
                    "judul":    info["title"] or info["link"],
                    "link":     info["link"],
                    "tanggal":  info["date"] or "-",
                    "keywords": info["keywords"],
                })

    print(f"[Search] Total articles matching '{keyword}': {len(results)}")
    return results


# Orchestration

def scrape_kontan(
    keyword: str,
    tanggal: str | datetime | None = None,
) -> list[dict]:
    """
    Scrape Kontan articles by keyword with optional date filtering and return structured results enriched with full content.
    """
    articles = _find_articles_by_keyword(keyword)

    if not articles:
        return []

    # --- Optional date filter ---
    if tanggal is not None:
        if isinstance(tanggal, datetime):
            iso_date = tanggal.strftime("%Y-%m-%d")
        else:
            iso_date = normalize_to_iso_date(str(tanggal)) or str(tanggal)

        articles = [a for a in articles if a.get("tanggal") == iso_date]
        print(f"[Scrape] After date filter ({iso_date}): {len(articles)} article(s) remaining.")

    if not articles:
        return []

    # articles = [
    #     a for a in articles
    #     if not any(sub in a["link"] for sub in EXCLUDED_SUBDOMAINS)
    # ]
    
    # --- Fetch full content for each matched article ---
    results: list[dict] = []

    for i, article in enumerate(articles, start=1):
        print(f"[Scrape] ({i}/{len(articles)}) Fetching content: {article['judul'][:60]}...")
        results.append({
            "title":   article.get("judul",   "-"),
            "date":    article.get("tanggal", "-"),
            "url":     article.get("link",    "-"),
            "content": _fetch_article_content(article["link"]),
        })
        time.sleep(CONTENT_FETCH_DELAY)

    return results


# Public Entry Point

def main_kontan(
    keyword: str = "Ekonomi",
    tanggal: str | None = None,
) -> pd.DataFrame | None:
    """
    Scrape Kontan articles by keyword with optional date normalization and return the results as a structured DataFrame.
    """
    # Normalise date before passing downstream
    if tanggal is not None:
        iso_date = normalize_to_iso_date(tanggal)
        if not iso_date:
            print(f"[Main] Warning: could not normalise tanggal='{tanggal}' — using as-is.")
            iso_date = tanggal
        tanggal = iso_date

    print(f"[Main] Keyword : '{keyword}'")
    print(f"[Main] Target  : {tanggal or '(no date filter)'}\n")

    articles = scrape_kontan(keyword, tanggal=tanggal)

    if not articles:
        print(f"[Main] No articles found for keyword='{keyword}'.")
        return None

    df = pd.DataFrame(articles)[["title", "date", "url", "content"]]
    print(f"[Main] Successfully scraped {len(df)} article(s).")
    return df


# Script Entry Point

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    result = main_kontan(keyword="kurs", tanggal=None)

    if result is not None:
        print(result)
        result.to_excel("kontan_results.xlsx", index=False, engine="openpyxl")
        print(f"\n[Output] Saved to 'kontan_results.xlsx'")
        print(f"[Output] Total articles : {len(result)}")
        print(f"[Output] Columns        : {', '.join(result.columns)}")