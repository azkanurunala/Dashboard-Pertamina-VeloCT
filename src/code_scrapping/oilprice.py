import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd
import json
import re


def parse_oilprice_xml(keyword=None, date_filter=None):
    url = "https://oilprice.com/googlenews.xml"
    print(f"[INFO] Fetching OilPrice.com news XML: {url}")
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        ns = {
            'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
            'news': 'http://www.google.com/schemas/sitemap-news/0.9'
        }
        articles = []
        url_tags = root.findall('.//sm:url', ns)
        print(f"[INFO] Found {len(url_tags)} total articles in XML")
        keyword_lower = keyword.lower() if keyword else None
        for url_tag in url_tags:
            loc = url_tag.find('sm:loc', ns)
            if loc is None or not loc.text:
                continue
            link = loc.text.strip()
            news_tag = url_tag.find('news:news', ns)
            if news_tag is None:
                continue
            title_tag = news_tag.find('news:title', ns)
            date_tag = news_tag.find('news:publication_date', ns)
            keywords_tag = news_tag.find('news:keywords', ns)
            title = title_tag.text.strip() if title_tag is not None and title_tag.text else "(No Title)"
            pubdate_raw = date_tag.text.strip() if date_tag is not None and date_tag.text else ""
            keywords = keywords_tag.text.strip() if keywords_tag is not None and keywords_tag.text else ""
            date_only = pubdate_raw.split('T')[0] if 'T' in pubdate_raw else pubdate_raw
            if keyword_lower:
                title_match = keyword_lower in title.lower()
                keywords_match = keyword_lower in keywords.lower()
                if not (title_match or keywords_match):
                    continue
            if date_filter:
                if isinstance(date_filter, datetime):
                    date_filter_str = date_filter.strftime('%Y-%m-%d')
                else:
                    date_filter_str = str(date_filter)
                if date_only != date_filter_str:
                    continue
            articles.append({
                'Judul': title,
                'Tanggal': date_only,
                'Link': link
            })
        filter_info = []
        if keyword:
            filter_info.append(f"keyword '{keyword}'")
        if date_filter:
            filter_info.append(f"date {date_filter}")
        filter_text = " with " + " and ".join(filter_info) if filter_info else ""
        print(f"[INFO] Found {len(articles)} matching articles{filter_text}")
        return articles
    except Exception as e:
        print(f"[ERROR] Failed to parse XML: {e}")
        return []


def fetch_article_content(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        
        soup = BeautifulSoup(r.content, "html.parser")
        
        json_ld_scripts = soup.find_all('script', {'type': 'application/ld+json'})
        
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                
                if isinstance(data, dict) and data.get('@type') == 'NewsArticle':
                    article_body = data.get('articleBody', '')
                    
                    if article_body:
                        article_body = article_body.replace('&nbsp;', ' ')
                        article_body = article_body.replace('&rsquo;', "'")
                        article_body = article_body.replace('&ldquo;', '"')
                        article_body = article_body.replace('&rdquo;', '"')
                        article_body = re.sub(r'\s+', ' ', article_body)
                        article_body = article_body.strip()
                        
                        print(f"[SUCCESS] Extracted {len(article_body)} characters")
                        return article_body
            except json.JSONDecodeError:
                continue
        
        print(f"[WARN] No JSON-LD found, trying HTML parsing...")
        
        article_body = soup.select_one("div#article-content.wysiwyg.clear")
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
            print(f"[SUCCESS] Extracted {len(content)} characters from HTML")
            return content
        
        return "N/A"
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch content: {e}")
        return "N/A"


def scrape_oilprice(keyword=None, date_filter=None):
    articles = parse_oilprice_xml(keyword, date_filter)
    if not articles:
        print("[INFO] No articles found.")
        return []
    
    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{len(articles)}] {article['Judul'][:60]}...")
        article['Konten'] = fetch_article_content(article['Link'])
    
    return articles


def reformat(data):
    if not data:
        print("[WARN] No data to save.")
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


def save_to_excel(df, filename='oilprice_results.xlsx'):
    try:
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"\n✅ Data berhasil disimpan ke: {filename}")
        print(f"   Total rows: {len(df)}")
        print(f"   Columns: {', '.join(df.columns.tolist())}")
        return True
    except Exception as e:
        print(f"\n❌ Gagal menyimpan ke Excel: {e}")
        return False


def main_oilprice(keyword=None, tanggal=None, save_excel=True):
    print(f"\n{'='*60}")
    print(f"OilPrice.com News Scraper (JSON-LD Method)")
    print(f"{'='*60}\n")
    
    data = scrape_oilprice(keyword, tanggal)
    if not data:  
        print("[INFO] No articles to save.")
        return None
    
    df = reformat(data)
    
    if df is None or df.empty:
        print("[WARN] No data to return")
        return None
    
    print(f"\n{'='*60}")
    print(f"[SUCCESS] Scraped {len(df)} articles")
    print(f"{'='*60}")
    
    print("\nPreview:")
    print(df[['title', 'date']].to_string(index=False))
    
    if save_excel:
        filename = f"oilprice_{keyword.replace(' ', '_')}_{tanggal}.xlsx" if keyword and tanggal else "oilprice_results.xlsx"
        save_to_excel(df, filename)
    
    return df


# if __name__ == '__main__':
#     # result = main_oilprice(
#     #     keyword="Oil Price", 
#     #     tanggal="2025-12-29",
#     #     save_excel=True
#     # )
    
#     # if result is not None:
#     #     print(f"\n{'='*60}")
#     #     print("Content Preview (first article):")
#     #     print(f"{'='*60}")
#     #     print(result.iloc[0]['content'][:500] + "...")