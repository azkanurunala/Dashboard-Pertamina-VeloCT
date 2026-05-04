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
from helpers.scraping_helper import fetch_xml
from helpers.scraping_utils import (
    NS_SITEMAP,
    clean_scraped_text,
    extract_news_sitemap_entry,
    normalize_to_iso_date,
    rename_to_standard_columns,
)


# Constants

KONTAN_SITEMAP_URL = "https://www.kontan.co.id/sitemap.xml"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    )
}

REQUEST_TIMEOUT          = 15
SITEMAP_FETCH_DELAY      = 0.15
CONTENT_FETCH_DELAY      = 1.0

# Sub-sitemap path must contain "news" AND at least one of these section names
REQUIRED_SITEMAP_TERM    = "news"
ALLOWED_SITEMAP_SECTIONS = ["internasional", "industri"]

# Article body container specific to the industri/internasional layout
CONTENT_SELECTOR = "div.tmpt-desk-kon"

# Extra boilerplate patterns for this section (built-ins "Baca Juga" and
# "Cek Berita dan Artikel" are already handled by clean_scraped_text)
EXTRA_BOILERPLATE_PATTERNS = [
    r"Selanjutnya.*",
    r"Menarik\s+Dibaca.*",
    r"INDEKS\s+BERITA.*",
]


# Sitemap Traversal

def _collect_section_sitemaps(
    root: ET.Element,
    sections: list[str] | None = None,
) -> list[str]:
    """
    Extract and deduplicate sub-sitemap URLs filtered by sitemap format, required path terms, and specified Kontan sections.
    """
    allowed = sections or ALLOWED_SITEMAP_SECTIONS
    links: list[str] = []
    seen:  set[str]  = set()

    for loc in root.findall(".//sm:loc", NS_SITEMAP):
        href = (loc.text or "").strip()
        if not href:
            continue

        href_lower = href.lower()

        is_sitemap_url = (
            href_lower.endswith(".xml")
            or href_lower.endswith(".xml.gz")
            or "sitemap" in href_lower
            or "/sitemaps/" in href_lower
        )
        if not is_sitemap_url:
            continue

        if (
            REQUIRED_SITEMAP_TERM in href_lower
            and any(s in href_lower for s in allowed)
            and href not in seen
        ):
            seen.add(href)
            links.append(href)

    print(f"[Sitemap] Found {len(links)} sub-sitemap(s) for sections: {allowed}.")
    for i, link in enumerate(links, start=1):
        print(f"   {i}. {link}")

    return links


# Content Fetching

def _fetch_article_content(url: str) -> str:
    """
    Fetch and extract cleaned article text from a Kontan page using a specific content container, removing noise and irrelevant inline links.
    """
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        for bad in soup(["script", "style", "figure", "iframe", "noscript"]):
            bad.decompose()

        div = soup.select_one(CONTENT_SELECTOR)
        if not div:
            print(f"[Content] '{CONTENT_SELECTOR}' not found: {url}")
            return "N/A"

        paragraphs = [
            el.get_text(strip=True)
            for el in div.find_all(["p", "li"])
            if el.get_text(strip=True)
            and not re.search(r"Baca\s+Juga", el.get_text(strip=True), re.IGNORECASE)
        ]

        if not paragraphs:
            print(f"[Content] No paragraph text found: {url}")
            return "N/A"

        return clean_scraped_text(
            "\n\n".join(paragraphs),
            extra_patterns=EXTRA_BOILERPLATE_PATTERNS,
            strip_url_lines=True,
        )

    except Exception as exc:
        print(f"[Content] Failed to fetch {url}: {exc}")
        return "N/A"


# Keyword Search

