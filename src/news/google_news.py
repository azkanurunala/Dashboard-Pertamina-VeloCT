import gzip
import io
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

import feedparser
import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


# Constants

REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}
REQUEST_TIMEOUT = 20

# Minimum paragraph character length for content extraction
MIN_PARAGRAPH_LENGTH = 30

# Supported platforms and their sitemap URLs
PLATFORM_SITEMAPS: dict[str, str] = {
    "CNBC": "https://www.cnbc.com/sitemap_news.xml",
    "CNN": "https://www.cnn.com/sitemap/news.xml",
}

# Namespace declarations for Google News sitemap parsing
NS: dict[str, str] = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "news": "http://www.google.com/schemas/sitemap-news/0.9",
}

# Boilerplate patterns to strip from CNN article text
CNN_BOILERPLATE_PATTERNS: list[str] = [
    r"Sign up for CNN.*",
    r"Read more:.*",
    r"Watch:.*",
    r"CNN\'s\s+[\w\s,]+contributed to this report\.?",
    r"This story.*contributed to this report\.?",
]

# Spam keywords used to identify non-content paragraphs
SPAM_KEYWORDS: tuple[str, ...] = (
    "cookie", "privacy policy", "terms of service", "subscribe",
    "sign up", "newsletter", "follow us", "advertisement",
)


# XML / Sitemap Utilities

def fetch_xml(url: str) -> bytes:
    """
    Fetch XML content from a URL, decompressing gzip if necessary.
    """
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        content = response.content

        if url.endswith(".gz") or content[:2] == b"\x1f\x8b":
            with gzip.GzipFile(fileobj=io.BytesIO(content)) as f:
                content = f.read()

        return content
    except Exception:
        return b""


def _extract_sitemap_entry(url_tag: ET.Element) -> dict | None:
    """
    Parse a sitemap <url> element into article metadata (title, url, date).
    """
    loc = url_tag.find("sm:loc", NS)
    if loc is None or not loc.text:
        return None

    news_tag = url_tag.find("news:news", NS)
    title = ""
    date = ""

    if news_tag is not None:
        title_tag = news_tag.find("news:title", NS)
        date_tag  = news_tag.find("news:publication_date", NS)
        title = title_tag.text.strip() if title_tag is not None and title_tag.text else ""
        date  = date_tag.text.strip()[:10] if date_tag is not None and date_tag.text else ""

    if not title:
        title = loc.text.rstrip("/").split("/")[-1].replace("-", " ").title()

    return {"title": title, "url": loc.text.strip(), "date": date}


# Content Validation

def is_valid_paragraph(text: str, min_length: int = 10) -> bool:
    """
    Return True if the text looks like a real content paragraph (not spam or metadata).
    """
    if not text or len(text) < min_length:
        return False

    text_lower = text.lower()
    if any(kw in text_lower for kw in SPAM_KEYWORDS):
        return False

    if re.match(r"^[\d\s\-:,\.]+$", text):
        return False

    return True


# Content Cleaning

def _clean_cnn_text(text: str) -> str:
    """
    Remove CNN-specific boilerplate patterns and normalise whitespace.
    """
    if not text or text == "N/A":
        return text

    for pattern in CNN_BOILERPLATE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)

    return re.sub(r" {2,}", " ", text).strip()


# Article Content Fetching

def _scrape_cnbc(url: str) -> str:
    """
    Fetch a CNBC article page and return its main body text or "N/A".
    """
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=25)
        soup = BeautifulSoup(response.text, "html.parser")
        containers = soup.select(
            'div.ArticleBody-articleBody, section#ArticleBody, div[class*="article-body"]'
        ) or [soup]

        text_lines: list[str] = []

        for container in containers:
            for bad in container.select(
                "script, style, iframe, figure, "
                'div[class*="ad"], div[data-module="mps-slot"], '
                'span[class*="share"], aside, '
                "div.RelatedContent-collapsibleContent, "
                'div[class*="RelatedContent"], div[class*="related"]'
            ):
                bad.decompose()

            for el in container.find_all(["p", "li", "h2"]):
                text = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
                if len(text) > MIN_PARAGRAPH_LENGTH:
                    text_lines.append(text)

        # Full-page fallback if no content found in known containers
        if not text_lines:
            for el in soup.find_all("p"):
                text = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
                if len(text) > MIN_PARAGRAPH_LENGTH:
                    text_lines.append(text)

        return "\n\n".join(text_lines) if text_lines else "N/A"

    except Exception as exc:
        print(f"[Content] Failed to fetch CNBC content: {exc}")
        return "N/A"


