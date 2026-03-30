import os
import re
import sys
import time
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Allow importing from the sibling 'helpers' directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from helpers.scraping_helper import setup_driver
from helpers.scraping_utils import parse_indonesian_date



# Constants

BI_NEWS_URL = "https://www.bi.go.id/id/publikasi/ruang-media/news-release/Default.aspx"

# CSS selectors used across multiple functions
SELECTOR_NEWS_LIST     = ".media-list"
SELECTOR_NEWS_ITEM     = ".media.media--pers"
SELECTOR_NEWS_TITLE    = ".media__title"
SELECTOR_NEWS_SUBTITLE = ".media__subtitle"
SELECTOR_CONTENT_DIV   = "div#ctl00_PlaceHolderMain_ctl05__ControlWrapper_RichHtmlField"
SELECTOR_CONTENT_FIELD = ".ms-rtestate-field"
SELECTOR_SEARCH_BOX    = "TextBoxSearch"
SELECTOR_FILTER_BTN    = "button.btn-outline-primary.btn--filter"
SELECTOR_SUBMIT_BTN    = (
    "ctl00_ctl54_g_895e8ef2_eaad_4a83_9db7_1632dd8595c0_ctl00_ButtonFilter"
)
SELECTOR_NEXT_PAGE     = "input.next[type='image']"

# Minimum character count for a paragraph to be included in the article body
MIN_PARAGRAPH_LENGTH = 30

# Paragraphs below this threshold are discarded without logging
MIN_PARAGRAPH_THRESHOLD = 5


# Search / Navigation

def submit_search(driver, keyword: str) -> None:
    """
    Submit a keyword search on the BI news page and wait for results.
    """
    search_box = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, SELECTOR_SEARCH_BOX))
    )
    search_box.clear()
    search_box.send_keys(keyword)
    print(f"[Search] Keyword '{keyword}' entered.")

    # Some page layouts require opening the filter panel before submitting
    try:
        filter_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, SELECTOR_FILTER_BTN))
        )
        filter_btn.click()
        time.sleep(2)
    except Exception:
        pass  # Filter panel not present on this layout — skip silently

    # Submit via the dedicated button, or fall back to the Enter key
    try:
        submit_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, SELECTOR_SUBMIT_BTN))
        )
        submit_btn.click()
    except Exception:
        search_box.send_keys(Keys.RETURN)

    print("[Search] Waiting for results to load (up to 60 s)...")
    time.sleep(60)
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, SELECTOR_NEWS_ITEM))
    )
    time.sleep(3)
    print("[Search] Results loaded successfully.")


def navigate_to_next_page(driver) -> bool:
    """
    Navigate to the next pagination page if available.
    """
    try:
        next_btn = driver.find_element(By.CSS_SELECTOR, SELECTOR_NEXT_PAGE)

        if next_btn.get_attribute("disabled"):
            print("[Pagination] Last page reached.")
            return False

        driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
        time.sleep(1)
        next_btn.click()
        print("[Pagination] Moving to next page...")
        time.sleep(3)
        return True

    except Exception:
        return False


# Page Scraping

def scrape_news_list_page(driver, target_date: str) -> tuple[list[dict], bool]:
    """
    Return articles matching the target date and whether scraping should stop.    
    """
    matched_articles: list[dict] = []
    should_stop = False

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SELECTOR_NEWS_LIST))
        )
    except TimeoutException:
        print("[Scrape] Timeout waiting for news list.")
        return matched_articles, should_stop

    news_items = driver.find_elements(By.CSS_SELECTOR, SELECTOR_NEWS_ITEM)
    print(f"[Scrape] Found {len(news_items)} articles on this page.")

    target_dt = datetime.strptime(target_date, "%Y-%m-%d")

    for idx, item in enumerate(news_items, start=1):
        try:
            # --- Title & URL ---
            title_el = item.find_element(By.CSS_SELECTOR, SELECTOR_NEWS_TITLE)
            title    = title_el.text.strip()
            url      = title_el.get_attribute("href")

            # --- Publication date ---
            # Subtitle format: "<date> • <category>"
            # The separator can be various unicode characters (•, ·, |, etc.),
            # so we use a regex split to isolate the date portion, with a full-
            # subtitle fallback in case no separator is present.
            subtitle = item.find_element(By.CSS_SELECTOR, SELECTOR_NEWS_SUBTITLE).text.strip()
            raw_date = re.split(r"[•·|]", subtitle)[0].strip() if re.search(r"[•·|]", subtitle) else subtitle
            iso_date = parse_indonesian_date(raw_date) or parse_indonesian_date(subtitle)

            if not iso_date:
                print(f"[Scrape] #{idx}: Could not parse date '{raw_date}' — skipped.")
                continue

            article_dt = datetime.strptime(iso_date, "%Y-%m-%d")

            # Results are newest-first; stop once we pass the target date
            if article_dt < target_dt:
                print(f"[Scrape] #{idx}: Article dated {iso_date} is older than target — stopping.")
                should_stop = True
                break

            if iso_date == target_date:
                print(f"[Scrape] #{idx}: MATCH — {title[:60]}... ({iso_date})")
                matched_articles.append({
                    "title":   title,
                    "date":    iso_date,
                    "url":     url,
                    "content": None,  # Full content is fetched in a later pass
                })
            else:
                print(f"[Scrape] #{idx}: Skip — {title[:60]}... ({iso_date})")

        except Exception as exc:
            print(f"[Scrape] #{idx}: Unexpected error — {exc}")
            continue

    return matched_articles, should_stop


