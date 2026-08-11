import os
import sys
import time
import traceback
from datetime import datetime
from urllib.parse import quote

import pandas as pd
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException, WebDriverException

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from helpers.scraping_helper import setup_driver
from helpers.scraping_utils import normalize_to_iso_date


# Constants

SCMP_SEARCH_BASE = "https://www.scmp.com/search"

# Seconds to wait after each scroll for new content to render
SCROLL_RENDER_DELAY = 10

# Seconds to wait for initial page load before scrolling
PAGE_LOAD_DELAY = 10

# Maximum number of scroll iterations before stopping
MAX_SCROLLS = 50

SCMP_ALLOWED_SECTIONS: set[str] = {
    "economy",
    "news",
    "business",
    "comment",
    "week-asia",
    "explained",
    "topics",
}


# Shared Driver (reused across keywords within a run)
#
# A fresh Chrome instance was launched and quit on every single keyword call.
# The driver is now created once and reused; only torn down on a
# WebDriverException (session actually dead) so a crash doesn't cascade into
# every remaining keyword, or explicitly via close_driver() at end of run.

_driver_instance = None


def _get_driver():
    global _driver_instance
    if _driver_instance is None:
        _driver_instance = setup_driver()
    return _driver_instance


def close_driver() -> None:
    """Quit the shared driver, if one was created. Call once at end of run."""
    global _driver_instance
    if _driver_instance is not None:
        try:
            _driver_instance.quit()
        except Exception:
            pass
        _driver_instance = None


# Scroll Helpers

def _get_oldest_article_date(page_source: str) -> datetime | None:
    """
    Extract the oldest visible article datetime from an SCMP search page by parsing <time> elements, or return None if unavailable.
    """
    soup  = BeautifulSoup(page_source, "html.parser")
    dates: list[datetime] = []

    for time_tag in soup.find_all("time"):
        raw = time_tag.get("datetime")
        if not raw:
            continue
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            dates.append(dt.replace(tzinfo=None))
        except ValueError:
            pass

    return min(dates) if dates else None


def _scroll_until_date(driver, target_date: datetime) -> None:
    """
    Scroll SCMP search results until reaching the target date or no additional content loads.
    """
    print(f"[Scroll] Target stop date: {target_date.date()}")
    last_height = driver.execute_script("return document.body.scrollHeight")

    for i in range(1, MAX_SCROLLS + 1):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_RENDER_DELAY)

        oldest = _get_oldest_article_date(driver.page_source)
        if oldest:
            print(f"[Scroll {i}/{MAX_SCROLLS}] Oldest article: {oldest.date()}")
            if oldest <= target_date:
                print("[Scroll] Target date reached — stopping.")
                break
        else:
            print(f"[Scroll {i}/{MAX_SCROLLS}] No dates found yet.")

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("[Scroll] No new content loaded — stopping.")
            break
        last_height = new_height

    print(f"[Scroll] Finished after {i} scroll(s).")


# Article Extraction

def _extract_articles(page_source: str) -> list[dict]:
    """
    Extract SCMP article metadata from search results page source, including title, date, URL, and summary.
    """
    soup       = BeautifulSoup(page_source, "html.parser")
    containers = soup.find_all("div", {"data-qa": "ContentItemSearch-Container"})
    print(f"[Extract] {len(containers)} article container(s) found.")

    articles: list[dict] = []

    for idx, container in enumerate(containers, start=1):
        try:
            link_tag = container.find("a", {"data-qa": "BaseLink-renderAnchor-StyledAnchor"})
            if not link_tag or not link_tag.get("href"):
                continue
            url = f"https://www.scmp.com{link_tag['href']}"
            try:
                section = url.split("scmp.com/")[1].split("/")[0]
                if section not in SCMP_ALLOWED_SECTIONS:
                    continue
            except (IndexError, AttributeError):
                continue

            title_tag = container.find("span", {"data-qa": "ContentHeadline-Headline"})
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)

            summary_tag = container.find("h3", {"data-qa": "ContentSummary-ContainerWithTag"})
            summary     = summary_tag.get_text(strip=True) if summary_tag else ""

            time_tag = container.find("time")
            if not time_tag or not time_tag.get("datetime"):
                continue

            dt             = datetime.fromisoformat(time_tag["datetime"].replace("Z", "+00:00"))
            date_formatted = dt.strftime("%Y-%m-%d")

            print(f"  [{idx}] {title[:50]}... | {date_formatted}")
            if summary:
                print(f"         {summary[:60]}...")

            articles.append({
                "title":   title,
                "date":    date_formatted,
                "url":     url,
                "content": summary,
            })

        except Exception as exc:
            print(f"  [{idx}] Error: {exc}")
            continue

    return articles


