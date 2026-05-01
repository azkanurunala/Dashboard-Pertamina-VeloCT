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
    extract_news_sitemap_entry,
    get_element_text,
    normalize_to_iso_date,
    rename_to_standard_columns,
)

# Constant

KOMPAS_SITEMAP_URL = "https://www.kompas.com/sitemap.xml"

NS_SITEMAP = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "news": "http://www.google.com/schemas/sitemap-news/0.9",
}

# HTTP headers sent with every article content request
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    )
}

# HTTP request timeout in seconds
REQUEST_TIMEOUT = 15

# Maximum recursion depth when traversing nested sitemap indexes
MAX_SITEMAP_DEPTH = 3

# Delay in seconds between sitemap fetch requests
SITEMAP_FETCH_DELAY = 0.15

# Delay in seconds between article sub-page requests
ARTICLE_PAGE_DELAY = 0.5

# Delay in seconds between article content fetches
CONTENT_FETCH_DELAY = 1.0

# CSS classes of Kompas-specific non-content elements to remove before parsing
KOMPAS_UNWANTED_CLASSES = [
    "kompasidRec__wrap", "kompasidRec__subs", "kompasidRec__title",
    "articleRelated", "article__related", "inner__sidebar",
    "inject-baca-juga", "ads-on-body",
]

# Prefixes that identify non-content lines (cross-links, CTAs, etc.)
KOMPAS_BOILERPLATE_PREFIXES = re.compile(
    r"^(baca\s+juga|download\s+sekarang|dalam\s+segala\s+situasi)",
    re.IGNORECASE,
)

# Sitemap Traversa

def _is_sitemap_index(root: ET.Element) -> bool:
    """
    Determine whether a sitemap XML root represents an index (has <sitemap> tags and no <url> tags).
    """
    has_sitemap_tags = root.findall(".//sm:sitemap", NS_SITEMAP)
    has_url_tags     = root.findall(".//sm:url",     NS_SITEMAP)
    return len(has_sitemap_tags) > 0 and len(has_url_tags) == 0


def _collect_article_sitemaps(root: ET.Element, depth: int = 0) -> list[str]:
    """
    Recursively traverse sitemap indexes to collect Kompas news article sitemap URLs while respecting depth limits and filtering relevant paths.
    """
    if depth > MAX_SITEMAP_DEPTH:
        print(f"[Sitemap] Warning: max depth {MAX_SITEMAP_DEPTH} reached.")
        return []

    article_sitemaps: list[str] = []
    indent = "  " * depth

    for sitemap_tag in root.findall(".//sm:sitemap", NS_SITEMAP):
        loc = sitemap_tag.find("sm:loc", NS_SITEMAP)
        href = get_element_text(loc)

        if not href or "news" not in href.lower():
            continue

        print(f"{indent}[Sitemap] Checking: {href}")

        try:
            content = fetch_xml(href)
            subroot = ET.fromstring(content)

            if _is_sitemap_index(subroot):
                print(f"{indent}  └─ Sitemap index — drilling down...")
                nested = _collect_article_sitemaps(subroot, depth + 1)
                article_sitemaps.extend(nested)
            else:
                url_count = len(subroot.findall(".//sm:url", NS_SITEMAP))
                print(f"{indent}  └─ Article sitemap — {url_count} URLs found.")
                article_sitemaps.append(href)

            time.sleep(SITEMAP_FETCH_DELAY)

        except Exception as exc:
            print(f"{indent}  └─ [Error] {exc}")
            continue

    return article_sitemaps

# Keyword Searc

