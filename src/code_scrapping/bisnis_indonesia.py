import os
import re
import sys
import time
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Allow importing shared utilities from the sibling 'helpers' directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from helpers.scraping_utils import normalize_to_iso_date, parse_month_name_date, rename_to_standard_columns


# Constants

BISNIS_SEARCH_URL = "https://search.bisnis.com/"

# HTTP headers sent with every request to avoid bot-detection blocks
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    )
}

# Delay in seconds between paginated requests (rate-limit courtesy)
REQUEST_DELAY_SECONDS = 1.5

# HTTP request timeout in seconds
REQUEST_TIMEOUT = 10

# CSS classes for elements to strip from article body before extracting text
BISNIS_UNWANTED_CLASSES = ["billboard", "baca-juga-box", "baca-juga-inline"]


# Content Utilities (Bisnis-specific)

def clean_article_text(text: str) -> str:
    """
    Clean Bisnis.com article text by removing boilerplate and extra blank lines.
    """
    if not text or text == "N/A":
        return text

    # Remove "Baca Juga ..." blocks (case-insensitive, including everything after)
    text = re.sub(r"Baca Juga.*", "", text, flags=re.IGNORECASE | re.DOTALL)

    # Collapse 3+ consecutive blank lines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# Pagination

def get_total_pages(soup: BeautifulSoup) -> int:
    """
    Return the total pagination pages from a Bisnis.com results page.
    """
    pagination = soup.find("ol", class_="pagingList")
    if not pagination:
        print("[Pagination] <ol class='pagingList'> not found — assuming 1 page.")
        return 1

    page_links = pagination.find_all("a", href=True)
    if not page_links:
        print("[Pagination] Pagination element found but contains no links — assuming 1 page.")
        return 1

    page_numbers = [
        int(a.get_text(strip=True))
        for a in page_links
        if a.get_text(strip=True).isdigit()
    ]

    return max(page_numbers) if page_numbers else 1


# Page Fetching

