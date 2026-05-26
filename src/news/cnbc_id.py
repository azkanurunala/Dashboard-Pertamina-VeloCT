import os
import re
import sys
import time
import traceback
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Allow importing shared utilities from the sibling 'helpers' directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from helpers.scraping_helper import setup_driver
from helpers.scraping_utils import (
    find_best_container,
    find_content_container,
    find_pagination_container,
    get_total_pages_from_pagination,
    normalize_to_iso_date,
    resolve_relative_date,
)


# Constants

CNBC_BASE_URL = "https://www.cnbcindonesia.com"
CNBC_SEARCH_URL = f"{CNBC_BASE_URL}/search"

# Delay in seconds between page requests (rate-limit courtesy)
REQUEST_DELAY_SECONDS = 1

# Delay after page load before reading the DOM (allows JS to render)
PAGE_RENDER_WAIT_SECONDS = 2

# Minimum paragraph character count to be included in article content
MIN_CONTENT_LENGTH = 15

# CNBC-specific location prefixes stripped from the start of article body text
CNBC_CONTENT_PREFIXES = [
    "Jakarta, CNBC Indonesia - ",
    "Jakarta, CNBC Indonesia-",
    "Jakarta, CNBC Indonesia –",
    "Jakarta, CNBC Indonesia– ",
]

# CSS classes on <div> elements that indicate ad or navigation blocks to remove
CNBC_UNWANTED_DIV_CLASSES = ["ads", "related", "sisip", "baca", "lihatjg", "linksisip"]

# CSS classes on <table> elements that indicate non-content blocks to remove
CNBC_UNWANTED_TABLE_CLASSES = ["linksisip", "pic_artikel"]

# Indonesian month names mapped to their abbreviated English equivalents,
# used to convert Indonesian absolute dates to a strptime-parseable format
INDONESIAN_TO_EN_MONTH = {
    "januari": "Jan", "februari": "Feb", "maret":    "Mar", "april": "Apr",
    "mei":     "May", "juni":     "Jun", "juli":     "Jul", "agustus": "Aug",
    "september": "Sep", "oktober": "Oct", "november": "Nov", "desember": "Dec",
}

CNBC_ALLOWED_CATEGORIES: list[str] = [
    "market",
    "news",
    "research",
    "opinion",
]

# Date Utilities (CNBC-specific)

def parse_cnbc_date(raw_date: str) -> str:
    """
    Parse a CNBC Indonesia date string into "DD Mon YYYY" format, handling relative times and Indonesian month names with fallbacks.
    """
    if not raw_date:
        return raw_date

    raw_date_lower = raw_date.strip().lower()

    # --- Relative date (e.g. "3 hari lalu", "2 jam yang lalu") ---
    iso = resolve_relative_date(raw_date_lower)
    if iso:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d %b %Y")

    # --- Indonesian absolute date (e.g. "29 Agustus 2025") ---
    for id_month, en_month in INDONESIAN_TO_EN_MONTH.items():
        if id_month in raw_date_lower:
            raw_date_lower = raw_date_lower.replace(id_month, en_month)
            break

    # Extract "DD Mon YYYY" pattern and return
    m = re.match(r"(\d{1,2}\s+\w+\s+\d{4})", raw_date_lower)
    if m:
        return m.group(1).strip()

    return raw_date  # Fallback: return original string unchanged


# Content Cleaning

def strip_cnbc_prefix(text: str) -> str:
    """
    Remove CNBC Indonesia location prefixes and discard parenthetical-only paragraphs from extracted text.
    """
    for prefix in CNBC_CONTENT_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break

    # Discard paragraphs that are purely parenthetical (e.g. source notes)
    if text.startswith("(") and text.endswith(")"):
        return ""

    return text.strip()


def remove_unwanted_elements(content_div: BeautifulSoup) -> None:
    """
    Remove scripts, styles, iframes, and class-matched non-content div/table elements from an article body in-place.
    """
    # Remove script/style/iframe noise
    for tag in content_div.find_all(["script", "style", "iframe"]):
        tag.decompose()

    # Collect unwanted divs first, then decompose.
    # Decomposing inside the find_all() iterator leaves stale None references
    # in the tree, causing AttributeError on subsequent iterations.
    divs_to_remove = [
        div for div in content_div.find_all("div")
        if div is not None and any(
            cls in " ".join(div.get("class") or [])
            for cls in CNBC_UNWANTED_DIV_CLASSES
        )
    ]
    for div in divs_to_remove:
        div.decompose()

    # Same two-pass approach for tables
    tables_to_remove = [
        table for table in content_div.find_all("table")
        if table is not None and any(
            cls in " ".join(table.get("class") or [])
            for cls in CNBC_UNWANTED_TABLE_CLASSES
        )
    ]
    for table in tables_to_remove:
        table.decompose()


# Page Parsing

