import json
import os
import re
import sys
import time
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from helpers.scraping_utils import (
    clean_scraped_text,
    dedup_by_key,
    fetch_rss_entries,
    normalize_to_iso_date,
)


# Constants

REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}

# Regex that identifies a Tempo article URL by its canonical patterns:
#   https://xxx.tempo.co/read/2084660/slug
#   https://www.tempo.co/hukum/slug-2112318
# Tolerant of trailing slashes and query strings.
ARTICLE_URL_RE = re.compile(
    r"^https?://([a-z0-9-]+\.)?tempo\.co/.*(/read/\d+/|-\d{6,})(/)?($|\?)",
    re.IGNORECASE,
)

# All known Tempo RSS feed URLs — used as fallback when Selenium search fails
TEMPO_RSS_FEEDS = [
    "https://rss.tempo.co/",
    "https://rss.tempo.co/full-content/",
    "https://rss.tempo.co/nasional",
    "https://rss.tempo.co/bisnis",
    "https://rss.tempo.co/metro",
    "https://rss.tempo.co/dunia",
    "https://rss.tempo.co/bola",
    "https://rss.tempo.co/tekno",
    "https://rss.tempo.co/otomotif",
    "https://rss.tempo.co/seleb",
    "https://rss.tempo.co/gaya",
    "https://rss.tempo.co/travel",
    "https://rss.tempo.co/difabel",
    "https://rss.tempo.co/creativelab",
    "https://rss.tempo.co/inforial",
    "https://rss.tempo.co/event",
    "https://rss.tempo.co/politik",
    "https://rss.tempo.co/hukum",
    "https://rss.tempo.co/ekonomi",
    "https://rss.tempo.co/lingkungan",
    "https://rss.tempo.co/wawancara",
    "https://rss.tempo.co/sains",
    "https://rss.tempo.co/investigasi",
    "https://rss.tempo.co/cekfakta",
    "https://rss.tempo.co/kolom",
    "https://rss.tempo.co/hiburan",
    "https://rss.tempo.co/internasional",
    "https://rss.tempo.co/olahraga",
    "https://rss.tempo.co/sepakbola",
    "https://rss.tempo.co/digital",
    "https://rss.tempo.co/gaya-hidup",
]

# Tempo-specific boilerplate patterns passed to clean_scraped_text
TEMPO_BOILERPLATE_PATTERNS = [
    r"Baca berita.*?klik di sini",
    r"Scroll ke bawah.*",
    r"Lulus dari Jurusan.*?(hak asasi manusia)?",
    r"This is breaking news.*",
]

# Minimum paragraph character length — shorter paragraphs are discarded
MIN_PARAGRAPH_LENGTH = 30

# Delay in seconds between article content fetches
CONTENT_FETCH_DELAY = 1.0

# Seconds to wait for JS rendering after Selenium page load
SELENIUM_RENDER_WAIT = 3

# Maximum search result pages to fetch via Selenium
SELENIUM_MAX_PAGES = 3


# Selenium Search

def _search_via_selenium(
    keyword: str,
    start_date: str | None = None,
    end_date: str | None = None,
    max_pages: int = SELENIUM_MAX_PAGES,
    headless: bool = True,
) -> tuple[list[str], str]:
    """
    Search Tempo via Selenium to collect deduplicated article URLs for a keyword and optional date range, returning the URLs with a status flag.
    """
    kw_enc  = requests.utils.quote(keyword.strip())
    all_urls: list[str] = []

    def _build_url(page: int) -> str:
        url = f"https://www.tempo.co/search?page={page}&q={kw_enc}"
        if start_date and end_date:
            url += f"&start_date={start_date}&end_date={end_date}"
        return url

    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1280,900")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("user-agent=Mozilla/5.0")

    driver = None
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options,
        )

        for page in range(1, max_pages + 1):
            driver.get(_build_url(page))
            time.sleep(SELENIUM_RENDER_WAIT)

            anchors = driver.find_elements(By.CSS_SELECTOR, "a[href]")
            print(f"[Search] Page {page}: {len(anchors)} anchors found.")

            page_urls = list({
                href.split("#")[0].strip()
                for a in anchors
                if (href := a.get_attribute("href"))
                and ARTICLE_URL_RE.match(href.split("#")[0].strip())
            })

            if not page_urls:
                if page == 1:
                    return [], "changed"
                break

            all_urls.extend(page_urls)
            time.sleep(1)

        return list(dict.fromkeys(all_urls)), "ok"  # preserve order, dedup

    except Exception as exc:
        print(f"[Search] Selenium error: {exc}")
        return [], "error"

    finally:
        if driver:
            driver.quit()


