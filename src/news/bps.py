import os
import re
import sys
import time
from datetime import datetime
from html import unescape

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Allow importing shared utilities from the sibling 'helpers' directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from helpers.scraping_utils import extract_clean_paragraphs, normalize_to_iso_date


# Constants

BPS_API_BASE_LIST   = "https://webapi.bps.go.id/v1/api/list/model/news"
BPS_API_BASE_DETAIL = "https://webapi.bps.go.id/v1/api/view"

# Default domain code for the national BPS portal
DEFAULT_DOMAIN = "0000"

# Language code used when fetching article detail
DEFAULT_LANG = "ind"

# Output folder for Excel results (relative to this script's location)
OUTPUT_FOLDER = "../hasil-scraping"

# Delay in seconds between paginated API requests (rate-limit courtesy)
REQUEST_DELAY_SECONDS = 1

# HTTP request timeout in seconds
REQUEST_TIMEOUT = 15

# Boilerplate keywords specific to BPS press-release footers.
# Paragraphs containing any of these strings are discarded during cleaning.
BPS_BOILERPLATE_KEYWORDS = [
    "narahubung", "contact", "telp", "fax", "email",
    "@bps.go.id", "jl.", "jakarta",
]


# API Layer

def fetch_news_list(api_key: str, page: int = 0, keyword: str | None = None,
                    domain: str = DEFAULT_DOMAIN) -> dict | None:
    """
    Fetch a paginated list of BPS news articles via API with optional keyword filtering, returning JSON or None on failure.
    """
    url = f"{BPS_API_BASE_LIST}/domain/{domain}/page/{page}/key/{api_key}"
    params = {"keyword": keyword} if keyword else {}

    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        print(f"[API] Failed to fetch news list (page={page}): {exc}")
        return None


def fetch_article_detail(api_key: str, news_id: str,
                         domain: str = DEFAULT_DOMAIN,
                         lang: str = DEFAULT_LANG) -> str | None:
    """
    Fetch and clean full BPS article content via API by decoding HTML and removing boilerplate text, returning None on failure.
    """
    url = (
        f"{BPS_API_BASE_DETAIL}/domain/{domain}/model/news"
        f"/lang/{lang}/id/{news_id}/key/{api_key}"
    )

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK":
            return None

        raw_html = data.get("data", {}).get("news", "")
        if not raw_html:
            return None

        # Decode HTML entities before parsing (BPS API returns escaped HTML)
        decoded_html = unescape(raw_html)
        content = extract_clean_paragraphs(decoded_html, boilerplate_keywords=BPS_BOILERPLATE_KEYWORDS)
        return content if content else None

    except Exception as exc:
        print(f"[API] Failed to fetch article detail (news_id={news_id}): {exc}")
        return None


# Response Parsing

def parse_news_list_response(api_response: dict) -> tuple[list[dict], dict | None]:
    """
    Parse BPS news list API response into structured articles with canonical URLs and return pagination metadata.
    """
    if not api_response:
        return [], None
    if api_response.get("status") != "OK":
        return [], None
    if api_response.get("data-availability") != "available":
        return [], None

    data = api_response.get("data", [])
    if len(data) < 2:
        return [], None

    pagination_meta = data[0]
    news_items      = data[1]
    articles: list[dict] = []

    for item in news_items:
        title    = item.get("title", "")
        date_str = item.get("rl_date", "")
        news_id  = item.get("news_id", "")

        # Build slug from title (mirrors BPS URL convention)
        slug = title.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug).strip("-")

        # Build canonical article URL
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
            y  = parsed_date.strftime("%Y")
            m  = parsed_date.strftime("%m")
            d  = parsed_date.strftime("%d")
            link = f"https://www.bps.go.id/id/news/{y}/{m}/{d}/{news_id}/{slug}.html"
        except ValueError:
            link = f"https://www.bps.go.id/id/news/{news_id}"

        articles.append({
            "title":    title,
            "date":     date_str,       # ISO format (YYYY-MM-DD) from API
            "kategori": item.get("newscat_name", ""),
            "news_id":  news_id,
            "link":     link,
        })

    return articles, pagination_meta


# Orchestration