def parse_article_card(section) -> dict | None:
    """
    Extract title, date, and link from a CNBC article card element using resilient selectors, or return None if no link is found.
    """
    try:
        # Prefer the primary group link; fall back to any anchor
        link_tag = section.find("a", class_="group", href=True) or section.find("a", href=True)
        if not link_tag:
            return None

        # Ensure URL is absolute
        link = link_tag.get("href", "")
        if link.startswith("/"):
            link = CNBC_BASE_URL + link

        # Filter berdasarkan kategori dari URL
        # Format: cnbcindonesia.com/{kategori}/{id}/{slug}
        try:
            category = link.split("cnbcindonesia.com/")[1].split("/")[0]
            if category not in CNBC_ALLOWED_CATEGORIES:
                return None
        except (IndexError, AttributeError):
            pass

        # Title: prefer <strong>, then heading tags, then the link itself
        title_tag = (
            link_tag.find("strong")
            or link_tag.find("h2")
            or link_tag.find("h3")
            or link_tag
        )
        title = title_tag.get_text(strip=True)

        # Publication date: prefer the known date span class, then <time>
        date_tag = (
            link_tag.find("span", class_="text-xs text-gray")
            or link_tag.find("span", class_=lambda x: x and "text-xs" in " ".join(x))
            or link_tag.find("time")
        )
        raw_date = date_tag.get_text(strip=True) if date_tag else ""
        pub_date = parse_cnbc_date(raw_date) if raw_date else ""

        return {"title": title, "date": pub_date, "link": link}

    except Exception:
        return None


def parse_search_results_page(driver, url: str) -> tuple[list[dict], BeautifulSoup | None]:
    """
    Load a CNBC search results page with Selenium, extract parsed article cards, and return both the results and page soup for pagination handling.
    """
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "section"))
        )
        time.sleep(PAGE_RENDER_WAIT_SECONDS)
    except Exception as exc:
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("[Parse] Warning: <section> not found, falling back to <body>.")
        except Exception as exc:
            print(f"[Parse] Timeout loading page: {exc}")
            return [], None
    time.sleep(PAGE_RENDER_WAIT_SECONDS)

    soup      = BeautifulSoup(driver.page_source, "html.parser")
    container = find_best_container(soup)

    if container:
        sections = container.find_all("section") or container.find_all("article")
    else:
        sections = soup.find_all("section")

    results: list[dict] = []
    for idx, section in enumerate(sections, start=1):
        article = parse_article_card(section)
        if article:
            print(f"  [{idx}] {article['title'][:60]}...")
            results.append(article)
        else:
            print(f"  [{idx}] Could not parse card.")

    print(f"[Parse] Extracted {len(results)} article(s) from {url}")
    return results, soup


def scrape_article_content(driver, url: str) -> str:
    """
    Load a CNBC article via Selenium, clean non-content elements, and return the extracted body text from paragraphs and lists.
    """
    try:
        driver.get(url)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "p"))
            )
        except Exception:
            print("[Content] Timeout waiting for <p> tags.")
            return ""

        time.sleep(PAGE_RENDER_WAIT_SECONDS)
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Locate content container: heuristic first, then known CSS fallbacks
        content_div = (
            find_content_container(soup)
            or soup.find("div", class_="detail-text")
            or soup.find("div", class_="detail_text")
            or soup.find("article")
        )

        if not content_div:
            print("[Content] Content container not found.")
            return ""

        remove_unwanted_elements(content_div)

        text_lines: list[str] = []

        # Collect paragraph text
        for p in content_div.find_all("p"):
            text = p.get_text(strip=True)
            if text and len(text) > MIN_CONTENT_LENGTH:
                cleaned = strip_cnbc_prefix(text)
                if cleaned:
                    text_lines.append(cleaned)

        # Collect list item text
        for ol in content_div.find_all(["ol", "ul"]):
            for li in ol.find_all("li", recursive=False):
                text = li.get_text(strip=True)
                if text and len(text) > MIN_CONTENT_LENGTH:
                    text_lines.append(text)

        result = "\n\n".join(text_lines)
        print(f"[Content] {len(result)} characters collected.")
        return result

    except Exception as exc:
        print(f"[Content] Error: {exc}")
        traceback.print_exc()
        return ""


# Orchestration