# Article Metadata Extraction

def _extract_article_meta(url: str) -> tuple[str, str]:
    """
    Extract article title and ISO publication date from a Tempo URL using JSON-LD with meta tag fallbacks.
    """
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=25)
        response.raise_for_status()
        soup  = BeautifulSoup(response.text, "html.parser")
        title = ""
        date  = ""

        # --- JSON-LD structured data ---
        for tag in soup.find_all("script", type="application/ld+json"):
            raw = (tag.string or "").strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue

            candidates = data if isinstance(data, list) else [data]
            for obj in candidates:
                if isinstance(obj, dict) and obj.get("@type") in ("NewsArticle", "Article"):
                    title = obj.get("headline") or obj.get("name") or title
                    dt    = obj.get("datePublished") or obj.get("dateCreated") or ""
                    if dt:
                        date = dt.split("T")[0]
                    break
            if title or date:
                break

        # --- meta article:published_time fallback ---
        if not date:
            meta = soup.find("meta", property="article:published_time")
            if meta and meta.get("content"):
                date = meta["content"].split("T")[0]

        # --- og:title / <title> fallback ---
        if not title:
            og = soup.find("meta", property="og:title")
            if og and og.get("content"):
                title = og["content"].strip()
            elif soup.title:
                title = soup.title.get_text(strip=True)

        return title.strip(), date.strip()

    except Exception:
        return "", ""


# Article Content Extraction

def _fetch_article_content(url: str) -> str:
    """
    Fetch a Tempo article page, remove common non-content elements, and return the cleaned main body text or "N/A" if unavailable.
    """
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=25)
        soup     = BeautifulSoup(response.text, "html.parser")

        container = soup.select_one(
            "div#isi, div.detail-content, article, div.detail-area"
        ) or soup

        # Remove noise elements (two-pass to avoid stale-reference errors)
        noise_selectors = (
            "script, style, iframe, figure, aside, nav, "
            "div[class*='ad'], div[class*='iklan'], "
            "div[class*='share'], div[class*='related'], "
            "div[class*='author'], div[class*='penulis'], "
            "div.text-neutral-900"
        )
        for tag in container.select(noise_selectors):
            tag.decompose()

        paragraphs = [
            re.sub(r"\s+", " ", p.get_text(" ", strip=True))
            for p in container.find_all("p")
            if len(re.sub(r"\s+", " ", p.get_text(" ", strip=True))) > MIN_PARAGRAPH_LENGTH
        ]

        if not paragraphs:
            return "N/A"

        raw_content = "\n\n".join(paragraphs)
        return clean_scraped_text(raw_content, extra_patterns=TEMPO_BOILERPLATE_PATTERNS)

    except Exception:
        return "N/A"


# Orchestration