def _scrape_cnn(url: str) -> str:
    """
    Fetch a CNN article page, remove non-content elements, and return cleaned body text.
    """
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Remove "Top Headlines" section and its following list
        top_headlines = soup.find("h2", id="top-headlines")
        if top_headlines:
            next_sibling = top_headlines.find_next_sibling()
            while next_sibling:
                if next_sibling.name == "div" and next_sibling.find("ul"):
                    next_sibling.decompose()
                    break
                next_sibling = next_sibling.find_next_sibling()
            top_headlines.decompose()

        for list_div in soup.find_all("div", class_="list-elevate"):
            prev_h2 = list_div.find_previous("h2")
            if prev_h2 and "top headlines" in prev_h2.get_text().lower():
                list_div.decompose()

        paragraphs: list[str] = []
        for selector in ["div.article__content", "div.video-resource__description", "main", "article"]:
            container = soup.select_one(selector)
            if container:
                for el in container.find_all(["h2", "p", "li"]):
                    text = el.get_text(strip=True)
                    if is_valid_paragraph(text, min_length=8) and text not in paragraphs:
                        paragraphs.append(text)
                if len(paragraphs) >= 3:
                    break

        if len(paragraphs) < 2:
            for el in soup.find_all(["h2", "p", "li"]):
                text = el.get_text(strip=True)
                if is_valid_paragraph(text, min_length=10) and text not in paragraphs:
                    paragraphs.append(text)

        return _clean_cnn_text("\n\n".join(paragraphs)) if paragraphs else "N/A"

    except Exception as exc:
        print(f"[Content] Failed to fetch CNN content: {exc}")
        return "N/A"


# Platform Scraper Registry

PLATFORM_SCRAPERS: dict[str, callable] = {
    "CNBC": _scrape_cnbc,
    "CNN": _scrape_cnn,
}


# Google News RSS

