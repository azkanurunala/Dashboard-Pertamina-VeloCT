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
from helpers.scraping_utils import extract_news_sitemap_entry, normalize_to_iso_date


# Constants

BLOOMBERG_TECHNOZ_BASE_URL    = "https://www.bloombergtechnoz.com"
BLOOMBERG_TECHNOZ_SITEMAP_URL = f"{BLOOMBERG_TECHNOZ_BASE_URL}/sitemap-news.xml"

NS_SITEMAP = {
    "sm":   "http://www.sitemaps.org/schemas/sitemap/0.9",
    "news": "http://www.google.com/schemas/sitemap-news/0.9",
}

# HTTP headers sent with every request to avoid bot-detection blocks
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    )
}

# Delay in seconds between article sub-page requests (rate-limit courtesy)
REQUEST_DELAY_SECONDS = 1.0

# HTTP request timeout in seconds
REQUEST_TIMEOUT = 10

# Maximum number of sub-pages to fetch per article (safety guard)
MAX_ARTICLE_PAGES = 10

# Date format used internally throughout this scraper for display/comparison
DISPLAY_DATE_FORMAT = "%d %b %Y"

BLOOMBERG_ALLOWED_KANALS: list[str] = [
    "market",
    "global",
    "nasional",
    "finansial",
    "energi",
    "sektor riil",
    "green",
]


# Sitemap Search
#
# bloombergtechnoz.com/search was rate-limited/down (429/502) on effectively
# every request in production, wasting a full network round-trip per
# keyword x sheet with zero results. sitemap-news.xml is a standard Google
# News sitemap covering roughly the last day of articles — same window this
# pipeline actually scrapes (yesterday's date) — so it's fetched once per
# process and searched in-memory per keyword instead.

_SITEMAP_ENTRIES_CACHE: list[dict] | None = None


def _get_sitemap_entries() -> list[dict]:
    """Return parsed sitemap entries, fetching sitemap-news.xml once per process."""
    global _SITEMAP_ENTRIES_CACHE
    if _SITEMAP_ENTRIES_CACHE is not None:
        return _SITEMAP_ENTRIES_CACHE

    print(f"[Sitemap] Fetching {BLOOMBERG_TECHNOZ_SITEMAP_URL}...")
    try:
        content = fetch_xml(BLOOMBERG_TECHNOZ_SITEMAP_URL)
        root = ET.fromstring(content)
        url_tags = root.findall(".//sm:url", NS_SITEMAP)
        _SITEMAP_ENTRIES_CACHE = [
            info for url_tag in url_tags
            if (info := extract_news_sitemap_entry(url_tag))
        ]
        print(f"[Sitemap] {len(_SITEMAP_ENTRIES_CACHE)} article(s) in sitemap.")
    except Exception as exc:
        print(f"[Sitemap] Failed to fetch sitemap: {exc}")
        _SITEMAP_ENTRIES_CACHE = []

    return _SITEMAP_ENTRIES_CACHE


def find_articles_by_keyword(keyword: str, filter_date: str | None = None) -> list[dict]:
    """
    Search the cached Bloomberg Technoz news sitemap for articles whose
    title or keywords match, optionally restricted to a single ISO date.
    """
    entries = _get_sitemap_entries()
    keyword_pattern = re.compile(r"\b" + re.escape(keyword.strip().lower()) + r"\b")

    results: list[dict] = []
    for info in entries:
        if filter_date and info.get("date") != filter_date:
            continue

        title    = (info.get("title")    or "").lower()
        keywords = (info.get("keywords") or "").lower()
        if not (keyword_pattern.search(title) or keyword_pattern.search(keywords)):
            continue

        iso_date = info.get("date")
        display_date = (
            datetime.strptime(iso_date, "%Y-%m-%d").strftime(DISPLAY_DATE_FORMAT)
            if iso_date else "-"
        )
        results.append({
            "title": info["title"] or info["link"],
            "link":  info["link"],
            "date":  display_date,
        })

    suffix = f" on {filter_date}" if filter_date else ""
    print(f"[Search] {len(results)} article(s) matched keyword '{keyword}'{suffix}.")
    return results


# Article Content Fetching

def _extract_kanal(soup: BeautifulSoup) -> str:
    """Extract kanal utama dari JSON-LD BreadcrumbList."""
    import json
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string)
            if data.get("@type") == "BreadcrumbList":
                items = data.get("itemListElement", [])
                if items:
                    return items[0].get("name", "").lower()
        except Exception:
            continue
    return ""