# Orchestration

def scrape_scmp(keyword: str, tanggal: str | None = None) -> pd.DataFrame | None:
    """
    Scrape SCMP search results for a keyword, scroll until the target date is reached, and return same-day articles as a DataFrame.
    """
    # Resolve and normalise target date
    if tanggal is None:
        iso_date = datetime.now().strftime("%Y-%m-%d")
    else:
        iso_date = normalize_to_iso_date(str(tanggal))
        if not iso_date:
            print(f"[Scrape] Warning: could not normalise tanggal='{tanggal}' — using today.")
            iso_date = datetime.now().strftime("%Y-%m-%d")

    target_dt = datetime.strptime(iso_date, "%Y-%m-%d")  # tz-naive

    encoded    = quote(keyword)
    search_url = f"{SCMP_SEARCH_BASE}/{encoded}?q={encoded}"

    print("=" * 60)
    print("SCRAPING SCMP")
    print(f"Keyword : {keyword}")
    print(f"Date    : {iso_date}")
    print(f"URL     : {search_url}")
    print("=" * 60)

    driver = _get_driver()
    try:
        print("[Scrape] Loading search page...")
        driver.get(search_url)
        time.sleep(PAGE_LOAD_DELAY)

        print("\n[Scrape] Scrolling...\n")
        _scroll_until_date(driver, target_date=target_dt)

        print("\n[Scrape] Extracting articles...\n")
        articles = _extract_articles(driver.page_source)
        print(f"[Scrape] {len(articles)} total article(s) extracted.")

        if not articles:
            return None

        df = pd.DataFrame(articles)

        # Normalise date column and filter to target date
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        if df["date"].dt.tz is not None:
            df["date"] = df["date"].dt.tz_localize(None)

        df   = df[df["date"].dt.date == target_dt.date()]
        df   = df.sort_values("date", ascending=False).reset_index(drop=True)
        df["date"] = df["date"].dt.date

        print(f"[Scrape] {len(df)} article(s) after date filter ({iso_date}).")
        return df if not df.empty else None

    except TimeoutException as exc:
        # Page/element just didn't load in time -- not a dead session, keep
        # the driver alive for the next keyword.
        print(f"[Scrape] Timeout waiting for page/element: {exc}")
        return None

    except WebDriverException as exc:
        # Session actually dead (crash, disconnect) -- drop it so the next
        # call gets a fresh browser instead of repeatedly failing on it.
        print(f"[Scrape] Driver error, resetting session: {exc}")
        close_driver()
        return None

    except Exception as exc:
        print(f"[Scrape] Error: {exc}")
        traceback.print_exc()
        return None


# Public Entry Point

def main_scmp(keyword: str, tanggal: str | None = None) -> pd.DataFrame | None:
    """
    Run the SCMP scraping workflow for a keyword and date, returning a DataFrame or None if no articles are found.
    """
    df = scrape_scmp(keyword, tanggal)

    if df is None or df.empty:
        print("[Main] No articles found.")
        return None

    print("\n" + "=" * 60)
    print("HASIL SCRAPING")
    print("=" * 60)
    print(f"Total artikel: {len(df)}")
    print("\nSample data:")
    print(df.head(10).to_string())
    return df


# Script Entry Point

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    result = main_scmp(keyword="badminton", tanggal="2026-04-29")

    if result is not None:
    #     output_file = f"scmp_scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    #     result.to_excel(output_file, index=False, engine="openpyxl")
    #     print(f"\n[Output] Saved to '{output_file}'")
    #     print(f"[Output] Total articles : {len(result)}")
    #     print(f"[Output] Columns        : {', '.join(result.columns.astype(str))}")
    #     print("\nPreview:")
    #     print(result[["title", "date"]].to_string())
    # else:
    #     print("\n[Output] No articles found.")
        categories = set(
            u.split("scmp.com/")[1].split("/")[0]
            for u in result["url"].tolist()
        )
        print(categories)