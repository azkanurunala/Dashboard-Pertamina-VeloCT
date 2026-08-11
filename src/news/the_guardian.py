import os
import sys
import time
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from helpers.scraping_helper import fetch_xml
from helpers.scraping_utils import (
    NS_SITEMAP,
    clean_scraped_text,
    dedup_by_key,
    extract_news_sitemap_entry,
    is_valid_paragraph,
    normalize_to_iso_date,
    rename_to_standard_columns,
)

import xml.etree.ElementTree as ET


# Constants

GUARDIAN_SITEMAP_URL = "http://www.theguardian.com/sitemaps/news.xml"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    )
}
REQUEST_TIMEOUT     = 15
CONTENT_FETCH_DELAY = 1.5   # seconds between article content fetches
MIN_PARAGRAPH_LENGTH = 15   # Guardian uses slightly longer threshold than default

# Guardian-specific spam/boilerplate phrases — passed to is_valid_paragraph
# as extra_spam_keywords in addition to the shared _SPAM_KEYWORDS in utils.
GUARDIAN_EXTRA_SPAM: tuple[str, ...] = (
    "share on",
    "view image in fullscreen",
    "photograph:",
    "marketing preferences",
    "enter your email",
    "skip past newsletter",
    "after newsletter promotion",
    "privacy notice:",
    "get updates about",
    "sign up to",
)

GUARDIAN_ALLOWED_SECTIONS: set[str] = {
    "world",
    "business",
    "commentisfree",
    "us-news",
    "australia-news",
    "environment",
    "politics",
    "uk-news",
    "global-development",
    "money",
    "news",
    "science",
    "the-grid",
}

# Sitemap Querying

def _get_articles_by_keyword(keyword: str) -> list[dict]:
    """
    Fetch The Guardian sitemap and return articles matching a keyword across title, keywords, or URL.
    """
    print(f"[Sitemap] Fetching {GUARDIAN_SITEMAP_URL}")
    content = fetch_xml(GUARDIAN_SITEMAP_URL)
    if not content:
        print("[Sitemap] Failed to fetch sitemap.")
        return []

    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        print(f"[Sitemap] Failed to parse XML: {exc}")
        return []

    url_tags = root.findall(".//sm:url", NS_SITEMAP)
    print(f"[Sitemap] {len(url_tags)} URL(s) in sitemap.")

    keyword_lower = keyword.lower()
    results: list[dict] = []

    for url_tag in url_tags:
        info = extract_news_sitemap_entry(url_tag)
        if not info or not info.get("link"):
            continue

        title    = info.get("title",    "") or ""
        keywords = info.get("keywords", "") or ""
        link     = info.get("link",     "") or ""

        if (
            keyword_lower in title.lower()
            or keyword_lower in keywords.lower()
            or keyword_lower in link.lower()
        ):
            try:
                section = link.split("theguardian.com/")[1].split("/")[0]
                if section not in GUARDIAN_ALLOWED_SECTIONS:
                    continue
            except (IndexError, AttributeError):
                continue

            print(f"\n[Match] {title}")
            print(f"        {link}")
            results.append({
                "Judul":   title or link,
                "Link":    link,
                "Tanggal": info.get("date", "-"),
            })

    print(f"[Sitemap] {len(results)} article(s) matched keyword '{keyword}'.")
    return results


# Article Content Fetching

def _fetch_article_content(url: str) -> str:
    """
    Fetch a Guardian article page, remove non-content elements, and return cleaned body text or "N/A" if no usable content is found.
    """
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Remove noise elements globally (two-pass to avoid stale refs)
        for tag in soup(["script", "style", "figure", "iframe", "noscript",
                          "aside", "form", "button", "svg", "gu-island"]):
            tag.decompose()

        content_div = soup.select_one("div.article-body-commercial-selector")
        if not content_div:
            print(f"[Content] Article body not found: {url}")
            return "N/A"

        paragraphs: list[str] = []
        for el in content_div.find_all(["p", "h2", "h3", "li"]):
            text = el.get_text(strip=True)
            if (
                is_valid_paragraph(
                    text,
                    min_length=MIN_PARAGRAPH_LENGTH,
                    extra_spam_keywords=GUARDIAN_EXTRA_SPAM,
                )
                and text not in paragraphs
            ):
                paragraphs.append(text)

        if not paragraphs:
            print(f"[Content] No valid paragraphs found: {url}")
            return "N/A"

        raw = "\n\n".join(paragraphs)
        return clean_scraped_text(raw, strip_control_chars=True)

    except Exception as exc:
        print(f"[Content] Failed to fetch content: {exc}")
        return "N/A"


# Orchestration