def fetch_search_results_page(keyword: str, page: int) -> tuple[list, BeautifulSoup | None]:
    """
    Return article cards and page soup from a Bisnis.com search results page.
    """
    params: dict = {"q": keyword}
    if page > 1:
        params["page"] = page

    try:
        response = requests.get(
            BISNIS_SEARCH_URL, params=params,
            headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        return soup.find_all("div", class_="artItem"), soup

    except Exception as exc:
        print(f"[Fetch] Failed to fetch page {page}: {exc}")
        return [], None


def fetch_article_content(url: str) -> str:
    """
    Fetch a Bisnis.com article and return its cleaned body text.
    """
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Locate the article body container
        container = soup.find("article", class_="detailsContent")
        if not container:
            print(f"[Content] 'detailsContent' not found, trying 'col--main': {url}")
            container = soup.find("div", class_="col--main")
        if not container:
            print(f"[Content] No content container found: {url}")
            return "N/A"

        # Remove non-content elements before extracting text.
        # Collect first, then decompose to avoid stale-reference errors.
        for css_class in BISNIS_UNWANTED_CLASSES:
            elements_to_remove = container.find_all(class_=css_class)
            for el in elements_to_remove:
                el.decompose()

        # Extract text from paragraph and list-item elements
        text_lines = [
            el.get_text(strip=True)
            for el in container.find_all(["p", "li"])
            if el.get_text(strip=True)
        ]

        if not text_lines:
            return "N/A"

        return clean_article_text("\n\n".join(text_lines))

    except Exception as exc:
        print(f"[Content] Failed to fetch content from {url}: {exc}")
        return "N/A"


# Article Card Parsing

def parse_article_card(item, target_date: str, target_dt: datetime) -> tuple[dict | None, bool]:
    """
    Parse one article card and return a match result plus a stop flag.
    """
    try:
        title_tag = item.find("h4", class_="artTitle")
        if not title_tag:
            return None, False

        title    = title_tag.get_text(strip=True)
        link     = item.find("a", class_="artLink")["href"]
        raw_date = item.find("div", class_="artDate").get_text(strip=True)
        iso_date = parse_month_name_date(raw_date)

        if not iso_date:
            return None, False

        article_dt = datetime.strptime(iso_date, "%Y-%m-%d")

        if article_dt < target_dt:
            # Article is older than target — signal caller to stop pagination
            return None, True

        if iso_date == target_date:
            return {"judul": title, "link": link, "tanggal": iso_date}, False

        # Article is newer than target — skip silently
        return None, False

    except Exception as exc:
        print(f"[Parse] Error parsing article card: {exc}")
        return None, False


# Orchestration

def scrape_bisnis_news(keyword: str, target_date: str) -> list[dict]:
    """
    Scrape Bisnis.com articles for the given keyword and publication date.
    """
    matched_articles: list[dict] = []
    target_dt = datetime.strptime(target_date, "%Y-%m-%d")

    # --- Fetch page 1 and read total page count ---
    print(f"[Scrape] Fetching page 1 to check pagination...")
    page_items, first_page_soup = fetch_search_results_page(keyword, page=1)

    if not first_page_soup:
        print("[Scrape] Failed to load page 1 — aborting.")
        return []

    total_pages = get_total_pages(first_page_soup)
    print(f"[Scrape] Total pages: {total_pages}")

    # --- Process page 1 ---
    stop_early = False
    for item in page_items:
        article, stop_early = parse_article_card(item, target_date, target_dt)
        if article:
            matched_articles.append(article)
        if stop_early:
            print(f"[Scrape] Article older than {target_date} found on page 1 — stopping.")
            break

    # --- Paginate through remaining pages ---
    if not stop_early:
        for page_num in range(2, total_pages + 1):
            print(f"[Scrape] Fetching page {page_num}/{total_pages}...")
            page_items, _ = fetch_search_results_page(keyword, page=page_num)

            if not page_items:
                print(f"[Scrape] Page {page_num} returned no items — stopping.")
                break

            for item in page_items:
                article, stop_early = parse_article_card(item, target_date, target_dt)
                if article:
                    matched_articles.append(article)
                if stop_early:
                    print(f"[Scrape] Article older than {target_date} found on page {page_num} — stopping.")
                    break

            if stop_early:
                break

            time.sleep(REQUEST_DELAY_SECONDS)

    print(f"\n[Scrape] List scraping complete. {len(matched_articles)} article(s) matched on {target_date}.")

    # --- Fetch full article content for each matched article ---
    if matched_articles:
        print(f"[Scrape] Fetching full content for {len(matched_articles)} article(s)...")
        for i, article in enumerate(matched_articles, start=1):
            print(f"[Scrape] ({i}/{len(matched_articles)}) {article['judul'][:50]}...")
            article["konten"] = fetch_article_content(article["link"])
            time.sleep(REQUEST_DELAY_SECONDS)

    return matched_articles


# Public Entry Point

def main_bisnis_indonesia(
    keyword: str = "Purbaya",
    tanggal: str = "2025-11-12",
) -> pd.DataFrame | None:
    """
    Run Bisnis.com scraping and return results as a DataFrame.
    """
    # Normalise any supported date format to ISO before passing downstream
    iso_date = normalize_to_iso_date(tanggal)
    if not iso_date:
        print(f"[Main] Warning: could not normalise tanggal='{tanggal}' — using as-is.")
        iso_date = tanggal

    print(f"[Main] Keyword : '{keyword}'")
    print(f"[Main] Target  : {iso_date}")

    articles = scrape_bisnis_news(keyword, iso_date)

    if not articles:
        print(f"[Main] No articles found for keyword='{keyword}' on {iso_date}.")
        return None

    df = pd.DataFrame(articles)

    if df.empty:
        print("[Main] DataFrame is empty after construction.")
        return None

    # Rename internal keys to project-standard column names
    df = rename_to_standard_columns(df)

    print(f"[Main] Successfully scraped {len(df)} article(s).")
    return df


# Script Entry Point

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()  # Load .env only when run directly, not when imported

    result = main_bisnis_indonesia(
        keyword="Purbaya",
        tanggal="2025-11-12",
    )

    if result is not None:
        print(result)

        # Output filename kept in Indonesian as per project convention
        result.to_excel("bisnis_indonesia_results.xlsx", index=False, engine="openpyxl")
        print(f"\n[Output] Saved to 'bisnis_indonesia_results.xlsx'")
        print(f"[Output] Total articles : {len(result)}")
        print(f"[Output] Columns        : {', '.join(result.columns)}")