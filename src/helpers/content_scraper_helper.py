"""
Helper module untuk scraping konten artikel dari berbagai platform.
Digunakan untuk mengambil konten artikel yang hanya tersedia di Google RSS.
"""

import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urlparse


def get_domain_from_url(url):
    """
    Extract domain dari URL.

    Args:
        url: URL artikel

    Returns:
        Domain name (e.g., 'cnbcindonesia.com', 'kompas.com')
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www.
        domain = domain.replace('www.', '')
        return domain
    except:
        return ''


def scrape_cnbc_content(url, headers=None):
    """
    Scrape konten artikel dari CNBC Indonesia.

    Args:
        url: URL artikel CNBC
        headers: Optional HTTP headers

    Returns:
        String konten artikel
    """
    if headers is None:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Find content div
        content_div = soup.find("div", class_="detail-text")
        if not content_div:
            content_div = soup.find("div", class_="detail_text")

        if not content_div:
            return ""

        # Remove unwanted elements
        for unwanted in content_div.find_all(["script", "style", "iframe", "figure", "table"]):
            unwanted.decompose()

        for div in content_div.find_all("div"):
            class_str = " ".join(div.get("class", []))
            if any(x in class_str for x in ["ads", "related", "sisip", "baca", "lihatjg", "linksisip"]):
                div.decompose()

        # Extract text from paragraphs
        all_text_lines = []

        for p in content_div.find_all("p"):
            text = p.get_text(strip=True)
            if text and len(text) > 15:
                # Clean CNBC-specific patterns
                if text.startswith("Jakarta, CNBC Indonesia"):
                    text = text.replace("Jakarta, CNBC Indonesia - ", "")
                    text = text.replace("Jakarta, CNBC Indonesia-", "")

                if text.startswith("(") and text.endswith(")") and len(text) < 20:
                    continue

                all_text_lines.append(text)

        # Extract from lists
        for ol in content_div.find_all(["ol", "ul"]):
            for li in ol.find_all("li", recursive=False):
                text = li.get_text(strip=True)
                if text and len(text) > 15:
                    all_text_lines.append(text)

        result = "\n\n".join(all_text_lines)
        return result

    except Exception as e:
        print(f"[ERROR] Failed to scrape CNBC content: {e}")
        return ""


def scrape_kompas_content(url, headers=None):
    """
    Scrape konten artikel dari Kompas.com.

    Args:
        url: URL artikel Kompas
        headers: Optional HTTP headers

    Returns:
        String konten artikel
    """
    if headers is None:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    all_content = []

    try:
        base_url = url.split('?')[0]
        r = requests.get(base_url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")

        content_div = soup.select_one("div.read__content")
        if not content_div:
            return ""

        cleaned_content = _clean_kompas_content(content_div)
        if cleaned_content and cleaned_content != "-":
            all_content.append(cleaned_content)

        # Check for multiple pages
        total_pages = _get_kompas_total_pages(soup)
        if total_pages > 1:
            for page_num in range(2, total_pages + 1):
                page_url = f"{base_url}?page={page_num}"
                r_page = requests.get(page_url, headers=headers, timeout=15)
                r_page.raise_for_status()
                current_soup = BeautifulSoup(r_page.content, "html.parser")
                content_div = current_soup.select_one("div.read__content")
                if content_div:
                    cleaned_content = _clean_kompas_content(content_div)
                    if cleaned_content and cleaned_content != "-":
                        all_content.append(cleaned_content)
                time.sleep(0.5)

        return "\n\n".join(all_content) if all_content else ""

    except Exception as e:
        print(f"[ERROR] Failed to scrape Kompas content: {e}")
        return ""


def _clean_kompas_content(content_div):
    """Helper untuk membersihkan konten Kompas"""
    if not content_div:
        return "-"

    # Remove unwanted elements
    unwanted_selectors = ["aside", "script", "style", "iframe", "noscript"]
    for sel in unwanted_selectors:
        for tag in content_div.find_all(sel):
            tag.decompose()

    unwanted_classes = [
        "kompasidRec__wrap", "kompasidRec__subs", "kompasidRec__title",
        "articleRelated", "article__related", "inner__sidebar",
        "inject-baca-juga", "ads-on-body"
    ]
    for kelas in unwanted_classes:
        for tag in content_div.find_all(class_=kelas):
            tag.decompose()

    # Extract paragraphs
    elements = content_div.find_all(["p", "li", "h2", "h3"])
    paragraphs = []
    for e in elements:
        text = e.get_text(strip=True)
        if not text or len(text) < 5:
            continue
        if re.search(r'^(baca\s+juga|download\s+sekarang|dalam\s+segala\s+situasi)', text, re.IGNORECASE):
            continue
        paragraphs.append(text)

    if not paragraphs:
        return "-"

    content = "\n\n".join(paragraphs)
    content = re.sub(r'\s+', ' ', content).strip()
    return content


def _get_kompas_total_pages(soup):
    """Helper untuk mendapatkan total halaman Kompas"""
    paging_wrap = soup.select_one("div.paging__wrap")
    if not paging_wrap:
        return 1

    paging_items = paging_wrap.select("div.paging__item")
    if not paging_items:
        return 1

    max_page = 1
    for item in paging_items:
        link = item.select_one("a.paging__link")
        if not link:
            continue
        href = link.get('href', '')
        if '?page=' in href:
            try:
                page_num = int(href.split('?page=')[-1].split('&')[0])
                if page_num > max_page:
                    max_page = page_num
            except (ValueError, IndexError):
                continue

    return max_page


def scrape_tempo_content(url, headers=None):
    """
    Scrape konten artikel dari Tempo.co.

    Args:
        url: URL artikel Tempo
        headers: Optional HTTP headers

    Returns:
        String konten artikel
    """
    if headers is None:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    try:
        r = requests.get(url, headers=headers, timeout=25)
        soup = BeautifulSoup(r.text, 'html.parser')
        teks_final = []

        # Find content container
        kontainer = soup.select_one('div#isi, div.detail-content, article, div.detail-area')
        if not kontainer:
            kontainer = soup

        # Remove unwanted elements
        for tag in kontainer.select('script, style, iframe, figure, aside, nav, '
                                    'div[class*="ad"], div[class*="iklan"], '
                                    'div[class*="share"], div[class*="related"], '
                                    'div[class*="author"], div[class*="penulis"], '
                                    'div.text-neutral-900'):
            tag.decompose()

        # Extract paragraphs
        for p in kontainer.find_all('p'):
            teks = re.sub(r'\s+', ' ', p.get_text(" ", strip=True))
            if len(teks) > 30:
                teks_final.append(teks)

        teks_bersih = "\n\n".join(teks_final)

        # Clean Tempo-specific patterns
        pola_bersih = [
            r'Baca berita.*?klik di sini',
            r'Scroll ke bawah.*',
            r'Lulus dari Jurusan.*?(hak asasi manusia)?',
            r'This is breaking news.*'
        ]
        for pola in pola_bersih:
            teks_bersih = re.sub(pola, '', teks_bersih, flags=re.I)

        teks_bersih = re.sub(r'\s+', ' ', teks_bersih).strip()
        return teks_bersih if teks_bersih else ""

    except Exception as e:
        print(f"[ERROR] Failed to scrape Tempo content: {e}")
        return ""


def scrape_generic_content(url, headers=None):
    """
    Generic content scraper untuk platform yang tidak dikenali.
    Menggunakan heuristic untuk ekstrak konten utama.

    Args:
        url: URL artikel
        headers: Optional HTTP headers

    Returns:
        String konten artikel
    """
    if headers is None:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Remove unwanted elements
        for unwanted in soup.find_all(["script", "style", "iframe", "nav", "header", "footer", "aside"]):
            unwanted.decompose()

        # Try to find main content container
        content = None

        # Common content selectors
        selectors = [
            "article",
            "div.article-content",
            "div.content",
            "div.post-content",
            "div.entry-content",
            "div[class*='article']",
            "div[class*='content']",
            "main"
        ]

        for selector in selectors:
            content = soup.select_one(selector)
            if content:
                break

        if not content:
            content = soup.body if soup.body else soup

        # Extract paragraphs
        paragraphs = []
        for p in content.find_all('p'):
            text = p.get_text(strip=True)
            if text and len(text) > 20:  # Minimal length
                paragraphs.append(text)

        if not paragraphs:
            return ""

        return "\n\n".join(paragraphs)

    except Exception as e:
        print(f"[ERROR] Failed to scrape generic content: {e}")
        return ""


def scrape_article_content(url):
    """
    Smart content scraper yang otomatis detect platform dan gunakan scraper yang sesuai.

    Args:
        url: URL artikel

    Returns:
        String konten artikel
    """
    if not url:
        return ""

    domain = get_domain_from_url(url)

    # Map domain to scraper function
    platform_scrapers = {
        'cnbcindonesia.com': scrape_cnbc_content,
        'kompas.com': scrape_kompas_content,
        'tempo.co': scrape_tempo_content,
    }

    # Check if domain is recognized
    for known_domain, scraper_func in platform_scrapers.items():
        if known_domain in domain:
            print(f"  [CONTENT] Using {known_domain} scraper for: {url[:60]}...")
            content = scraper_func(url)
            if content:
                print(f"  [CONTENT] ✓ Scraped {len(content)} characters")
                return content
            else:
                print(f"  [CONTENT] ✗ Failed, trying generic scraper...")
                break

    # Fallback to generic scraper
    print(f"  [CONTENT] Using generic scraper for: {url[:60]}...")
    content = scrape_generic_content(url)

    if content:
        print(f"  [CONTENT] ✓ Scraped {len(content)} characters")
    else:
        print(f"  [CONTENT] ✗ No content found")

    return content


# Test function
if __name__ == '__main__':
    # Test scraping dari berbagai platform
    test_urls = {
        'cnbc': 'https://www.cnbcindonesia.com/news/...',  # Ganti dengan URL valid
        'kompas': 'https://www.kompas.com/...',
        'tempo': 'https://www.tempo.co/...'
    }

    for platform, url in test_urls.items():
        print(f"\n{'='*70}")
        print(f"Testing {platform.upper()}")
        print(f"{'='*70}")

        content = scrape_article_content(url)

        if content:
            print(f"\nContent preview (first 200 chars):")
            print(content[:200] + "...")
        else:
            print("\nNo content scraped")
