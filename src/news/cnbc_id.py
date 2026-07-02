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
CNBC_TAG_URL = f"{CNBC_BASE_URL}/tag"

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

def extract_date_from_url(url: str) -> str:
    """
    Ekstrak tanggal publikasi dari URL artikel CNBC Indonesia.

    URL CNBC selalu mengandung tanggal dalam format YYYYMMDD atau
    YYYYMMDDHHmmss di path segment, contoh:
      /market/20260430-17-740123/...       -> 2026-04-30
      /news/20260605140008-4-740421/...    -> 2026-06-05
    Ini adalah sumber tanggal paling reliable — tidak berubah dan tidak
    bergantung pada kapan scraping dijalankan (tidak seperti relative date
    "3 hari yang lalu" yang di-resolve ke waktu scraping).

    Return: "DD Mon YYYY" (e.g. "30 Apr 2026"), atau "" jika tidak ditemukan.
    """
    # Ambil 8 digit pertama dari segment path yang diawali angka
    m = re.search(r"/(\d{8})", url)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y%m%d").strftime("%d %b %Y")
        except ValueError:
            pass
    return ""


def parse_cnbc_date(raw_date: str) -> str:
    """
    Parse a CNBC Indonesia date string into "DD Mon YYYY" format.
    Digunakan sebagai fallback jika ekstraksi dari URL gagal.
    """
    if not raw_date:
        return raw_date

    raw_date_lower = raw_date.strip().lower()

    # --- Relative date (e.g. "3 hari lalu", "2 jam yang lalu") ---
    # CATATAN: relative date hanya reliable untuk scraping hari ini.
    # Untuk scraping historical, gunakan extract_date_from_url().
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
        # Utamakan tanggal dari URL — lebih reliable dari teks kartu yang
        # menampilkan relative date ("3 jam yang lalu") saat scraping historical.
        pub_date = extract_date_from_url(link)
        if not pub_date:
            # Fallback ke teks tanggal di kartu jika URL tidak mengandung tanggal
            raw_date = date_tag.get_text(strip=True) if date_tag else ""
            pub_date = parse_cnbc_date(raw_date) if raw_date else ""

        return {"title": title, "date": pub_date, "link": link}

    except Exception:
        return None


