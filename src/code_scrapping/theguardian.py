import requests
import pandas as pd
from datetime import datetime
import re

_API_KEY = "997b85f0-96ed-452c-b509-5f62ec918b2a"
_BASE_URL = "https://content.guardianapis.com/search"

def clean_text(text):
    if not text:
        return ''
    return re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)

def fetch_articles(keyword, start_date, end_date):
    params = {
        'q': keyword,
        'api-key': _API_KEY,
        'page-size': 200, 
        'show-fields': 'bodyText',
        'from-date': start_date,
        'to-date': end_date,
        'order-by': 'newest'
    }
    try:
        print(f"Fetching articles for '{keyword}' from {start_date} to {end_date}...")
        response = requests.get(_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get('response', {}).get('status') != 'ok':
            print(f"Error: API returned non-ok status")
            return []
        results = data['response'].get('results', [])
        print(f"Found {len(results)} articles")
        articles = []
        for article in results:
            date_iso = article.get('webPublicationDate', '')
            if date_iso:
                try:
                    date_obj = datetime.fromisoformat(date_iso.replace('Z', '+00:00'))
                    date_formatted = date_obj.strftime('%Y-%m-%d')
                except:
                    date_formatted = date_iso[:10] 
            else:
                date_formatted = ''
            article_data = {
                'Judul': clean_text(article.get('webTitle', '')),
                'Tanggal': date_formatted,  
                'Link': article.get('webUrl', ''),
                'Konten': clean_text(article.get('fields', {}).get('bodyText', ''))
            }
            articles.append(article_data)
        return articles
    except requests.exceptions.RequestException as e:
        print(f"Error fetching articles: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

def scrape_theguardian(keyword, tanggal):
    print("=" * 80)
    print(f"Scraping The Guardian for keyword: '{keyword}'")
    print("=" * 80)
    if isinstance(tanggal, datetime):
        date_str = tanggal.strftime('%Y-%m-%d')
    else:
        date_str = tanggal
    print(f"Date: {date_str}")
    print()
    articles = fetch_articles(keyword, date_str, date_str)
    if not articles:
        print("No articles found")
        return pd.DataFrame(columns=['Judul', 'Tanggal', 'Link', 'Konten'])
    df = pd.DataFrame(articles)
    df = df[['Judul', 'Tanggal', 'Link', 'Konten']]
    print(f"\nSuccessfully scraped {len(df)} articles")
    print("\nPreview:")
    print(df.head(3).to_string(index=False))
    print("=" * 80)
    return df

if __name__ == "__main__":
    today = "2026-01-02"
    keyword = "Gasoline"
    df = scrape_theguardian(keyword, today)
    df.to_excel("theguardian_results.xlsx", index=False, engine='openpyxl')
    print(f"\nReturned DataFrame shape: {df.shape}")
    if not df.empty:
        print("\nSample data:")
        print(df.head())