def scrape_google_news(
    keyword: str,
    language: str = "en",
    country: str = "US",
    filter_date: str | datetime | None = None,
    filter_platform: str | None = None,
) -> list[dict]:
    """
    Fetch articles from Google News RSS for a keyword with optional date and platform filters.
    """
    encoded_keyword = urllib.parse.quote(keyword)
    rss_url = (
        f"https://news.google.com/rss/search?q={encoded_keyword}"
        f"&hl={language}&gl={country}&ceid={country}:{language}"
    )
    print(f"  [RSS URL] {rss_url}")

    try:
        response = requests.get(rss_url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if not feed.entries:
            print("[Google News] No articles found.")
            return []
    except requests.exceptions.RequestException as exc:
        print(f"[Google News] Error fetching RSS: {exc}")
        return []
    except Exception as exc:
        print(f"[Google News] Error parsing RSS: {exc}")
        return []

# Selenium URL Resolver

def _resolve_google_news_url_selenium(google_url: str) -> str:
    """
    Use Selenium to resolve a Google News redirect URL to its actual destination.
    """
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(20)
        driver.get(google_url)

        max_wait  = 15
        start_time = time.time()
        while time.time() - start_time < max_wait:
            current_url = driver.current_url
            if "news.google.com" not in current_url:
                print("  [Selenium] Redirected successfully.")
                return current_url
            time.sleep(0.5)

        print("  [Selenium] No redirect detected — returning original URL.")
        return google_url

    except Exception as exc:
        print(f"  [Selenium] Error: {str(exc)[:200]}")
        return google_url

    finally:
        if driver:
            driver.quit()


# Sitemap Lookup

def _find_article_in_sitemap(platform: str, title: str, date_str: str | None = None) -> dict | None:
    """
    Search a platform's news sitemap for an article matching the given title and date.
    """
    try:
        if platform not in PLATFORM_SITEMAPS:
            return None

        sitemap_url = PLATFORM_SITEMAPS[platform]
        data = fetch_xml(sitemap_url)
        if not data:
            return None

        root = ET.fromstring(data)

        # Strip platform name suffix from title (e.g. " - CNN", " - CNBC")
        title_clean = re.sub(rf"\s*-\s*{platform}$", "", title, flags=re.IGNORECASE).strip()
        title_normalised = re.sub(r"[^\w\s]", "", title_clean.lower()).strip()

        for url_tag in root.findall(".//sm:url", NS):
            info = _extract_sitemap_entry(url_tag)
            if not info:
                continue
            if date_str and info["date"] != date_str:
                continue

            sitemap_title_normalised = re.sub(r"[^\w\s]", "", info["title"].lower()).strip()
            if title_normalised == sitemap_title_normalised:
                return {"url": info["url"], "title": info["title"]}

        return None

    except Exception as exc:
        print(f"  [Sitemap] Failed to search {platform} sitemap: {exc}")
        return None


# Orchestration

def scrape_google_news_with_content(
    keyword: str,
    language: str = "en",
    country: str = "US",
    filter_date: str | None = None,
    filter_platform: str | None = None,
    use_selenium_fallback: bool = True,
) -> list[dict]:
    """
    Fetch Google News articles with full content using sitemap lookup and Selenium fallback.
    """
    print("=" * 70)
    print("STEP 1: Fetching metadata from Google News")
    print("=" * 70)
    articles = scrape_google_news(keyword, language, country, filter_date, filter_platform)
    if not articles:
        return []

    print("\n" + "=" * 70)
    print("STEP 2: Fetching article content")
    print("=" * 70)
    print(f"Total articles : {len(articles)}")
    print(f"Mode           : Sitemap -> Selenium fallback")
    print(f"Selenium       : {'Enabled' if use_selenium_fallback else 'Disabled'}")

    for idx, article in enumerate(articles):
        article["content"] = "N/A"
        print(f"\n[{idx + 1}/{len(articles)}] {article['title'][:60]}...")
        print(f"  Source : {article['source']}")
        print(f"  Date   : {article['date']}")

        # Identify platform
        platform = next(
            (key for key in PLATFORM_SCRAPERS if key.upper() in article["source"].upper()),
            None,
        )

        if not platform:
            print(f"  [Skip] Platform '{article['source']}' not supported.")
            continue

        scraper_func = PLATFORM_SCRAPERS[platform]
        date_str = article["date"].strftime("%Y-%m-%d") if article["date"] else None

        # Strategy 1: sitemap lookup
        print(f"  [Sitemap] Searching {platform} sitemap...")
        matched = _find_article_in_sitemap(platform, article["title"], date_str)

        if matched:
            print(f"  [Sitemap] FOUND")
            print(f"  [Sitemap] Title : {matched['title'][:60]}...")
            print(f"  [Sitemap] URL   : {matched['url'][:80]}...")
            article["url"] = matched["url"]
            content = scraper_func(matched["url"])
            article["content"] = content
            status = f"OK — {len(content)} chars" if content != "N/A" else "FAIL — empty content"
            print(f"  [Content] {status}")

        else:
            print("  [Sitemap] NOT FOUND")
            if use_selenium_fallback:
                print("  [Selenium] Resolving Google News URL...")
                actual_url = _resolve_google_news_url_selenium(article["url"])
                print(f"  [Selenium] Resolved: {actual_url[:80]}...")
                content = scraper_func(actual_url)
                article["content"] = content
                status = f"OK — {len(content)} chars" if content != "N/A" else "FAIL"
                print(f"  [Content] {status}")
            else:
                print("  [Skip] Selenium fallback disabled.")

        time.sleep(0.5)

    return articles


# Script Entry Point

if __name__ == "__main__":
    print("=" * 70)
    print("Google News scraper — multi-platform (CNBC & CNN)")
    print("=" * 70)

    keyword = "oil"
    platform = input("Pilih platform (CNBC/CNN/ALL): ").strip().upper() or "ALL"

    if platform not in ["CNBC", "CNN", "ALL"]:
        print("Platform tidak valid — menggunakan ALL.")
        platform = "ALL"

    print(f"\nKeyword : '{keyword}'")
    print(f"Filter : {platform}")
    print(f"Strategy : Sitemap -> Selenium fallback")

    articles = scrape_google_news_with_content(
        keyword=keyword,
        filter_platform=None if platform == "ALL" else platform,
        use_selenium_fallback=True,
    )

    if articles:
        total = len(articles)
        success = len([a for a in articles if a["content"] != "N/A"])
        fail = total - success

        print("\n" + "=" * 70)
        print("HASIL SCRAPING")
        print("=" * 70)
        print(f"Total artikel : {total}")
        print(f"Berhasil : {success} ({success / total * 100:.1f}%)")
        print(f"Gagal : {fail} ({fail / total * 100:.1f}%)")

        print("\n" + "=" * 70)
        print("PREVIEW ARTIKEL")
        print("=" * 70)
        for idx, article in enumerate(articles):
            print(f"\n{idx + 1}. {article['title']}")
            print(f"   Date : {article['date']}")
            print(f"   Source : {article['source']}")
            print(f"   URL : {article['url'][:80]}...")
            print(f"   Content : {len(article['content'])} chars")
            if article["content"] != "N/A":
                print(f"   Preview : {article['content'][:150]}...")

        df = pd.DataFrame(articles)
        df.to_excel("google_news.xlsx", index=False, engine="openpyxl")
        print(f"\n[Output] Saved to 'google_news.xlsx'")
        print(f"[Output] Total articles : {total}")

    else:
        print("\n[Output] No articles found.")