def parse_search_results_page(driver, url: str) -> tuple[list[dict], BeautifulSoup | None]:
    """
    Load a CNBC search results page with Selenium, extract parsed article cards, and return both the results and page soup for pagination handling.
    """
    # Set page load timeout lebih longgar — halaman CNBC kadang lambat load JS-nya
    driver.set_page_load_timeout(90)

    try:
        driver.get(url)
    except Exception as exc:
        # TimeoutException dari Selenium: halaman belum selesai load tapi DOM mungkin sudah ada
        print(f"[Parse] Page load timeout (lanjut baca DOM): {type(exc).__name__}")

    # Tunggu JS selesai render konten artikel.
    # Konten CNBC di-inject oleh JS setelah page load — perlu tunggu
    # document.readyState == 'complete' dan scroll untuk trigger lazy load,
    # lalu polling sampai <section> dengan link artikel muncul di DOM.
    def _wait_for_articles(drv, timeout=30):
        deadline = time.time() + timeout
        # Tunggu JS ready state complete dulu
        try:
            WebDriverWait(drv, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass
        # Scroll sedikit ke bawah untuk trigger lazy-load JS
        try:
            drv.execute_script("window.scrollTo(0, 300);")
        except Exception:
            pass
        time.sleep(2)
        # Polling sampai section dengan link artikel muncul
        while time.time() < deadline:
            try:
                sections = drv.find_elements(
                    By.CSS_SELECTOR,
                    "section a[href*='/market/2'], section a[href*='/news/2'], "
                    "section a[href*='/research/2'], section a[href*='/opinion/2']"
                )
                if sections:
                    return True
            except Exception:
                pass
            time.sleep(2)
        return False

    found_content = _wait_for_articles(driver)
    if not found_content:
        print("[Parse] Warning: article sections not found after wait, reading DOM as-is.")
    else:
        print("[Parse] Article sections found.")

    time.sleep(1)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Utamakan container CNBC search yang diketahui: div[data-target="search"]
    # Ini adalah div yang di-render oleh JS dan berisi semua <section> artikel.
    container = (
        soup.find("div", attrs={"data-target": "search"})
        or find_best_container(soup)
    )

    if container:
        sections = (
            container.find_all("section")
            or container.find_all("article")
            or container.find_all("div", recursive=False)
        )
    else:
        sections = soup.find_all("section") or soup.find_all("article")

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
        driver.set_page_load_timeout(60)
        try:
            driver.get(url)
        except Exception as exc:
            print(f"[Content] Page load timeout (lanjut baca DOM): {type(exc).__name__}")

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
    seen_urls: set[str] = set()

    try:
        # Gunakan /search dengan fromdate & todate jika filter_dt tersedia —
        # ini memastikan semua artikel pada tanggal target ter-cover,
        # tanpa bergantung pada urutan kronologis halaman.
        # Filter date di sisi kode (_filter_by_date) tetap dijalankan sebagai
        # validasi ganda, tapi stop_early dinonaktifkan karena hasil search
        # sudah dibatasi oleh server.
        query_slug = query.strip().replace(" ", "+")
        if filter_dt:
            date_param = filter_dt.strftime("%d%%2F%m%%2F%Y")  # DD%2FMM%2FYYYY
            search_url = (
                f"{CNBC_SEARCH_URL}?query={query_slug}"
                f"&fromdate={date_param}&todate={date_param}"
            )
            print(f"[Main] Menggunakan search URL dengan filter tanggal: {filter_dt.strftime('%d/%m/%Y')}")
        else:
            search_url = f"{CNBC_SEARCH_URL}?query={query_slug}"
            print("[Main] Menggunakan search URL tanpa filter tanggal.")

        # --- Scrape page 1 dan deteksi total halaman ---
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

        # Dedup + filter (validasi ganda; stop_early tidak berlaku karena
        # server sudah filter tanggal via fromdate/todate)
        all_results = _dedup_articles(all_results, seen_urls)
        all_results, _ = _filter_by_date(all_results, filter_dt, page_num=1)

        # --- Paginate through remaining pages ---
        if total_pages > 1:
            for page_num in range(2, total_pages + 1):
                print(f"\n[Main] === Page {page_num} ===")
                page_url = f"{search_url}&page={page_num}"
                page_results, _ = parse_search_results_page(driver, page_url)

                if not page_results:
                    print("[Main] Empty page — stopping pagination.")
                    break

                page_results = _dedup_articles(page_results, seen_urls)
                filtered, _ = _filter_by_date(page_results, filter_dt, page_num)
                all_results.extend(filtered)

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


def _dedup_articles(articles: list[dict], seen_urls: set[str]) -> list[dict]:
    """
    Hapus artikel duplikat berdasarkan URL (artikel bisa muncul di beberapa kategori).
    """
    unique = []
    for a in articles:
        if a["link"] not in seen_urls:
            seen_urls.add(a["link"])
            unique.append(a)
        else:
            print(f"[Dedup] Skipped duplicate: {a['link'][-60:]}")
    return unique


def _filter_by_date(
    articles: list[dict],
    filter_dt: datetime | None,
    page_num: int,
) -> tuple[list[dict], bool]:
    """
    Filter artikel berdasarkan tanggal target.

    stop_early hanya aktif jika SELURUH artikel di halaman lebih lama dari
    target — bukan berhenti begitu menemukan satu artikel lebih lama.
    Ini penting karena urutan artikel di CNBC tidak selalu kronologis
    (bisa dikelompokkan per kategori/channel).
    """
    if not filter_dt:
        return articles, False

    matched: list[dict] = []
    has_recent = False  # ada artikel dengan tanggal >= target di halaman ini

    for article in articles:
        try:
            article_dt = datetime.strptime(article["date"], "%d %b %Y")
        except ValueError:
            print(f"[Filter] Could not parse date '{article['date']}' — skipped.")
            continue

        if article_dt.date() == filter_dt.date():
            print(f"[Filter] Page {page_num}: MATCH — {article['date']}")
            matched.append(article)
            has_recent = True
        elif article_dt > filter_dt:
            print(f"[Filter] Page {page_num}: Skip — {article['date']} (newer than target)")
            has_recent = True
        else:
            print(f"[Filter] Page {page_num}: Skip — {article['date']} (older than target)")

    # Hentikan pagination hanya jika tidak ada satu pun artikel >= target di halaman ini,
    # yang berarti kita sudah melewati zona waktu yang relevan sepenuhnya.
    stop_early = not has_recent
    if stop_early:
        print(f"[Filter] Page {page_num}: Semua artikel lebih lama dari target — stop pagination.")

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

    tanggal: format "YYYY-MM-DD" / "DD-MM-YYYY" / None.
             Jika None, default ke hari ini (untuk kebutuhan scraping harian).
    """
    # Default ke hari ini jika tanggal tidak diberikan
    if tanggal is None:
        tanggal = datetime.today().strftime("%Y-%m-%d")
        print(f"[Main] tanggal tidak diberikan — default ke hari ini: {tanggal}")

    iso_date = normalize_to_iso_date(tanggal)
    if not iso_date:
        try:
            iso_date = datetime.strptime(tanggal, "%d-%m-%Y").strftime("%Y-%m-%d")
        except ValueError:
            iso_date = tanggal  # biarkan scrape_cnbc_news yang handle error

    results = scrape_cnbc_news(
        query=keyword,
        filter_date=iso_date,
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

    # tanggal=None -> otomatis pakai hari ini
    df = main_cnbc(
        keyword="ihsg",
        tanggal=None,
    )

    if df is not None and not df.empty:
        print(f"\n[Output] Total articles : {len(df)}")
        print(df[["title", "date"]].to_string(index=False))