def fetch_article_content(driver, url: str) -> str:
    """
    Fetch and return the main article text from the given URL.
    """
    print(f"\n[Content] Fetching: {url}")
    try:
        driver.get(url)
        time.sleep(5)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SELECTOR_CONTENT_FIELD))
        )

        soup        = BeautifulSoup(driver.page_source, "html.parser")
        content_div = soup.select_one(SELECTOR_CONTENT_DIV)

        if not content_div:
            print("[Content] Content <div> not found.")
            return "N/A"

        paragraphs   = content_div.find_all("p")
        valid_chunks: list[str] = []

        print(f"[Content] {len(paragraphs)} <p> tags found.")

        for idx, p in enumerate(paragraphs, start=1):
            text = p.get_text(strip=True)

            # Discard empty or near-empty tags
            if not text or len(text) < MIN_PARAGRAPH_THRESHOLD:
                continue

            # Discard the standard footer line appended to every article
            if "Jakarta," in text and "Departemen Komunikasi" in text:
                print(f"[Content] #{idx}: Skipped (footer).")
                continue

            # Discard the document reference number line
            if text.startswith("No. ") and "DKom" in text:
                print(f"[Content] #{idx}: Skipped (reference number).")
                continue

            if len(text) >= MIN_PARAGRAPH_LENGTH:
                valid_chunks.append(text)
                print(f"[Content] #{idx}: Added ({len(text)} chars).")
            else:
                print(f"[Content] #{idx}: Skipped (too short: {len(text)} chars).")

        if not valid_chunks:
            print("[Content] No usable content found.")
            return "N/A"

        result = "\n\n".join(valid_chunks).strip()
        print(f"[Content] Total: {len(result)} characters collected.")
        return result

    except Exception as exc:
        print(f"[Content] Error: {exc}")
        import traceback
        traceback.print_exc()
        return "N/A"


# Orchestration

def scrape_bi_news(url: str, keyword: str, target_date: str, headless: bool = True) -> list[dict]:
    """
    Scrape BI news articles matching the target date and fetch their content.
    """
    all_articles: list[dict] = []
    driver = None

    try:
        driver = setup_driver(headless=headless)

        print(f"\n{'='*80}")
        print(f"[Main] URL      : {url}")
        print(f"[Main] Keyword  : '{keyword}'")
        print(f"[Main] Target   : {target_date}")
        print(f"{'='*80}")

        driver.get(url)
        time.sleep(3)

        if keyword:
            submit_search(driver, keyword)

        # --- Paginated list scraping ---
        page_num = 1
        while True:
            print(f"\n[Main] === Page {page_num} ===")
            articles, should_stop = scrape_news_list_page(driver, target_date)
            all_articles.extend(articles)

            print(f"[Main] Matched this page : {len(articles)}")
            print(f"[Main] Cumulative total  : {len(all_articles)}")

            if should_stop:
                print(f"\n[Main] Stopping — found article older than {target_date}.")
                break

            if not navigate_to_next_page(driver):
                break

            page_num += 1

        print(f"\n{'='*80}")
        print(f"[Main] List scraping complete. {len(all_articles)} article(s) found on {target_date}.")

        # --- Full-content fetch for each matched article ---
        if all_articles:
            print(f"\n[Main] Fetching full content for {len(all_articles)} article(s)...")
            print(f"{'='*80}")

            for i, article in enumerate(all_articles, start=1):
                print(f"\n[Main] ({i}/{len(all_articles)}) {article['title'][:60]}...")
                article["content"] = fetch_article_content(driver, article["url"])
                time.sleep(2)  # Polite delay between requests

        print(f"\n{'='*80}")
        print(f"[Main] Done. {len(all_articles)} article(s) with full content.")

    except Exception as exc:
        print(f"\n[Main] Fatal error: {exc}")

    finally:
        if driver:
            driver.quit()
            print("[Main] Browser closed.")

    return all_articles


# Public Entry Point

def main_bank_indonesia(keyword: str, target_date: str) -> pd.DataFrame | None:
    """
    Return BI news articles for the given keyword and date as a DataFrame.
    """
    articles = scrape_bi_news(
        url=BI_NEWS_URL,
        keyword=keyword,
        target_date=target_date,
        headless=True,
    )

    if not articles:
        print(f"\n[Result] No articles found for keyword='{keyword}' on {target_date}.")
        return None

    df = pd.DataFrame(articles)
    print(f"\n[Result] {len(df)} article(s) found.")
    print("\n[Result] Preview:")
    print(df[["title", "date", "url"]].head())
    return df


# Script Entry Point

if __name__ == "__main__":
    result = main_bank_indonesia(
        keyword="BI Rate",
        target_date="2025-08-29",
    )

    if result is not None:
        # Output filename kept in Indonesian as per project convention
        output_path = "bank_indonesia_results.xlsx"
        result.to_excel(output_path, index=False, engine="openpyxl")
        print(f"\n[Output] Saved to '{output_path}'")
        print(f"[Output] Total articles : {len(result)}")
        print(f"[Output] Columns        : {', '.join(result.columns)}")