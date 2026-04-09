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
from helpers.scraping_utils import normalize_to_iso_date, parse_month_name_date, resolve_relative_date


# Constants

BLOOMBERG_TECHNOZ_BASE_URL   = "https://www.bloombergtechnoz.com"
BLOOMBERG_TECHNOZ_SEARCH_URL = f"{BLOOMBERG_TECHNOZ_BASE_URL}/search"

# HTTP headers sent with every request to avoid bot-detection blocks
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    )
}

# Delay in seconds between paginated list requests (rate-limit courtesy)
REQUEST_DELAY_SECONDS = 1.0

# HTTP request timeout in seconds
REQUEST_TIMEOUT = 10

# Maximum number of sub-pages to fetch per article (safety guard)
MAX_ARTICLE_PAGES = 10

# Date format used internally throughout this scraper for display/comparison
DISPLAY_DATE_FORMAT = "%d %b %Y"


# Date Utilities (Bloomberg Technoz-specific)

def parse_bloomberg_date(raw_date: str) -> str:
    """
    Parse a Bloomberg Technoz date string into a normalized display format.
    """
    cleaned = raw_date.replace("|", "").strip().lower()

    # --- Relative date (e.g. "3 jam yang lalu", "2 hari lalu") ---
    iso = resolve_relative_date(cleaned)
    if iso:
        return datetime.strptime(iso, "%Y-%m-%d").strftime(DISPLAY_DATE_FORMAT)

    # --- Absolute date with Indonesian or English month name ---
    iso = parse_month_name_date(cleaned)
    if iso:
        return datetime.strptime(iso, "%Y-%m-%d").strftime(DISPLAY_DATE_FORMAT)

    return cleaned  # Fallback: return sanitised string unchanged


# Pagination

def get_total_pages(soup: BeautifulSoup) -> int:
    """
    Return total pages from a Bloomberg Technoz results page.
    """
    pagination = soup.find("ul", class_="pagging") if soup else None
    if not pagination:
        return 1

    page_numbers = [
        int(m.group(1))
        for a in pagination.find_all("a", href=True)
        if (m := re.search(r"pagenum=(\d+)", a["href"]))
    ]

    return max(page_numbers) if page_numbers else 1


# Article Content Fetching

