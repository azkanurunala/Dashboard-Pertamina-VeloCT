import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import re
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from helpers.content_scraper_helper import scrape_article_content
except ImportError:
    def scrape_article_content(url):
        print(f"[WARNING] content_scraper_helper not available, skipping content scraping")
        return ""

def fetch_google_news_rss(keyword, language='id', country='ID'):
    base_url = "https://news.google.com/rss/search"
    params = {
        'q': keyword,
        'hl': language,
        'gl': country,
        'ceid': f'{country}:{language}'
    }
    try:
        print(f"[Google RSS] Fetching news for keyword: {keyword}")
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        articles = []
        items = root.findall('.//item')
        print(f"[Google RSS] Found {len(items)} articles")
        for idx, item in enumerate(items, 1):
            try:
                title = item.find('title').text if item.find('title') is not None else ''
                link = item.find('link').text if item.find('link') is not None else ''
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ''
                source = item.find('source').text if item.find('source') is not None else ''
                date_formatted = parse_google_rss_date(pub_date)
                print(f"  [{idx}/{len(items)}] {title[:50]}... | {source}")
                actual_url = clean_google_news_url(link, follow_redirect=True, timeout=5)
                if actual_url and 'news.google.com' not in actual_url:
                    print(f"URL resolved: {actual_url[:60]}...")
                else:
                    print(f"Using Google redirect URL (may be skipped in content scraping)")
                articles.append({
                    'title': title,
                    'url': actual_url,
                    'date': date_formatted,
                    'source': source,
                    'content': '',
                    'google_rss_link': link 
                })
                time.sleep(0.2)
            except Exception as e:
                print(f"  [ERROR] Failed to parse item {idx}: {e}")
                continue
        return articles
    except Exception as e:
        print(f"[ERROR] Failed to fetch Google News RSS: {e}")
        return []


def parse_google_rss_date(pub_date_str):
    if not pub_date_str:
        return ''
    try:
        dt = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %Z')
        return dt.strftime('%Y-%m-%d')
    except:
        try:
            dt = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
            return dt.strftime('%Y-%m-%d')
        except:
            return pub_date_str


def clean_google_news_url(google_url, follow_redirect=True, timeout=10):
    if not google_url:
        return ''
    if 'news.google.com' not in google_url:
        return google_url
    if follow_redirect:
        try:
            response = requests.head(google_url, allow_redirects=True, timeout=timeout)
            actual_url = response.url
            if actual_url and 'news.google.com' not in actual_url:
                return actual_url
            response = requests.get(google_url, allow_redirects=True, timeout=timeout, stream=True)
            actual_url = response.url
            if actual_url and 'news.google.com' not in actual_url:
                return actual_url

        except Exception as e:
            print(f"    [WARNING] Failed to follow redirect: {e}")

    return google_url


def normalize_url(url):
    if not url:
        return ''

    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^www\.', '', url)
    url = url.split('?')[0].split('#')[0]
    url = url.rstrip('/')

    return url.lower()


def merge_and_deduplicate(platform_results, google_rss_results, date_filter=None):
    print(f"\n[MERGE] Platform results: {len(platform_results)}")
    print(f"[MERGE] Google RSS results: {len(google_rss_results)}")

    df_platform = pd.DataFrame(platform_results) if platform_results else pd.DataFrame()
    df_google = pd.DataFrame(google_rss_results) if google_rss_results else pd.DataFrame()

    if date_filter:
        print(f"[MERGE] Applying date filter: {date_filter}")

        if not df_platform.empty and 'date' in df_platform.columns:
            df_platform['date'] = pd.to_datetime(df_platform['date'], errors='coerce').dt.strftime('%Y-%m-%d')
            df_platform = df_platform[df_platform['date'] == date_filter]
            print(f"[MERGE] Platform after filter: {len(df_platform)}")

        if not df_google.empty and 'date' in df_google.columns:
            df_google = df_google[df_google['date'] == date_filter]
            print(f"[MERGE] Google RSS after filter: {len(df_google)}")

    if df_platform.empty and df_google.empty:
        print("[MERGE] No results after filtering")
        return []

    if df_google.empty:
        print("[MERGE] Only platform results available")
        return df_platform.to_dict('records')

    if df_platform.empty:
        print("[MERGE] Only Google RSS results available")
        return df_google.to_dict('records')

    df_platform['url_normalized'] = df_platform['url'].apply(normalize_url)
    df_google['url_normalized'] = df_google['url'].apply(normalize_url)

    platform_urls = set(df_platform['url_normalized'].values)
    df_google_unique = df_google[~df_google['url_normalized'].isin(platform_urls)].copy()

    df_platform = df_platform.drop(columns=['url_normalized'])
    df_google_unique = df_google_unique.drop(columns=['url_normalized'])

    combined = pd.concat([df_platform, df_google_unique], ignore_index=True)

    print(f"[MERGE] Platform unique: {len(df_platform)}")
    print(f"[MERGE] Google RSS unique: {len(df_google_unique)}")
    print(f"[MERGE] Total combined: {len(combined)}")
    print(f"[MERGE] Duplicates removed: {len(df_google) - len(df_google_unique)}")

    return combined.to_dict('records')


