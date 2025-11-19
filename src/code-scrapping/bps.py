import requests
import pandas as pd
from datetime import datetime
import re
import time
import os
from bs4 import BeautifulSoup
from html import unescape

def get_news_from_api(api_key, page=0, keyword=None, domain="0000"):
    base_url = "https://webapi.bps.go.id/v1/api/list/model/news"
    url = f"{base_url}/domain/{domain}/page/{page}/key/{api_key}"
    params = {}
    if keyword:
        params['keyword'] = keyword
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except:
        return None

def get_news_detail_from_api(api_key, news_id, domain="0000", lang="ind"):
    base_url = "https://webapi.bps.go.id/v1/api/view"
    url = f"{base_url}/domain/{domain}/model/news/lang/{lang}/id/{news_id}/key/{api_key}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get('status') != 'OK':
            return None
        html_text = data.get('data', {}).get('news', '')
        if not html_text:
            return None
        html_text = unescape(html_text)
        soup = BeautifulSoup(html_text, 'html.parser')
        p_tags = soup.find_all('p')
        result = []
        block = ['narahubung','contact','telp','fax','email','@bps.go.id','jl.','jakarta']
        for p in p_tags:
            t = p.get_text(strip=True)
            if not t:
                continue
            if any(k in t.lower() for k in block):
                continue
            result.append(t)
        return "\n\n".join(result) if result else None
    except:
        return None

def parse_api_response(api_response):
    if not api_response:
        return [], None
    if api_response.get('status') != 'OK':
        return [], None
    if api_response.get('data-availability') != 'available':
        return [], None
    data = api_response.get('data', [])
    if len(data) < 2:
        return [], None
    meta = data[0]
    news_items = data[1]
    results = []
    for item in news_items:
        title = item.get('title', '')
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')
        date_str = item.get('rl_date', '')
        news_id = item.get('news_id', '')
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            y, m, d2 = d.strftime("%Y"), d.strftime("%m"), d.strftime("%d")
            link = f"https://www.bps.go.id/id/news/{y}/{m}/{d2}/{news_id}/{slug}.html"
        except:
            link = f"https://www.bps.go.id/id/news/{news_id}"
        results.append({
            "title": title,
            "date": date_str,
            "kategori": item.get("newscat_name", ""),
            "news_id": news_id,
            "link": link
        })
    return results, meta

def scrape_bps_all(api_key, query=None, filter_date=None, max_pages=None):
    filter_dt = None
    if filter_date:
        try:
            if re.match(r"\d{4}-\d{2}-\d{2}", filter_date):
                filter_dt = datetime.strptime(filter_date, "%Y-%m-%d")
            else:
                filter_dt = datetime.strptime(filter_date, "%d %b %Y")
        except:
            filter_dt = None
    all_results = []
    page = 0
    total_pages = None
    stop = False
    while True:
        resp = get_news_from_api(api_key, page=page, keyword=query)
        news_list, meta = parse_api_response(resp)
        if not news_list:
            break
        if meta and total_pages is None:
            total_pages = meta.get("pages", 1)
            if max_pages:
                total_pages = min(total_pages, max_pages)
        if filter_dt:
            tmp = []
            for n in news_list:
                try:
                    nd = datetime.strptime(n["date"], "%Y-%m-%d")
                    if nd < filter_dt:
                        stop = True
                        break
                    if nd.date() == filter_dt.date():
                        tmp.append(n)
                except:
                    pass
            all_results.extend(tmp)
            if stop:
                break
        else:
            all_results.extend(news_list)
        if max_pages and page + 1 >= max_pages:
            break
        if total_pages and page + 1 >= total_pages:
            break
        page += 1
        time.sleep(1)
    if not all_results:
        return []
    for a in all_results:
        c = get_news_detail_from_api(api_key, a["news_id"])
        a["konten"] = c if c else ""
    for a in all_results:
        try:
            d = datetime.strptime(a["date"], "%Y-%m-%d")
            a["date"] = d.strftime("%d %b %Y")
        except:
            pass
    return all_results

def main_bps(api_key, query=None, filter_tanggal=None, max_pages=None, output_filename="hasil_scrapping_bps"):
    if filter_tanggal:
        if re.match(r"\d{4}-\d{2}-\d{2}", filter_tanggal):
            try:
                dt = datetime.strptime(filter_tanggal, "%Y-%m-%d")
                filter_tanggal = dt.strftime("%d %b %Y")
            except:
                pass

    results = scrape_bps_all(api_key, query=query, filter_date=filter_tanggal, max_pages=max_pages)
    if not results:
        return None
    df = pd.DataFrame(results)
    df["date"] = pd.to_datetime(df["date"], format="%d %b %Y").dt.date
    cols = ["title", "date", "kategori", "konten", "link"]
    df = df[cols]
    folder = "../hasil-scrapping"
    os.makedirs(folder, exist_ok=True)
    if not output_filename:
        q = query.replace(" ", "_") if query else "all"
        output_filename = f"bps_{q}.xlsx"
    if not output_filename.endswith(".xlsx"):
        output_filename += ".xlsx"
    path = os.path.join(folder, output_filename)
    df.to_excel(path, index=False)
    print(f"Saved to {path}")
    return df

if __name__ == "__main__":
    API_KEY = "eb8b64853b0c18e0f6784eb8cf9a76cd"
    main_bps(API_KEY, query="ekonomi", filter_tanggal="2025-11-17")
