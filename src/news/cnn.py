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
    NS_SITEMAP,
    clean_scraped_text,
    dedup_by_key,
    extract_news_sitemap_entry,
    is_valid_paragraph,
    normalize_to_iso_date,
)


# Constants

CNN_SITEMAP_URL  = "https://www.cnn.com/sitemap/news.xml"
REQUEST_HEADERS  = {"User-Agent": "Mozilla/5.0"}
REQUEST_TIMEOUT  = 20

# Delay between sitemap sub-URL requests
SITEMAP_FETCH_DELAY = 0.5

# Delay between article content fetches
CONTENT_FETCH_DELAY = 1.0

# CNN-specific boilerplate patterns passed to clean_scraped_text
CNN_BOILERPLATE_PATTERNS = [
    r"Sign up for CNN.*",
    r"Read more:.*",
    r"Watch:.*",
    r"CNN\'s\s+[\w\s,]+contributed to this report\.?",
    r"This story.*contributed to this report\.?",
]


# Sitemap Parsing

def _parse_cnn_sitemap_entry(url_tag: ET.Element) -> dict | None:
    """
    Parse a CNN sitemap entry into article metadata, prioritizing lastmod for date and using URL slug as a title fallback.
    """
    # Read <sm:lastmod> before calling the shared parser (which may
    # overwrite date with the <news:publication_date> value)
    lastmod_tag = url_tag.find("sm:lastmod", NS_SITEMAP)
    lastmod     = (lastmod_tag.text or "").strip() if lastmod_tag is not None else ""
    lastmod_iso = lastmod.split("T")[0] if "T" in lastmod else lastmod

    info = extract_news_sitemap_entry(url_tag)
    if not info:
        return None

    link  = info["link"]
    title = info["title"]

    # Use <sm:lastmod> as date if present — CNN priority
    date = lastmod_iso or info["date"] or "-"

    # URL-slug fallback title
    if not title or title == "(No Title)":
        title = link.rstrip("/").split("/")[-1].replace("-", " ").title()

    return {"title": title, "link": link, "tanggal": date}


# Sitemap Crawling

def _get_all_cnn_articles() -> list[dict]:
    """
    Fetch and parse all CNN article entries from the sitemap, handling both index and leaf sitemap structures.
    """
    results: list[dict] = []

    try:
        root_content = fetch_xml(CNN_SITEMAP_URL)
        root         = ET.fromstring(root_content)

        # Determine whether root is a sitemap index or a leaf
        if root.tag.endswith("sitemapindex"):
            sub_urls = [
                s.find("sm:loc", NS_SITEMAP).text
                for s in root.findall(".//sm:sitemap", NS_SITEMAP)
                if s.find("sm:loc", NS_SITEMAP) is not None
            ]
        else:
            sub_urls = [CNN_SITEMAP_URL]

        for sub_url in sub_urls:
            try:
                sub_content = fetch_xml(sub_url)
                sub_root    = ET.fromstring(sub_content)
                for url_tag in sub_root.findall(".//sm:url", NS_SITEMAP):
                    info = _parse_cnn_sitemap_entry(url_tag)
                    if info:
                        results.append(info)
                time.sleep(SITEMAP_FETCH_DELAY)
            except Exception:
                continue

    except Exception:
        pass

    return results


# Article Content Fetching