def fetch_article_content(url: str) -> tuple[str, str]:
    """
    Fetch a Bloomberg Technoz article and return its combined text.
    """
    all_text_lines: list[str] = []
    kanal = ""

    try:
        for page in range(1, MAX_ARTICLE_PAGES + 1):
            # Page 1 uses the canonical URL; subsequent pages append /N
            page_url = url if page == 1 else f"{url}/{page}"
            print(f"  [Content] Fetching sub-page {page}: {page_url}")

            response = requests.get(page_url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            if page == 1:
                kanal = _extract_kanal(soup)
                print(f"  [Content] Kanal: '{kanal}'")

            # Locate article body containers on this sub-page
            articles = soup.find_all("div", class_="article")
            if not articles:
                print(f"  [Content] No article div on sub-page {page} — stopping.")
                break

            found_content = False
            for article in articles:
                detail_div = article.find("div", class_="detail-in")
                if not detail_div:
                    continue

                found_content = True

                # Collect paragraph text, skipping "Baca Juga" cross-links
                for p in detail_div.find_all("p"):
                    text = p.get_text(strip=True)
                    if text and "Baca Juga" not in text:
                        all_text_lines.append(text)

                # Collect ordered list items
                for ol in detail_div.find_all("ol"):
                    for li in ol.find_all("li", recursive=False):
                        text = li.get_text(strip=True)
                        if text:
                            all_text_lines.append(text)

            if not found_content:
                print(f"  [Content] No usable content on sub-page {page} — stopping.")
                break

            # Bloomberg Technoz signals the final sub-page with a "No more pages" div
            status_div = soup.find("div", class_="status")
            if status_div:
                no_more = status_div.find("div", class_="no-more")
                if no_more and no_more.get_text(strip=True) == "No more pages":
                    print(f"  [Content] End of article reached on sub-page {page}.")
                    break

            time.sleep(REQUEST_DELAY_SECONDS)

        print(f"  [Content] {len(all_text_lines)} text lines collected across all sub-pages.")
        return "\n".join(all_text_lines), kanal

    except Exception as exc:
        print(f"  [Content] Failed to fetch article {url}: {exc}")
        import traceback
        traceback.print_exc()
        return ""


# Orchestration

def scrape_bloomberg_technoz_news(
    query: str,
    filter_date: str | None = None,
) -> list[dict]:
    """
    Find Bloomberg Technoz articles by query via the cached news sitemap,
    optionally restricted to a single date, and enrich each match with
    full article content.
    """
    iso_date = None
    if filter_date:
        try:
            iso_date = datetime.strptime(filter_date, DISPLAY_DATE_FORMAT).strftime("%Y-%m-%d")
            print(f"[Scrape] Target date: {filter_date}")
        except ValueError as exc:
            print(f"[Scrape] Warning: could not parse filter_date='{filter_date}': {exc}")

    all_results = find_articles_by_keyword(query, filter_date=iso_date)

    print(f"\n[Scrape] Sitemap search complete. {len(all_results)} article(s) passed the filter.")

    if not all_results:
        return []

    # --- Fetch full article content for each matched article ---
    print(f"\n[Scrape] Fetching full content for {len(all_results)} article(s)...")

    keyword_pattern = re.compile(r"\b" + re.escape(query.strip()) + r"\b", re.IGNORECASE)
    filtered_results: list[dict] = []

    for i, article in enumerate(all_results, start=1):
        print(f"[Scrape] [{i}/{len(all_results)}] {article['title']}")
        article["konten"], kanal = fetch_article_content(article["link"])
        # Filter kanal
        if kanal and kanal not in BLOOMBERG_ALLOWED_KANALS:
            print(f"  [Filter] Kanal '{kanal}' tidak diizinkan — dilewati.")
            continue

        # Filter keyword
        if not keyword_pattern.search(article["title"]) and not keyword_pattern.search(article["konten"]):
            print(f"[Skip] '{query.strip()}' tidak ditemukan: {article['title']!r}")
            continue
        filtered_results.append(article)

    print("[Scrape] Content fetching complete.")
    return filtered_results


# Public Entry Point

def main_bloomberg_technoz(
    query: str,
    filter_tanggal: str | None = None,
) -> pd.DataFrame | None:
    """
    Scrape Bloomberg Technoz articles for a query with normalized date filtering and return the results as a clean, structured DataFrame.
    """
    # Default to today if no date supplied
    if filter_tanggal is None:
        filter_tanggal = datetime.now().strftime("%Y-%m-%d")

    # Normalise to ISO first, then convert to the display format used internally
    iso_date = normalize_to_iso_date(filter_tanggal)
    if iso_date:
        display_date = datetime.strptime(iso_date, "%Y-%m-%d").strftime(DISPLAY_DATE_FORMAT)
    else:
        print(f"[Main] Warning: could not normalise filter_tanggal='{filter_tanggal}' — using as-is.")
        display_date = filter_tanggal

    print(f"[Main] Query  : '{query}'")
    print(f"[Main] Target : {display_date}\n")

    results = scrape_bloomberg_technoz_news(query, filter_date=display_date)

    if not results:
        print("\n[Main] No articles found.")
        return None

    df = pd.DataFrame(results)
    df["date"] = pd.to_datetime(df["date"], format=DISPLAY_DATE_FORMAT, errors="coerce").dt.date
    df = df.rename(columns={"konten": "content", "link": "url"})

    return df


# Script Entry Point

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()  # Load .env only when run directly, not when imported

    result = main_bloomberg_technoz(
        query="nuklir",
        filter_tanggal="2026-03-26",
    )

    if result is not None:
        print(result)

        # Output filename kept in Indonesian as per project convention
        result.to_excel("bloomberg_technoz_results.xlsx", index=False, engine="openpyxl")
        print(f"\n[Output] Saved to 'bloomberg_technoz_results.xlsx'")
        print(f"[Output] Total articles : {len(result)}")
        print(f"[Output] Columns        : {', '.join(result.columns)}")
