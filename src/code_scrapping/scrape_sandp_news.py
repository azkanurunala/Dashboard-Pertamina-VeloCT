import requests
import pandas as pd
import json
import os
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def load_tokens(token_file_path="../../token.json"):
    try:
        with open(token_file_path, 'r') as f:
            token_data = json.load(f)
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            print("Token berhasil dimuat dari file")
            return access_token, refresh_token
    except FileNotFoundError:
        print(f"File {token_file_path} tidak ditemukan")
        return None, None
    except json.JSONDecodeError:
        print(f"Error membaca JSON dari {token_file_path}")
        return None, None

def save_tokens(token_data, token_file_path="../token.json"):
    try:
        with open(token_file_path, 'w') as f:
            json.dump(token_data, f, indent=2)
            print("Token baru berhasil disimpan")
        return True
    except Exception as e:
        print(f"Error menyimpan token: {e}")
        return False

def refresh_access_token(refresh_token, token_file_path="../token.json"):
    url = "https://api.ci.spglobal.com/auth/api/refresh"
    payload = {
        "refresh_token": refresh_token
    }
    try:
        print("Memperbarui access token...")
        print(f"Refresh token: {refresh_token[:20]}...")
        response = requests.post(url, data=payload, timeout=30)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        response.raise_for_status()
        token_data = response.json()
        new_access_token = token_data.get('access_token')
        new_refresh_token = token_data.get('refresh_token', refresh_token)
        save_tokens(token_data, token_file_path)
        print("Access token berhasil diperbarui")
        return new_access_token, new_refresh_token
    except requests.exceptions.RequestException as e:
        print(f"Error saat refresh token: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        return None, None

def extract_text_from_html(html_content):
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, 'html.parser')
    for script in soup(["script", "style"]):
        script.decompose()
    text = soup.get_text(separator=' ', strip=True)
    text = ' '.join(text.split())
    return text

def get_article_content(access_token, article_id):
    url = f"https://api.ci.spglobal.com/news-insights/v1/content/{article_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data and 'envelope' in data and 'content' in data['envelope']:
            body_html = data['envelope']['content'].get('body', '')
            body_text = extract_text_from_html(body_html)
            return body_text
        return ""
    except requests.exceptions.RequestException as e:
        print(f"Error saat mengambil content untuk article {article_id}: {e}")
        return ""

def search_news(access_token, query="SAF", start_date=None, end_date=None, pagesize=1000):
    url = "https://api.ci.spglobal.com/news-insights/v1/search/story"
    if start_date and end_date:
        filter_query = f'updatedDate >= "{start_date}" AND updatedDate < "{end_date}"'
    else:
        filter_query = None
    params = {
        "q": query,
        "pagesize": pagesize
    }
    if filter_query:
        params["filter"] = filter_query
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    try:
        print(f"\nMengambil news untuk query: '{query}'")
        if filter_query:
            print(f"Filter: {filter_query}")
        response = requests.get(url, params=params, headers=headers, timeout=60)
        print(f"Status: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        if data and 'results' in data:
            results = data['results']
            metadata = data.get('metadata', {})
            print(f"Total artikel ditemukan: {metadata.get('count', len(results))}")
            articles = []
            for idx, item in enumerate(results, 1):
                article_id = item.get('id', '')
                headline = item.get('headline', '')
                updated_date = item.get('updatedDate', '')
                document_url = item.get('documentUrl', '')
                date_only = ""
                if updated_date:
                    try:
                        dt = datetime.fromisoformat(updated_date.replace('Z', '+00:00'))
                        date_only = dt.strftime('%Y-%m-%d')
                    except:
                        date_only = updated_date.split('T')[0] if 'T' in updated_date else updated_date

                print(f"  [{idx}/{len(results)}] Mengambil content: {headline[:50]}...")
                content = get_article_content(access_token, article_id)
                articles.append({
                    'title': headline,
                    'date': date_only,
                    'url': document_url,
                    'content': content
                })
            return articles
        else:
            print("Tidak ada hasil ditemukan")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error saat search news: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return []

def scrape_news_sap(keyword="SAF", tanggal_filter=None):
    token_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "token.json")
    access_token, refresh_token = load_tokens(token_file_path)
    if not access_token or not refresh_token:
        print("Gagal memuat S&P Global token dari file")
        return []
    start_date = None
    end_date = None
    if tanggal_filter:
        try:
            date_obj = datetime.strptime(tanggal_filter, '%Y-%m-%d')
            start_date = f"{tanggal_filter} 00:00:00"
            next_day = date_obj + timedelta(days=1)
            end_date = next_day.strftime('%Y-%m-%d 00:00:00')
        except Exception as e:
            print(f"Error parsing tanggal_filter: {e}")
            return []
    articles = search_news(access_token, keyword, start_date, end_date, pagesize=1000)
    if not articles:
        print("Mencoba refresh token...")
        new_access_token, _ = refresh_access_token(refresh_token, token_file_path)
        if new_access_token:
            articles = search_news(new_access_token, keyword, start_date, end_date, pagesize=1000)
        else:
            print("Gagal refresh token")
            return []
    if not articles:
        print("Tidak ada artikel yang ditemukan")
        return []
    print(f"\nBerhasil mengambil {len(articles)} artikel")
    return articles