def find_articles_by_keyword(keyword: str) -> list[dict]:
    """
    Crawl Kompas sitemap tree to find and return articles whose title or keywords match the given keyword using case-insensitive whole-word matching.
    """
    try:
        root = ET.fromstring(fetch_xml(KOMPAS_SITEMAP_URL))
    except Exception as exc:
        print(f"[Sitemap] Failed to fetch main sitemap: {exc}")
        return []

    print("[Sitemap] Crawling sitemap tree to find article sitemaps...")
    article_sitemaps = _collect_article_sitemaps(root)

    if not article_sitemaps:
        print("[Sitemap] No article sitemaps found.")
        return []

    print(f"\n[Search] Found {len(article_sitemaps)} article sitemap(s). Starting keyword search...\n")

    # Compile a whole-word, case-insensitive pattern for the keyword
    keyword_pattern = re.compile(
        r"\b" + re.escape(keyword.strip().lower()) + r"\b"
    )

    results: list[dict] = []

    for idx, sitemap_url in enumerate(article_sitemaps, start=1):
        print(f"[Search] ({idx}/{len(article_sitemaps)}) Processing: {sitemap_url}")

        try:
            content = fetch_xml(sitemap_url)
            subroot = ET.fromstring(content)
            url_tags = subroot.findall(".//sm:url", NS_SITEMAP)
            print(f"   URLs in this sitemap: {len(url_tags)}")

            for url_tag in url_tags:
                info = extract_news_sitemap_entry(url_tag)
                if not info:
                    continue

                title    = (info.get("title")    or "").lower()
                keywords = (info.get("keywords") or "").lower()

                if keyword_pattern.search(title) or keyword_pattern.search(keywords):
                    results.append({
                        "Judul":   info["title"] or info["link"],
                        "Link":    info["link"],
                        "Tanggal": info["date"] or "-",
                    })

            print(f"   Matching articles so far: {len(results)}")

        except Exception as exc:
            print(f"[Search] Error processing {sitemap_url}: {exc}")
            continue

        time.sleep(SITEMAP_FETCH_DELAY)

    print(f"\n[Search] Total articles matching '{keyword}': {len(results)}")
    return results

# Content Cleaning (Kompas-specific

def _clean_article_content(content_div: BeautifulSoup) -> str:
    """
    Clean Kompas article content by removing non-content elements and extracting relevant text into normalized paragraphs.
    """
    if not content_div:
        return "-"

    # Remove noise tags unconditionally
    for tag in content_div.find_all(["aside", "script", "style", "iframe", "noscript"]):
        tag.decompose()

    # Collect Kompas-specific non-content divs, then decompose (two-pass to
    # avoid stale-reference errors from decomposing during iteration)
    unwanted = [
        tag
        for css_class in KOMPAS_UNWANTED_CLASSES
        for tag in content_div.find_all(class_=css_class)
    ]
    for tag in unwanted:
        tag.decompose()

    # Extract text from content elements
    paragraphs: list[str] = []
    for el in content_div.find_all(["p", "li", "h2", "h3"]):
        text = el.get_text(strip=True)

        if not text or len(text) < 5:
            continue

        # Skip boilerplate lines (e.g. "Baca Juga", "Download Sekarang")
        if KOMPAS_BOILERPLATE_PREFIXES.search(text):
            continue

        paragraphs.append(text)

    if not paragraphs:
        return "-"

    # Normalise internal whitespace and join
    content = "\n\n".join(paragraphs)
    return re.sub(r"\s+", " ", content).strip()

# Pagination (Kompas-specific

def _get_total_article_pages(soup: BeautifulSoup) -> int:
    """
    Read the total sub-page count from Kompas article pagination.

    Kompas encodes page numbers in ``?page=N`` query parameters on
    ``<a class="paging__link">`` anchors inside ``<div class="paging__wrap">``.

    Parameters
    ----------
    soup : BeautifulSoup
        Parsed HTML of an article page.

    Returns
    -------
    int
        Highest page number found, or 1 if pagination is absent.
    """
    paging_wrap = soup.select_one("div.paging__wrap")
    if not paging_wrap:
        return 1

    max_page = 1
    for link in paging_wrap.select("a.paging__link"):
        href = link.get("href", "")
        if "?page=" not in href:
            continue
        try:
            page_num = int(href.split("?page=")[-1].split("&")[0])
            max_page = max(max_page, page_num)
        except (ValueError, IndexError):
            continue

    return max_page

# Article Content Fetchin

