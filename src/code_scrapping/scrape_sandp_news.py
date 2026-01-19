import requests
import pandas as pd
import os
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

SP_USERNAME = os.getenv("S&P_USERNAME")
SP_PASSWORD = os.getenv("S&P_PASSWORD")

def login_spglobal(username=None, password=None):
    if username is None:
        username = SP_USERNAME
    if password is None:
        password = SP_PASSWORD
    if not username or not password:
        print("Error: S&P_USERNAME atau S&P_PASSWORD tidak ditemukan di environment variables")
        return None
    url = "https://api.ci.spglobal.com/auth/api"
    payload = {
        "username": username,
        "password": password
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    try:
        print("Login ke S&P Global API...")
        print(f"Username: {username}")
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        print(f"Status code: {response.status_code}")
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data.get('access_token')
        if access_token:
            print("Login berhasil! Access token diperoleh.")
            return access_token
        else:
            print("Login gagal: access_token tidak ditemukan dalam response")
            print(f"Response: {token_data}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error saat login: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        return None

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
    print("\nLogin ke S&P Global API...")
    access_token = login_spglobal()
    if not access_token:
        print("Gagal login ke S&P Global API")
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
        print("Tidak ada artikel yang ditemukan")
        return []
    print(f"\nBerhasil mengambil {len(articles)} artikel")
    return articles


if __name__ == "__main__":
    print("=" * 60)
    print("TEST SCRAPE S&P GLOBAL NEWS")
    print("=" * 60)
    keyword = "SAF"
    tanggal = datetime.today().strftime('%Y-%m-%d')
    print(f"\nKeyword: {keyword}")
    print(f"Tanggal: {tanggal}")
    articles = scrape_news_sap(keyword=keyword, tanggal_filter=tanggal)
    print("\n" + "=" * 60)
    print("HASIL")
    print("=" * 60)
    if articles:
        print(f"Total artikel: {len(articles)}\n")
        for i, article in enumerate(articles[:5], 1):
            print(f"[{i}] {article['title']}")
            print(f"    Date: {article['date']}")
            print(f"    URL: {article['url']}")
            print(f"    Content: {article['content'][:200]}..." if article['content'] else "    Content: -")
            print()
    else:
        print("Tidak ada artikel ditemukan")
    print("=" * 60)
    print("SELESAI")
    print("=" * 60)