def scrape_missing_content(df, max_articles=None):
    if df is None or df.empty:
        return df

    mask_empty_content = (df['content'].isna()) | (df['content'] == '')
    articles_to_scrape = df[mask_empty_content].copy()

    if len(articles_to_scrape) == 0:
        print(f"[SCRAPE CONTENT] All articles already have content ✓")
        return df

    print(f"[SCRAPE CONTENT] Found {len(articles_to_scrape)} articles without content")

    if max_articles and len(articles_to_scrape) > max_articles:
        print(f"[SCRAPE CONTENT] Limiting to {max_articles} articles")
        articles_to_scrape = articles_to_scrape.head(max_articles)

    success_count = 0
    failed_count = 0

    for idx, row in articles_to_scrape.iterrows():
        url = row.get('url', '')
        if not url or 'news.google.com' in url:
            print(f"  [{idx+1}] Skipping Google redirect URL")
            failed_count += 1
            continue

        try:
            print(f"  [{idx+1}/{len(articles_to_scrape)}] Scraping: {url[:60]}...")
            content = scrape_article_content(url)

            if content:
                df.at[idx, 'content'] = content
                success_count += 1
                print(f"    ✓ Success ({len(content)} chars)")
            else:
                failed_count += 1
                print(f"    ✗ Failed (no content)")

            time.sleep(0.5)

        except Exception as e:
            failed_count += 1
            print(f"    ✗ Error: {e}")
            continue

    print(f"\n[SCRAPE CONTENT] Summary:")
    print(f"  ✓ Success: {success_count}")
    print(f"  ✗ Failed: {failed_count}")
    print(f"  Total: {len(articles_to_scrape)}")

    return df


def scrape_with_google_rss_fallback(keyword, date=None, platform_scraper=None, scraper_args=None, scrape_content=True):
    if date:
        if isinstance(date, datetime):
            date = date.strftime('%Y-%m-%d')
        else:
            date = str(date)
            if re.match(r'\d{2}\s+\w+\s+\d{4}', date):
                try:
                    dt = datetime.strptime(date, '%d %b %Y')
                    date = dt.strftime('%Y-%m-%d')
                except:
                    pass

    print(f"\n{'='*70}")
    print(f"SCRAPING WITH GOOGLE RSS FALLBACK")
    print(f"Keyword: {keyword}")
    print(f"Date filter: {date if date else 'None'}")
    print(f"{'='*70}\n")

    platform_results = []
    if platform_scraper:
        print(f"[STEP 1] Scraping from platform...")
        try:
            args = scraper_args or {}
            df_platform = platform_scraper(keyword=keyword, tanggal=date, **args)

            if df_platform is not None and not df_platform.empty:
                platform_results = df_platform.to_dict('records')
                print(f"[STEP 1] ✓ Platform scraping successful: {len(platform_results)} articles")
            else:
                print(f"[STEP 1] ⚠ Platform scraping returned no results")
        except Exception as e:
            print(f"[STEP 1] ✗ Platform scraping failed: {e}")
    else:
        print("[STEP 1] No platform scraper provided, skipping...")

    print(f"\n[STEP 2] Scraping from Google News RSS...")
    google_rss_results = fetch_google_news_rss(keyword)

    if google_rss_results:
        print(f"[STEP 2] ✓ Google RSS scraping successful: {len(google_rss_results)} articles")
    else:
        print(f"[STEP 2] ⚠ Google RSS scraping returned no results")

    print(f"\n[STEP 3] Merging and deduplicating...")
    combined_results = merge_and_deduplicate(platform_results, google_rss_results, date_filter=date)

    if not combined_results:
        print(f"[STEP 3] ⚠ No results after merging")
        return None

    df_combined = pd.DataFrame(combined_results)

    standard_columns = ['title', 'date', 'url', 'content']
    for col in standard_columns:
        if col not in df_combined.columns:
            df_combined[col] = ''

    if scrape_content:
        print(f"\n[STEP 4] Scraping content for Google RSS articles...")
        df_combined = scrape_missing_content(df_combined)
    else:
        print(f"\n[STEP 4] Skipping content scraping (scrape_content=False)")

    if 'date' in df_combined.columns:
        df_combined['date'] = pd.to_datetime(df_combined['date'], errors='coerce')
        df_combined = df_combined.sort_values('date', ascending=False)

    print(f"\n{'='*70}")
    print(f"SCRAPING COMPLETED SUCCESSFULLY")
    print(f"Total articles: {len(df_combined)}")
    print(f"{'='*70}\n")

    return df_combined


def main_google_news(keyword, tanggal=None):
    return scrape_with_google_rss_fallback(
        keyword=keyword,
        date=tanggal,
        platform_scraper=None
    )


if __name__ == '__main__':
    df = main_google_news(keyword="pertamina", tanggal="2025-12-30")

    if df is not None and not df.empty:
        print("\nPreview hasil:")
        print(df[['title', 'date', 'source']].head(10))

        output_file = f"google_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(output_file, index=False)
        print(f"\nHasil disimpan ke: {output_file}")
    else:
        print("\nTidak ada hasil")