def scrape_tempo(
    keyword: str,
    tanggal: str | None = None,
    rss_limit: int = 80,
) -> list[dict]:
    """
    Scrape Tempo articles by keyword with an optional date filter using Selenium search first, then RSS fallback, and return each match with full content.
    """
    kw_lower = keyword.lower().strip()

    # Normalise date to ISO — handles both "DD-MM-YYYY" and "YYYY-MM-DD"
    iso_date = normalize_to_iso_date(tanggal) if tanggal else None

    print(f"[Scrape] keyword='{kw_lower}' | date_filter='{iso_date}' | rss_limit={rss_limit}")

    candidates: list[dict] = []

    # ------------------------------------------------------------------ #
    # Strategy 1: Selenium search                                          #
    # ------------------------------------------------------------------ #
    urls, status = _search_via_selenium(
        keyword,
        start_date=iso_date,
        end_date=iso_date,
        headless=True,
    )

    if status == "ok" and urls:
        print(f"[Scrape] Selenium search OK: {len(urls)} URLs found.")

        for url in urls:
            title, article_date = _extract_article_meta(url)

            if iso_date:
                if not article_date:
                    print(f"[Skip] No date metadata — skipping: {url}")
                    continue
                if article_date != iso_date:
                    print(f"[Skip] Date mismatch ({article_date} ≠ {iso_date}): {url}")
                    continue

            candidates.append({"title": title, "link": url, "tanggal": article_date})

    # ------------------------------------------------------------------ #
    # Strategy 2: RSS fallback                                             #
    # ------------------------------------------------------------------ #
    else:
        print(f"[Scrape] Selenium status='{status}' — falling back to RSS feeds.")

        # keyword_pattern = re.compile(r"\b" + re.escape(kw_lower) + r"\b")
        keyword_pattern = re.compile(r"\b" + re.escape(kw_lower.strip()) + r"\b", re.IGNORECASE)
        
        for feed_url in TEMPO_RSS_FEEDS:
            try:
                entries = fetch_rss_entries(feed_url, limit=rss_limit)
            except Exception:
                continue

            for entry in entries:
                title   = entry.get("title",   "")
                link    = entry.get("link",    "")
                tgl     = entry.get("tanggal", "")
                summary = entry.get("summary", "") or ""

                if not link:
                    continue

                # Keyword check against title + summary
                # if kw_lower not in (title + " " + summary).lower():
                #     continue
                if not keyword_pattern.search((title + " " + summary).lower()):
                    continue

                # Date filter
                if iso_date and tgl and tgl != iso_date:
                    continue

                candidates.append({"title": title, "link": link, "tanggal": tgl})

    # Deduplicate by URL before fetching content
    candidates = dedup_by_key(candidates, key="link")

    if not candidates:
        print("[Scrape] No articles found (Selenium + RSS fallback).")
        return []

    print(f"[Scrape] {len(candidates)} unique article(s) found. Fetching content...")

    results: list[dict] = []
    for i, article in enumerate(candidates, start=1):
        print(f"[Scrape] ({i}/{len(candidates)}) {article['link']}")
        results.append({
            "title":   article.get("title",   ""),
            "date":    article.get("tanggal", ""),
            "url":     article.get("link",    ""),
            "content": _fetch_article_content(article["link"]),
        })
        time.sleep(CONTENT_FETCH_DELAY)

    return results


# Public Entry Point

def main_tempo(
    keyword: str = "minyak",
    tanggal: str | None = None,
) -> pd.DataFrame | None:
    """
    Run the Tempo scraping workflow for a keyword and optional date, returning a structured DataFrame or None if no results are found.
    """
    print(f"[Main] Keyword : '{keyword}'")
    print(f"[Main] Target  : {tanggal or '(no date filter)'}\n")

    articles = scrape_tempo(keyword, tanggal=tanggal)

    if not articles:
        print("[Main] No articles found.")
        return None

    df = pd.DataFrame(articles)[["title", "date", "url", "content"]]
    print(f"[Main] Successfully scraped {len(df)} article(s).")
    return df


# Script Entry Point

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    result = main_tempo(keyword="kurs", tanggal=None)

    if result is not None:
        print(result.head())
        result.to_excel("tempo_results.xlsx", index=False, engine="openpyxl")
        print(f"\n[Output] Saved to 'tempo_results.xlsx'")
        print(f"[Output] Total articles : {len(result)}")
        print(f"[Output] Columns        : {', '.join(result.columns)}")