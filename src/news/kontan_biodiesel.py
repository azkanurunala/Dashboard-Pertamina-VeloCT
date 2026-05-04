import os
import sys
import time
from datetime import datetime

import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from helpers.scraping_utils import normalize_to_iso_date, rename_to_standard_columns

# Reuse all shared internals from the BBM scraper
from news.kontan_bbm import (
    CONTENT_FETCH_DELAY,
    _fetch_article_content,
    _find_articles_by_keyword,
)


# Section Override

# The only difference vs kontan_bbm_scraper: "investasi" instead of
# "internasional". Passed explicitly to _find_articles_by_keyword so that
# no module-level state needs to be mutated.
BIODIESEL_SITEMAP_SECTIONS = ["investasi", "industri"]


# Orchestration

def scrape_kontan_biodiesel(keyword: str, date: str | datetime | None = None) -> list[dict]:
    """
    Scrape Kontan investasi/industri articles by keyword with optional date filtering and enrich results with full content.
    """
    articles = _find_articles_by_keyword(keyword, sections=BIODIESEL_SITEMAP_SECTIONS)

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

def main_kontan_biodiesel(
    keyword: str = "BBM",
    tanggal: str | None = None,
) -> pd.DataFrame | None:
    """
    Scrape Kontan investasi/industri articles with keyword and normalized date filtering, returning a standardized DataFrame.
    """
    if tanggal is not None:
        iso_date = normalize_to_iso_date(tanggal)
        if not iso_date:
            print(f"[Main] Warning: could not normalise tanggal='{tanggal}' — using as-is.")
            iso_date = tanggal
        tanggal = iso_date

    print(f"[Main] Keyword : '{keyword}'")
    print(f"[Main] Target  : {tanggal or '(no date filter)'}\n")

    data = scrape_kontan_biodiesel(keyword, date=tanggal)

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

    result = main_kontan_biodiesel(keyword="BBM", tanggal=None)

    if result is not None:
        print(result)
        result.to_excel("kontan_biodiesel_results.xlsx", index=False, engine="openpyxl")
        print(f"\n[Output] Saved to 'kontan_biodiesel_results.xlsx'")
        print(f"[Output] Total articles : {len(result)}")
        print(f"[Output] Columns        : {', '.join(result.columns)}")