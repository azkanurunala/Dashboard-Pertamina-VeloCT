import requests
import pandas as pd
from datetime import datetime
import time
import re

# API Key dari The Guardian
API_KEY = "997b85f0-96ed-452c-b509-5f62ec918b2a"

# Keyword pencarian (tidak case sensitive)
# Contoh: "Gasoline", "Oil Price", "Electric Vehicle", "Renewable Energy"
KEYWORD = "Gasoline"

# Rentang tanggal (format: yyyy-mm-dd)
FROM_DATE = "2020-01-01"  # Tanggal mulai
TO_DATE = "2024-12-31"    # Tanggal akhir

BASE_URL = "https://content.guardianapis.com/search"

def fetch_articles(keyword, api_key, from_date, to_date, page=1):
    """
    Fetch articles from The Guardian API with date filters
    """
    params = {
        'q': keyword,
        'api-key': api_key,
        'page': page,
        'page-size': 50,  # Maximum results per page
        'show-fields': 'bodyText',  # Include article content
        'from-date': from_date,
        'to-date': to_date,
        'order-by': 'newest'
    }

    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page {page}: {e}")
        return None

def clean_text(text):
    """
    Remove illegal characters for Excel
    """
    if not text:
        return ''
    # Remove control characters except tab, newline, and carriage return
    return re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)

def extract_article_data(article):
    """
    Extract relevant fields from article
    """
    return {
        'title': clean_text(article.get('webTitle', '')),
        'date': article.get('webPublicationDate', ''),
        'url': article.get('webUrl', ''),
        'content': clean_text(article.get('fields', {}).get('bodyText', ''))
    }

def scrape_all_articles(keyword, api_key, from_date, to_date):
    """
    Scrape all articles matching the keyword within date range
    """
    all_articles = []
    page = 1

    print(f"Starting to scrape articles with keyword: '{keyword}'")
    print(f"Date range: {from_date} to {to_date}")
    print("-" * 60)

    while True:
        print(f"Fetching page {page}...")
        data = fetch_articles(keyword, api_key, from_date, to_date, page)

        if not data or data.get('response', {}).get('status') != 'ok':
            print("Error: Unable to fetch data")
            break

        response = data['response']
        results = response.get('results', [])

        if not results:
            print(f"No more results found. Total pages: {page - 1}")
            break

        # Extract article data
        for article in results:
            article_data = extract_article_data(article)
            all_articles.append(article_data)

        print(f"  - Found {len(results)} articles on page {page}")
        print(f"  - Total articles collected: {len(all_articles)}")

        # Check if there are more pages
        total_pages = response.get('pages', 1)
        if page >= total_pages:
            print(f"\nReached last page. Total pages: {total_pages}")
            break

        page += 1

        # Rate limiting: pause between requests
        time.sleep(0.5)

    return all_articles

def save_to_excel(articles, keyword, from_date, to_date):
    """
    Save articles to Excel file with dynamic filename
    """
    if not articles:
        print("No articles to save.")
        return

    # Create dynamic filename
    keyword_clean = keyword.lower().replace(' ', '_')
    filename = f"theguardian_{keyword_clean}_{from_date}_to_{to_date}.xlsx"

    # Create DataFrame
    df = pd.DataFrame(articles)

    # Convert date format
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d %H:%M:%S')

    # Reorder columns
    df = df[['title', 'date', 'url', 'content']]

    # Save to Excel
    try:
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"\n[OK] Successfully saved {len(articles)} articles to '{filename}'")

        # Display summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total articles: {len(articles)}")
        print(f"Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"Output file: {filename}")
        print("=" * 60)

    except Exception as e:
        print(f"Error saving to Excel: {e}")
        print("Trying to save as CSV instead...")
        csv_filename = filename.replace('.xlsx', '.csv')
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"[OK] Saved as CSV: {csv_filename}")

        # Display summary for CSV
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total articles: {len(articles)}")
        print(f"Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"Output file: {csv_filename}")
        print("=" * 60)

def validate_date(date_str):
    """
    Validate date format (yyyy-mm-dd)
    """
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def main():
    """
    Main function to run the scraper
    """
    # Validate dates
    if not validate_date(FROM_DATE) or not validate_date(TO_DATE):
        print("Error: Invalid date format. Please use yyyy-mm-dd format.")
        return

    print("=" * 60)
    print("THE GUARDIAN API SCRAPER")
    print("=" * 60)
    print(f"Keyword: {KEYWORD}")
    print(f"Date range: {FROM_DATE} to {TO_DATE}")
    print(f"API Key: {API_KEY[:20]}...")
    print("=" * 60)
    print()

    # Scrape articles
    articles = scrape_all_articles(KEYWORD, API_KEY, FROM_DATE, TO_DATE)

    # Save to Excel
    if articles:
        save_to_excel(articles, KEYWORD, FROM_DATE, TO_DATE)

        # Display first few articles as preview
        print("\nPreview of first 3 articles:")
        print("-" * 60)
        for i, article in enumerate(articles[:3], 1):
            print(f"\n{i}. {article['title']}")
            print(f"   Date: {article['date']}")
            print(f"   URL: {article['url']}")
            print(f"   Content preview: {article['content'][:100]}...")
    else:
        print("No articles found.")

if __name__ == "__main__":
    main()