def scrape_the_guardian(
    keyword: str,
    tanggal: str | None = None,
    fetch_content: bool = True,
) -> list[dict]:
    """
    Scrape Guardian articles by keyword with optional date filtering and optional full-content retrieval.
    """
    keyword = keyword.strip()
    iso_date = normalize_to_iso_date(str(tanggal)) if tanggal else None

    print("=" * 70)
    print(f"[Guardian] Keyword : '{keyword}'")
    print(f"[Guardian] Date    : {iso_date or '(no filter)'}")
    print(f"[Guardian] Mode    : {'full content' if fetch_content else 'metadata only'}")
    print("=" * 70)

    articles = _get_articles_by_keyword(keyword)

    if not articles:
        print("[Guardian] No articles found.")
        return []

    # Date filter
    if iso_date:
        articles = [a for a in articles if a.get("Tanggal") == iso_date]
        print(f"[Guardian] {len(articles)} article(s) after date filter ({iso_date}).")

    if not articles:
        print("[Guardian] No articles after filtering.")
        return []

    # Content fetch
    if fetch_content:
        print(f"\n[Guardian] Fetching content for {len(articles)} article(s)...")
        for i, article in enumerate(articles, start=1):
            print(f"  ({i}/{len(articles)}) {article['Judul'][:60]}...")
            article["Konten"] = _fetch_article_content(article["Link"])
            time.sleep(CONTENT_FETCH_DELAY)
        print("[Guardian] Content fetch complete.")
    else:
        for article in articles:
            article["Konten"] = ""

    return articles


# Public Entry Point

def main_guardian(
    keyword: str,
    tanggal: str | None = None,
    fetch_content: bool = True,
) -> pd.DataFrame | None:
    """
    Run the Guardian scraping workflow for a keyword with optional date and content fetching, returning a standardized DataFrame or None.
    """
    articles = scrape_the_guardian(keyword, tanggal=tanggal, fetch_content=fetch_content)
    if not articles:
        return None
    df = rename_to_standard_columns(pd.DataFrame(articles))
    return df


# Script Entry Point  (multi-keyword / keyword-group example)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    # Map group label -> list of keywords to search
    # Each unique article is collected once, tagged with its group + keyword.
    # KEYWORDS: dict[str, list[str]] = {
    #     "volatility index ": [
    #     # "volatility ",
    #     "market volatility ", "financial volatility "
    #     ],
    # }

    # TANGGAL      = None   # e.g. "2025-01-15" — None means no date filter
    # FETCH_KONTEN = True   # False = metadata only (faster)

    # all_results: list[dict] = []
    # seen_links:  set[str]   = set()

    # for group_keyword, keyword_list in KEYWORDS.items():
    #     for kw in [group_keyword] + keyword_list:
    #         kw = kw.strip()
    #         if not kw:
    #             continue

    #         print(f"\n{'=' * 70}")
    #         print(f"[Group: {group_keyword}] Keyword: '{kw}'")
    #         print(f"{'=' * 70}")

    #         hasil = scrape_the_guardian(kw, tanggal=TANGGAL, fetch_content=FETCH_KONTEN)

    #         for article in hasil:
    #             link = article.get("Link", "")
    #             if link and link not in seen_links:
    #                 seen_links.add(link)
    #                 article["Group"]   = group_keyword
    #                 article["Keyword"] = kw
    #                 all_results.append(article)

    # print(f"\n{'=' * 70}")
    # print(f"TOTAL UNIQUE ARTICLES: {len(all_results)}")
    # print(f"{'=' * 70}")

    # if all_results:
    #     df = pd.DataFrame(
    #         all_results,
    #         columns=["Group", "Keyword", "Judul", "Link", "Tanggal", "Konten"],
    #     )
    #     df = rename_to_standard_columns(df)
    #     filename = f"guardian_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    #     df.to_excel(filename, index=False, engine="openpyxl")
    #     print(f"\n[Output] Saved to '{filename}'")

    #     print("\nPreview (first 5 articles):")
    #     for i, row in enumerate(all_results[:5], start=1):
    #         print(f"\n{i}. [{row['Group']}] via '{row['Keyword']}'")
    #         print(f"   Title   : {row['Judul']}")
    #         print(f"   Date    : {row['Tanggal']}")
    #         print(f"   URL     : {row['Link']}")
    #         if row.get("Konten"):
    #             print(f"   Content : {row['Konten'][:200]}...")
    
    keywords = [
        "nuclear"]

    all_sections = set()
    for kw in keywords:
        result = main_guardian(keyword=kw, tanggal="2026-04-29", fetch_content=False)
        if result is not None:
            sections = set(
                u.split("theguardian.com/")[1].split("/")[0]
                for u in result["url"].tolist()
            )
            print(f"{kw}: {sections}")
            all_sections.update(sections)

    print(f"\nSemua seksi yang muncul: {all_sections}")