def scrape_cnbc_news(
    query: str,
    filter_date: str | None = None,
    headless: bool = True,
    max_pages: int | None = None,
) -> list[dict]:
    """
    Scrape CNBC Indonesia search results for a keyword and optional date, then fetch full content for each matched article.
    """
    # Normalise filter_date to a datetime object for date comparison
    filter_dt: datetime | None = None
    if filter_date:
        iso = normalize_to_iso_date(filter_date)
        if iso:
            filter_dt = datetime.strptime(iso, "%Y-%m-%d")
            print(f"[Main] Target date: {filter_dt.strftime('%d %b %Y')}")
        else:
            print(f"[Main] Warning: could not parse filter_date='{filter_date}' — collecting all dates.")

    driver = setup_driver(headless=headless)

    try:
        search_url = f"{CNBC_SEARCH_URL}?query={query.strip().replace(' ', '+')}"

        # --- Scrape page 1 and detect total pages ---
        print(f"\n[Main] === Page 1 ===")
        all_results, first_page_soup = parse_search_results_page(driver, search_url)

        if not first_page_soup:
            print("[Main] Failed to load page 1.")
            return []

        pagination  = find_pagination_container(first_page_soup)
        total_pages = get_total_pages_from_pagination(pagination)
        if max_pages:
            total_pages = min(total_pages, max_pages)
        print(f"[Main] Total pages to scrape: {total_pages}")

        # Apply date filter to page 1 results
        all_results, stop_early = _filter_by_date(all_results, filter_dt, page_num=1)

        # --- Paginate through remaining pages ---
        if not stop_early and total_pages > 1:
            for page_num in range(2, total_pages + 1):
                print(f"\n[Main] === Page {page_num} ===")
                page_url        = f"{search_url}&page={page_num}"
                page_results, _ = parse_search_results_page(driver, page_url)

                if not page_results:
                    print("[Main] Empty page — stopping pagination.")
                    break

                filtered, stop_early = _filter_by_date(page_results, filter_dt, page_num)
                all_results.extend(filtered)

                if stop_early:
                    break

                time.sleep(REQUEST_DELAY_SECONDS)

        print(f"\n{'=' * 70}")
        print(f"[Main] List scraping complete. {len(all_results)} article(s) found.")
        print(f"{'=' * 70}")

        if not all_results:
            return []

        # --- Fetch full article content ---
        print(f"\n[Main] Fetching full content for {len(all_results)} article(s)...")
        print(f"{'=' * 70}")
        for i, article in enumerate(all_results, start=1):
            print(f"\n[Main] ({i}/{len(all_results)}) {article['title'][:65]}...")
            article["content"] = scrape_article_content(driver, article["link"])
            time.sleep(0.5)

        print(f"\n[Main] Done.")
        return all_results

    except Exception as exc:
        traceback.print_exc()
        return []

    finally:
        driver.quit()
        print("[Main] Browser closed.")


def _filter_by_date(
    articles: list[dict],
    filter_dt: datetime | None,
    page_num: int,
) -> tuple[list[dict], bool]:
    """
    Filter articles by target date, returning matches and a stop flag if older articles are encountered.
    """
    if not filter_dt:
        return articles, False

    matched: list[dict] = []
    stop_early = False

    for article in articles:
        try:
            article_dt = datetime.strptime(article["date"], "%d %b %Y")
        except ValueError:
            print(f"[Filter] Could not parse date '{article['date']}' — skipped.")
            continue

        if article_dt < filter_dt:
            print(f"[Filter] Page {page_num}: article dated {article['date']} is older than target — stopping.")
            stop_early = True
            break
        elif article_dt.date() == filter_dt.date():
            print(f"[Filter] Page {page_num}: MATCH — {article['date']}")
            matched.append(article)
        else:
            print(f"[Filter] Page {page_num}: Skip — {article['date']} (newer than target)")

    print(f"[Filter] Page {page_num}: {len(matched)} article(s) matched.")
    return matched, stop_early


# Public Entry Point

def main_cnbc(
    keyword: str,
    tanggal: str | None = None,
    headless: bool = True,
    max_pages: int | None = None,
) -> pd.DataFrame | None:
    """
    Run the CNBC scraping workflow with normalized date handling and return a structured DataFrame or None if no results are found.
    """
    iso_date = None
    if tanggal is not None:
        iso_date = normalize_to_iso_date(tanggal)
        if not iso_date:
            try:
                iso_date = datetime.strptime(tanggal, "%d-%m-%Y").strftime("%Y-%m-%d")
            except ValueError:
                pass

    results = scrape_cnbc_news(
        query=keyword,
        filter_date=iso_date or tanggal,
        headless=headless,
        max_pages=max_pages,
    )

    if not results:
        print("\n[Main] No articles found.")
        return None

    df = pd.DataFrame(results)
    df["date"] = pd.to_datetime(df["date"], format="%d %b %Y", errors="coerce").dt.date
    df = df.rename(columns={"link": "url"})

    print(f"\n[Main] Shape    : {df.shape}")
    print(f"[Main] Columns  : {list(df.columns)}")
    print(f"\n[Main] Preview  :")
    print(df[["title", "date"]].head(10))

    return df


# Script Entry Point

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()  # Load .env only when run directly, not when imported

    df = main_cnbc(
        keyword="ihsg",
        tanggal=None,
    )
    print(df["url"].head(20).tolist())

    # if df is not None and not df.empty:
    #     print(f"\n[Output] Total articles : {len(df)}")
    #     if "content" in df.columns:
    #         print(f"\n[Output] Sample content :")
    #         print(df.iloc[0]["content"][:300] + "...")

    #     # Output filename kept in Indonesian as per project convention
    #     df.to_excel("cnbc_id.xlsx", index=False, engine="openpyxl")
    #     print("\n[Output] Saved to 'cnbc_id.xlsx'")