def scrape_bps_news(api_key: str, query: str | None = None,
                    filter_date: str | None = None,
                    max_pages: int | None = None) -> list[dict]:
    """
    Fetch BPS news articles from the public API with optional keyword and date filtering, then enrich each match with full article content.
    """
    # Normalise filter_date to a datetime object for comparison
    filter_dt: datetime | None = None
    if filter_date:
        iso = normalize_to_iso_date(filter_date)
        if iso:
            filter_dt = datetime.strptime(iso, "%Y-%m-%d")
        else:
            print(f"[Scrape] Could not parse filter_date='{filter_date}' — collecting all articles.")

    all_articles:  list[dict] = []
    page           = 0
    total_pages:   int | None = None
    stop_early     = False

    while True:
        print(f"[Scrape] Fetching page {page}...")
        response              = fetch_news_list(api_key, page=page, keyword=query)
        articles, meta        = parse_news_list_response(response)

        if not articles:
            print("[Scrape] No articles returned — stopping.")
            break

        # Resolve total page count from the first response
        if meta and total_pages is None:
            total_pages = meta.get("pages", 1)
            if max_pages:
                total_pages = min(total_pages, max_pages)
            print(f"[Scrape] Total pages to fetch: {total_pages}")

        # Apply date filter: collect only articles matching filter_date,
        # stop once an older article is encountered (newest-first ordering)
        if filter_dt:
            for article in articles:
                try:
                    article_dt = datetime.strptime(article["date"], "%Y-%m-%d")
                    if article_dt < filter_dt:
                        stop_early = True
                        break
                    if article_dt.date() == filter_dt.date():
                        all_articles.append(article)
                except ValueError:
                    pass  # Skip articles with unparseable dates

            if stop_early:
                print(f"[Scrape] Found article older than {filter_date} — stopping.")
                break
        else:
            all_articles.extend(articles)

        # Stop if page limit or total pages reached
        if max_pages and page + 1 >= max_pages:
            break
        if total_pages and page + 1 >= total_pages:
            break

        page += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    if not all_articles:
        return []

    # --- Fetch full article content for each matched article ---
    print(f"\n[Scrape] Fetching full content for {len(all_articles)} article(s)...")
    for i, article in enumerate(all_articles, start=1):
        print(f"[Scrape] ({i}/{len(all_articles)}) {article['title'][:60]}...")
        content          = fetch_article_detail(api_key, article["news_id"])
        article["konten"] = content if content else ""

    return all_articles


# Public Entry Point

def main_bps(
    api_key: str,
    query: str | None = None,
    filter_tanggal: str | None = None,
    max_pages: int | None = None,
    output_filename: str = "hasil_scraping_bps",
) -> pd.DataFrame | None:
    """
    Run the BPS scraping workflow with optional filters, return a structured DataFrame, and save results to an Excel file.
    """
    # Normalise filter_tanggal to ISO format for consistent downstream handling
    if filter_tanggal:
        iso = normalize_to_iso_date(filter_tanggal)
        if iso:
            filter_tanggal = iso
        else:
            print(f"[Main] Warning: could not normalise filter_tanggal='{filter_tanggal}'.")

    articles = scrape_bps_news(
        api_key=api_key,
        query=query,
        filter_date=filter_tanggal,
        max_pages=max_pages,
    )

    if not articles:
        print("[Main] No articles found — nothing to save.")
        return None

    df = pd.DataFrame(articles)

    # Parse date column to a proper date type for clean Excel output
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce").dt.date

    # Keep only the columns relevant for the output file
    df = df[["title", "date", "kategori", "konten", "link"]]

    # --- Save to Excel ---
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    if not output_filename.endswith(".xlsx"):
        output_filename += ".xlsx"

    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    df.to_excel(output_path, index=False, engine="openpyxl")
    print(f"[Main] Saved {len(df)} article(s) to '{output_path}'")

    return df


# Script Entry Point

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    API_KEY = os.getenv("BPS_API_KEY")

    result = main_bps(
        api_key=API_KEY,
        query="ekonomi",
        filter_tanggal="2025-11-17",
        output_filename="hasil_scraping_bps",
    )
    print(result["kategori"].unique().tolist())
    # if result is not None:
    #     print(f"\n[Output] Total articles : {len(result)}")
    #     print(f"[Output] Columns        : {', '.join(result.columns)}")