def _find_articles_by_keyword(
    keyword: str,
    sections: list[str] | None = None,
) -> list[dict]:
    """
    Crawl Kontan section-specific sitemaps to find and return articles whose title or keywords match the given keyword.
    """
    try:
        root = ET.fromstring(fetch_xml(KONTAN_SITEMAP_URL))
    except Exception as exc:
        print(f"[Sitemap] Failed to fetch main sitemap: {exc}")
        return []

    sub_sitemaps  = _collect_section_sitemaps(root, sections=sections)
    keyword_lower = keyword.lower()
    results: list[dict] = []

    for idx, sub_url in enumerate(sub_sitemaps, start=1):
        print(f"[Search] ({idx}/{len(sub_sitemaps)}) Processing: {sub_url}")
        try:
            content = fetch_xml(sub_url)
            subroot = ET.fromstring(content)
            urls    = subroot.findall(".//sm:url", NS_SITEMAP)
            print(f"   URLs in this sitemap: {len(urls)}")

            for url_tag in urls:
                info = extract_news_sitemap_entry(url_tag)
                if not info or not info.get("link"):
                    continue

                title    = (info.get("title")    or "").lower()
                keywords = (info.get("keywords") or "").lower()

                if keyword_lower in title or keyword_lower in keywords:
                    results.append({
                        "Judul":   info["title"] or info["link"],
                        "Link":    info["link"],
                        "Tanggal": info["date"] or "-",
                    })

            print(f"   Matching articles so far: {len(results)}")

        except Exception as exc:
            print(f"[Search] Failed to process {sub_url}: {exc}")
            continue

        time.sleep(SITEMAP_FETCH_DELAY)

    print(f"[Search] Total articles matching '{keyword}': {len(results)}")
    return results


# Orchestration

def scrape_kontan_bbm(keyword: str, date: str | datetime | None = None) -> list[dict]:
    """
    Scrape Kontan industri/internasional articles by keyword with optional date filtering and enrich results with full content.
    """
    articles = _find_articles_by_keyword(keyword, sections=ALLOWED_SITEMAP_SECTIONS)

    if not articles:
        print("[Scrape] No articles found for this keyword.")
        return []

    if date is not None:
        if isinstance(date, datetime):
            iso_date = date.strftime("%Y-%m-%d")
        else:
            iso_date = normalize_to_iso_date(str(date)) or str(date)

        articles = [a for a in articles if a.get("Tanggal") == iso_date]
        print(f"[Scrape] After date filter ({iso_date}): {len(articles)} article(s) remaining.")

    if not articles:
        return []

    for i, article in enumerate(articles, start=1):
        print(f"[Scrape] ({i}/{len(articles)}) Fetching content: {article['Link']}")
        article["Konten"] = _fetch_article_content(article["Link"])
        time.sleep(CONTENT_FETCH_DELAY)

    return articles


# Public Entry Point

def main_kontan_bioenergi(
    keyword: str = "BBM",
    tanggal: str | None = None,
) -> pd.DataFrame | None:
    """
    Scrape Kontan industri/internasional articles with keyword and normalized date filtering, returning a standardized DataFrame.
    """
    if tanggal is not None:
        iso_date = normalize_to_iso_date(tanggal)
        if not iso_date:
            print(f"[Main] Warning: could not normalise tanggal='{tanggal}' — using as-is.")
            iso_date = tanggal
        tanggal = iso_date

    print(f"[Main] Keyword : '{keyword}'")
    print(f"[Main] Target  : {tanggal or '(no date filter)'}\n")

    data = scrape_kontan_bbm(keyword, date=tanggal)

    if not data:
        print("[Main] No articles found.")
        return None

    df = rename_to_standard_columns(pd.DataFrame(data))

    if df.empty:
        print("[Main] DataFrame is empty after formatting.")
        return None

    print(f"[Main] Successfully scraped {len(df)} article(s).")
    return df


# Script Entry Point

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    result = main_kontan_bioenergi(keyword="BBM", tanggal=None)

    if result is not None:
        print(result)
        result.to_excel("kontan_bbm_results.xlsx", index=False, engine="openpyxl")
        print(f"\n[Output] Saved to 'kontan_bbm_results.xlsx'")
        print(f"[Output] Total articles : {len(result)}")
        print(f"[Output] Columns        : {', '.join(result.columns)}")