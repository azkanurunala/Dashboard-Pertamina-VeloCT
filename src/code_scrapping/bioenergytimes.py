import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time


def search_bioenergytimes(keyword, page=1):
    keyword_formatted = keyword.replace(' ', '+')
    if page == 1:
        url = f"https://bioenergytimes.com/?s={keyword_formatted}"
    else:
        url = f"https://bioenergytimes.com/page/{page}/?s={keyword_formatted}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        articles = []
        article_modules = soup.select("div.tdb_module_loop.td_module_wrap")
        for module in article_modules:
            try:
                title_elem = module.select_one("h3.entry-title.td-module-title a")
                if not title_elem:
                    continue
                title = title_elem.get('title', '').strip()
                if not title:
                    title = title_elem.get_text(strip=True)
                link = title_elem.get('href', '').strip()
                date_elem = module.select_one("span.td-post-date time")
                if not date_elem:
                    date_elem = module.select_one("span.td-post-date")
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    try:
                        date_obj = datetime.strptime(date_text, "%B %d, %Y")
                        date_formatted = date_obj.strftime("%Y-%m-%d")
                    except:
                        date_formatted = date_text
                else:
                    date_formatted = "N/A"
                if title and link:
                    articles.append({
                        'Judul': title,
                        'Tanggal': date_formatted,
                        'Link': link
                    })
            except Exception as e:
                print(f"[WARN] Error parsing article: {e}")
                continue
        return articles
    except Exception as e:
        print(f"[ERROR] Failed to fetch page {page}: {e}")
        return []


def fetch_article_content(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        article_body = soup.select_one("div.tdb_single_content div.tdb-block-inner")
        if not article_body:
            print(f"[WARN] No article content found")
            return "N/A"
        content_parts = []
        for elem in article_body.find_all(['p']):
            text = elem.get_text(strip=True)
            if text and len(text) > 10:
                content_parts.append(text)
        if content_parts:
            content = "\n\n".join(content_parts)
            print(f"Success Extracted {len(content)} characters")
            return content
        return "N/A"
    except Exception as e:
        print(f"Error, Failed to fetch content: {e}")
        return "N/A"

def scrape_bioenergytimes(keyword, tanggal=None):
    all_articles = []
    filter_datetime = None
    if tanggal:
        try:
            if isinstance(tanggal, datetime):
                filter_datetime = tanggal
            else:
                filter_datetime = datetime.strptime(str(tanggal), '%Y-%m-%d')
            print(f"[INFO] Filter tanggal: {filter_datetime.strftime('%Y-%m-%d')}")
        except Exception as e:
            print(f"[WARN] Gagal parse filter_date '{tanggal}': {e}")
            filter_datetime = None
    page = 1
    should_stop = False
    while not should_stop:
        print(f"\n[INFO] Scraping page {page}...")
        articles = search_bioenergytimes(keyword, page)
        if not articles:
            print(f"[INFO] No more articles found on page {page}, stopping.")
            break
        for article in articles:
            try:
                article_date = datetime.strptime(article['Tanggal'], '%Y-%m-%d')
                if filter_datetime:
                    if article_date < filter_datetime:
                        print(f"[INFO] Found article with older date ({article['Tanggal']}) on page {page}, stopping scraping")
                        should_stop = True
                        break
                    elif article_date == filter_datetime:
                        all_articles.append(article)
                else:
                    all_articles.append(article)
            except Exception as e:
                print(f"[WARN] Error parsing date '{article['Tanggal']}': {e}")
                if not filter_datetime:
                    all_articles.append(article)
        if should_stop:
            break
        page += 1
        time.sleep(2)
    print(f"\n[INFO] Total articles found: {len(all_articles)}")
    if not all_articles:
        print("[INFO] No articles to process.")
        return None
    print(f"\n[INFO] Fetching content for {len(all_articles)} articles...\n")
    for i, article in enumerate(all_articles, 1):
        print(f"[{i}/{len(all_articles)}] {article['Judul'][:60]}...")
        article['Konten'] = fetch_article_content(article['Link'])
        if i < len(all_articles):
            time.sleep(2)
    df = pd.DataFrame(all_articles)
    df = df.rename(
        columns={
            'Judul': 'title',
            'Tanggal': 'date',
            'Link': 'url',
            'Konten': 'content'
        }
    )
    return df


def reformat(data):
    if not data:
        print("[WARN] No data to reformat.")
        return None
    df = pd.DataFrame(data)
    df = df.rename(
        columns={
            'Judul': 'title',
            'Tanggal': 'date',
            'Link': 'url',
            'Konten': 'content'
        }
    )
    return df


if __name__ == '__main__':
    df = scrape_bioenergytimes(
        keyword="SAF Indonesia",
        tanggal="2026-01-12"
    )
    if df is not None and not df.empty:
        df.to_excel("bioenergytimes_results.xlsx", index=False, engine='openpyxl')
        print("\n[INFO] Scraping completed and saved to 'bioenergytimes_results.xlsx'")
        print(f"[INFO] Total articles: {len(df)}")
    else:
        print("\n[INFO] No articles found")