def fetch_article_content(url: str) -> str:
    """
    Fetch a Bloomberg Technoz article and return its combined text.
    """
    all_text_lines: list[str] = []

    try:
        for page in range(1, MAX_ARTICLE_PAGES + 1):
            # Page 1 uses the canonical URL; subsequent pages append /N
            page_url = url if page == 1 else f"{url}/{page}"
            print(f"  [Content] Fetching sub-page {page}: {page_url}")

            response = requests.get(page_url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

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
        return "\n".join(all_text_lines)

    except Exception as exc:
        print(f"  [Content] Failed to fetch article {url}: {exc}")
        import traceback
        traceback.print_exc()
        return ""


# Search Results Page Parsing

def fetch_search_results_page(url: str) -> tuple[list[dict], BeautifulSoup | None]:
    """
    Fetch a Bloomberg Technoz search results page, extract valid article data (title, date, link), and return it along with the parsed HTML for optional pagination handling.
    """
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except Exception as exc:
        print(f"[Fetch] Failed to access {url}: {exc}")
        return [], None

    soup  = BeautifulSoup(response.text, "html.parser")
    cards = soup.find_all("div", class_="card-box")
    articles: list[dict] = []

    for card in cards:
        a_tag      = card.find("a", href=True)
        title_tag  = card.find("h2", class_="title")
        date_tag   = card.find("span", class_="cl-gray")

        title    = title_tag.get_text(strip=True) if title_tag else ""
        raw_date = date_tag.get_text(strip=True)  if date_tag  else ""
        link     = a_tag["href"]                  if a_tag     else ""

        # Ensure URL is absolute
        if link and not link.startswith("http"):
            link = BLOOMBERG_TECHNOZ_BASE_URL + link

        if not title or not link:
            continue  # Skip incomplete cards

        articles.append({
            "title": title,
            "date":  parse_bloomberg_date(raw_date),
            "link":  link,
        })

    return articles, soup


# Orchestration

def scrape_bloomberg_technoz_news(
    query: str,
    filter_date: str | None = None,
) -> list[dict]:
    """
    Scrape Bloomberg Technoz articles by query with optional date filtering, paginate results with early stopping, and enrich each article with full content.
    """
    search_url = f"{BLOOMBERG_TECHNOZ_SEARCH_URL}?query={query}&type=berita"

    # Parse filter_date into a datetime for comparison
    filter_dt: datetime | None = None
    if filter_date:
        try:
            filter_dt = datetime.strptime(filter_date, DISPLAY_DATE_FORMAT)
            print(f"[Scrape] Target date: {filter_dt.strftime(DISPLAY_DATE_FORMAT)}")
        except ValueError as exc:
            print(f"[Scrape] Warning: could not parse filter_date='{filter_date}': {exc}")

    # --- Page 1: fetch results and detect total page count ---
    print(f"[Scrape] Fetching page 1...")
    all_results, first_page_soup = fetch_search_results_page(search_url)
    total_pages = get_total_pages(first_page_soup)
    print(f"[Scrape] Total pages: {total_pages}")

    # Apply date filter to page 1 results
    all_results, stop_early = _filter_by_date(all_results, filter_dt, page_num=1)

    # --- Paginate through remaining pages ---
    if not stop_early:
        for page_num in range(2, total_pages + 1):
            print(f"\n[Scrape] Fetching page {page_num}/{total_pages}...")
            page_url     = f"{search_url}&pagenum={page_num}"
            page_results, _ = fetch_search_results_page(page_url)

            if not page_results:
                print(f"[Scrape] Page {page_num} returned no results — stopping.")
                break

            matched, stop_early = _filter_by_date(page_results, filter_dt, page_num)
            all_results.extend(matched)

            if stop_early:
                break

            time.sleep(REQUEST_DELAY_SECONDS)

    print(f"\n[Scrape] List scraping complete. {len(all_results)} article(s) passed the filter.")

    if not all_results:
        return []

    # --- Fetch full article content for each matched article ---
    print(f"\n[Scrape] Fetching full content for {len(all_results)} article(s)...")
    
    keyword_pattern = re.compile(r"\b" + re.escape(query.strip()) + r"\b", re.IGNORECASE)
    filtered_results: list[dict] = []
    
    for i, article in enumerate(all_results, start=1):
        print(f"[Scrape] [{i}/{len(all_results)}] {article['title']}")
        article["konten"] = fetch_article_content(article["link"])
        if not keyword_pattern.search(article["title"]) and not keyword_pattern.search(article["konten"]):
            print(f"[Skip] '{query.strip()}' tidak ditemukan: {article['title']!r}")
            continue
        filtered_results.append(article)
        
    print("[Scrape] Content fetching complete.")
    # return all_results
    return filtered_results


def _filter_by_date(
    articles: list[dict],
    filter_dt: datetime | None,
    page_num: int,
) -> tuple[list[dict], bool]:
    """
    Filter articles by target date, returning matches and a stop flag when older articles are encountered to halt further pagination.
    """
    if not filter_dt:
        return articles, False

    matched: list[dict] = []
    stop_early = False

    for article in articles:
        try:
            article_dt = datetime.strptime(article["date"], DISPLAY_DATE_FORMAT)
        except ValueError:
            print(f"[Filter] Could not parse date '{article['date']}' — skipped.")
            continue

        if article_dt < filter_dt:
            print(f"[Filter] Page {page_num}: article dated {article['date']} is older than target — stopping.")
            stop_early = True
            break
        elif article_dt == filter_dt:
            matched.append(article)

    return matched, stop_early


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
        query="Biodiesel",
        filter_tanggal="2025-09-20",
    )

    if result is not None:
        print(result)

        # Output filename kept in Indonesian as per project convention
        result.to_excel("bloomberg_technoz_results.xlsx", index=False, engine="openpyxl")
        print(f"\n[Output] Saved to 'bloomberg_technoz_results.xlsx'")
        print(f"[Output] Total articles : {len(result)}")
        print(f"[Output] Columns        : {', '.join(result.columns)}")