def _fetch_article_content(url: str) -> str:
    """
    Fetch a CNN article page, remove headline/related noise, and return cleaned body text from relevant content containers or fallback parsing.
    """
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Remove "Top Headlines" section and its following list
        top_headlines = soup.find("h2", id="top-headlines")
        if top_headlines:
            sibling = top_headlines.find_next_sibling()
            while sibling:
                if sibling.name == "div" and sibling.find("ul"):
                    sibling.decompose()
                    break
                sibling = sibling.find_next_sibling()
            top_headlines.decompose()

        # Remove related-link list-elevate blocks near "top headlines" h2
        for list_div in soup.find_all("div", class_="list-elevate"):
            prev_h2 = list_div.find_previous("h2")
            if prev_h2 and "top headlines" in prev_h2.get_text().lower():
                list_div.decompose()

        # Collect paragraphs from known content containers
        paragraphs: list[str] = []
        for selector in [
            "div.article__content",
            "div.video-resource__description",
            "main",
            "article",
        ]:
            container = soup.select_one(selector)
            if not container:
                continue
            for el in container.find_all(["h2", "p", "li"]):
                text = el.get_text(strip=True)
                if is_valid_paragraph(text, min_length=8) and text not in paragraphs:
                    paragraphs.append(text)
            if len(paragraphs) >= 3:
                break

        # Full-page fallback
        if len(paragraphs) < 2:
            for el in soup.find_all(["h2", "p", "li"]):
                text = el.get_text(strip=True)
                if is_valid_paragraph(text, min_length=10) and text not in paragraphs:
                    paragraphs.append(text)

        if not paragraphs:
            return "N/A"

        raw = "\n\n".join(paragraphs)
        return clean_scraped_text(raw, extra_patterns=CNN_BOILERPLATE_PATTERNS)

    except Exception:
        return "N/A"


# Sitemap Source

def scrape_cnn_international(keyword: str, tanggal: str | None = None) -> list[dict]:
    """
    Fetch CNN articles from sitemap, optionally filter by date, enrich with content, and return those matching the keyword.
    """
    print("\n[Sitemap] Fetching all CNN articles from sitemap...")
    articles = _get_all_cnn_articles()
    print(f"[Sitemap] {len(articles)} total article(s) in sitemap.")

    # Date filter
    if tanggal:
        articles = [a for a in articles if a.get("tanggal") == tanggal]
        print(f"[Sitemap] {len(articles)} article(s) after date filter ({tanggal}).")

    # Fetch content
    print(f"[Sitemap] Fetching content for {len(articles)} article(s)...")
    with_content: list[dict] = []
    for i, article in enumerate(articles, start=1):
        print(f"[Sitemap] ({i}/{len(articles)}) {article['title'][:60]}...")
        content = _fetch_article_content(article["link"])
        time.sleep(CONTENT_FETCH_DELAY)
        with_content.append({
            "title":   article["title"],
            "date":    article["tanggal"],
            "url":     article["link"],
            "content": content,
        })

    # Keyword filter (whole-word against title and content)
    keyword_pattern = re.compile(
        r"\b" + re.escape(keyword.strip().lower()) + r"\b"
    )
    matched = [
        a for a in with_content
        if keyword_pattern.search(a["title"].lower())
        or keyword_pattern.search(a["content"].lower())
    ]

    print(f"[Sitemap] {len(matched)} article(s) matched keyword '{keyword}'.")
    return matched


# Public Entry Point

def main_google_news_cnn(
    keyword: str,
    tanggal: str | None = None,
) -> list[dict]:
    """
    Collect CNN articles from Google News and sitemap sources, then merge and deduplicate the results.
    """
    iso_date = normalize_to_iso_date(tanggal) if tanggal else None
    if tanggal and not iso_date:
        print(f"[Main] Warning: could not normalise tanggal='{tanggal}' — ignoring date filter.")

    # --- Source 1: Google News ---
    print("=" * 70)
    print("STEP 1: Google News (CNN only) + Content")
    print("=" * 70)
    google_articles = scrape_google_news_with_content(
        keyword,
        filter_date=iso_date,
        filter_platform="CNN",
        use_selenium_fallback=True,
    )
    print(f"[Google News] {len(google_articles)} CNN article(s) found.")

    # --- Source 2: CNN Sitemap ---
    print("\n" + "=" * 70)
    print("STEP 2: CNN Sitemap + Content")
    print("=" * 70)
    sitemap_articles = scrape_cnn_international(keyword, tanggal=iso_date)
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

    keyword = "Geopolitical"
    print(f"Scraping CNN (Google News + Sitemap) — keyword: '{keyword}'\n")

    results = main_google_news_cnn(keyword=keyword, tanggal=None)

    print(f"\n[Output] Total: {len(results)} article(s)")

    if results:
        df       = pd.DataFrame(results)
        filename = f"cnn_combined_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        print(df)
        df.to_excel(filename, index=False, engine="openpyxl")
        print(f"[Output] Saved to '{filename}'")
    else:
        print("[Output] No articles found.")