def fetch_article_content(url: str) -> str:
    """
    Extract the highest Kompas article page number from pagination links, defaulting to 1 if none exist.
    """
    all_content: list[str] = []
    base_url = url.split("?")[0]  # Strip any existing query parameters

    try:
        # --- Page 1 ---
        response = requests.get(base_url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        content_div = soup.select_one("div.read__content")
        if not content_div:
            print(f"[Content] Content div not found: {base_url}")
            return "N/A"

        cleaned = _clean_article_content(content_div)
        if cleaned and cleaned != "-":
            all_content.append(cleaned)

        # --- Sub-pages 2..N ---
        total_pages = _get_total_article_pages(soup)
        if total_pages > 1:
            print(f"   [Content] {total_pages} sub-pages detected.")

            for page_num in range(2, total_pages + 1):
                page_url = f"{base_url}?page={page_num}"
                print(f"   [Content] Fetching sub-page {page_num}: {page_url}")

                r_page = requests.get(page_url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
                r_page.raise_for_status()
                page_soup = BeautifulSoup(r_page.content, "html.parser")

                content_div = page_soup.select_one("div.read__content")
                if not content_div:
                    print(f"   [Content] Content div not found on sub-page {page_num}.")
                    continue

                cleaned = _clean_article_content(content_div)
                if cleaned and cleaned != "-":
                    all_content.append(cleaned)

                time.sleep(ARTICLE_PAGE_DELAY)

        if not all_content:
            print(f"[Content] No valid content found: {url}")
            return "N/A"

        return "\n\n".join(all_content)

    except Exception as exc:
        print(f"[Content] Failed to fetch {url}: {exc}")
        return "N/A"

# Orchestratio

def scrape_kompas(keyword: str, date: str | datetime | None = None) -> list[dict]:
    """
    Fetch Kompas articles by keyword with optional date filtering and populate each result with its full content.
    """
    articles = find_articles_by_keyword(keyword)

    if not articles:
        print("[Scrape] No articles found for this keyword.")
        return []

    # --- Optional date filter ---
    if date is not None:
        if isinstance(date, datetime):
            iso_date = date.strftime("%Y-%m-%d")
        else:
            iso_date = normalize_to_iso_date(str(date)) or str(date)

        articles = [a for a in articles if a.get("Tanggal") == iso_date]
        print(f"[Scrape] After date filter ({iso_date}): {len(articles)} article(s) remaining.")

    if not articles:
        return []

    # --- Fetch full content for each matched article ---
    for i, article in enumerate(articles, start=1):
        print(f"[Scrape] ({i}/{len(articles)}) Fetching content: {article['Link']}")
        article["Konten"] = fetch_article_content(article["Link"])
        time.sleep(CONTENT_FETCH_DELAY)

    return articles

# Public Entry Poin

def main_kompas(keyword: str = "MotoGP", tanggal: str | None = None) -> pd.DataFrame | None:
    """
    Run Kompas scraping workflow for a keyword and date, returning a standardized DataFrame or None if no results or errors occur.
    """
    try:
        articles = scrape_kompas(keyword, date=tanggal)

        if not articles:
            print("[Main] No articles found.")
            return None

        df = rename_to_standard_columns(pd.DataFrame(articles))

        if df.empty:
            print("[Main] No articles found after formatting.")
            return None

        print(f"[Main] Successfully scraped {len(df)} article(s) from Kompas.")
        return df

    except Exception as exc:
        print(f"[Main] Unexpected error: {exc}")
        return None

# Script Entry Poin

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()  # Load .env only when run directly, not when imported

    result = main_kompas(keyword="Ekonomi", tanggal="2026-01-28")

    if result is not None:
        print(result)

        # Output filename kept in Indonesian as per project convention
        result.to_excel("kompas_results.xlsx", index=False, engine="openpyxl")
        print(f"\n[Output] Saved to 'kompas_results.xlsx'")
        print(f"[Output] Total articles : {len(result)}")
        print(f"[Output] Columns        : {', '.join(result.columns)}")