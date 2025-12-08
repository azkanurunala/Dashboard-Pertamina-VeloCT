import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, date
from openpyxl import load_workbook

EXCEL_PATH = "../results/(Terstruktur)Data Scrapping.xlsx"
SHEET_NAME = "(Data)CPO"

def get_max_pagination(base_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/121.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(base_url, headers=headers, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error: {e}")
        return 1
    soup = BeautifulSoup(resp.text, "lxml")
    pagination = soup.select_one("div.bdp-post-pagination")
    if not pagination:
        return 1
    page_links = pagination.select("a.page-numbers")
    max_page = 1
    for link in page_links:
        text = link.get_text(strip=True)
        if text.isdigit():
            max_page = max(max_page, int(text))
    print(f"Total halaman: {max_page}")
    return max_page

def parse_date_from_title(title):
    bulan_id = {
        "Januari": 1, "Februari": 2, "Maret": 3, "April": 4,
        "Mei": 5, "Juni": 6, "Juli": 7, "Agustus": 8,
        "September": 9, "Oktober": 10, "November": 11, "Desember": 12
    }
    pattern = r'(\d{1,2})\s+(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+(\d{4})'
    match = re.search(pattern, title)
    if match:
        day = int(match.group(1))
        month = bulan_id[match.group(2)]
        year = int(match.group(3))
        try:
            return f"{year:04d}-{month:02d}-{day:02d}"
        except:
            return None
    return None

def scrape_articles_from_page(page_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/121.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(page_url, headers=headers, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error di {page_url}: {e}")
        return []
    soup = BeautifulSoup(resp.text, "lxml")
    articles = []
    main_article = soup.select_one("div.bdp-left-block")
    if main_article:
        title_tag = main_article.select_one("h2.bdp-post-title a")
        if title_tag:
            title = title_tag.get_text(strip=True)
            link = title_tag.get("href", "")
            if "Posisi Harga Komoditas" in title:
                article_date = parse_date_from_title(title)
                if article_date:
                    articles.append({
                        "title": title,
                        "url": link,
                        "upload_date": article_date
                    })
    article_containers = soup.select("div.bdp-s-medium-9.bdp-columns")
    for container in article_containers:
        title_tag = container.select_one("h4.bdp-post-title a")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        link = title_tag.get("href", "")
        if "Posisi Harga Komoditas" not in title:
            continue
        article_date = parse_date_from_title(title)
        if article_date:
            articles.append({
                "title": title,
                "url": link,
                "upload_date": article_date
            })
    return articles

def scrape_articles_until_last_date(last_date):
    base_url = "https://gapki.id/posisi-harga-komoditas/"
    print(f"\nMencari artikel baru setelah {last_date}...")
    max_page = get_max_pagination(base_url)
    new_articles = []
    should_stop = False
    for page_num in range(1, max_page + 1):
        if should_stop:
            break
        if page_num == 1:
            page_url = base_url
        else:
            page_url = f"{base_url}page/{page_num}/"
        print(f"Scraping halaman {page_num}...", end=" ")
        articles = scrape_articles_from_page(page_url)
        print(f"{len(articles)} artikel ditemukan")
        for article in articles:
            article_date = article["upload_date"]
            if article_date >= last_date:
                new_articles.append(article)
                print(f"{article_date} - {article['title'][:50]}...")
            else:
                print(f"Artikel {article_date} sudah lebih lama dari {last_date}, berhenti")
                should_stop = True
                break
    print(f"\nTotal artikel baru ditemukan: {len(new_articles)}")
    return new_articles

def get_last_upload_date():
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
        
        if df.empty or "Upload_Dates" not in df.columns:
            print("Sheet kosong atau kolom Upload_Dates tidak ada")
            return None
        
        df["Upload_Dates"] = pd.to_datetime(df["Upload_Dates"], errors='coerce')
        last_date = df["Upload_Dates"].max()
        
        if pd.isna(last_date):
            print("Tidak ada tanggal valid di Upload_Dates")
            return None
        
        last_date_str = last_date.strftime("%Y-%m-%d")
        print(f"Upload_Dates terakhir: {last_date_str}")
        return last_date_str
        
    except FileNotFoundError:
        print("File Excel tidak ditemukan")
        return None
    except Exception as e:
        print(f"Error membaca Excel: {e}")
        return None

def parse_date_in_parentheses(date_str, full_text, article_title=None):
    bulan_abbr = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
        "Mei": 5, "Jun": 6, "Jul": 7, "Agt": 8, "Agu": 8,
        "Sep": 9, "Okt": 10, "Nov": 11, "Des": 12
    }
    match = re.search(r"(\d{1,2})\s*(\w+)", date_str)
    if not match:
        return None
    day = int(match.group(1))
    month_str = match.group(2)
    month = None
    for abbr, num in bulan_abbr.items():
        if month_str.startswith(abbr):
            month = num
            break
    if not month:
        return None
    year = None
    if article_title:
        year_match = re.search(r'20\d{2}', article_title)
        if year_match:
            year = int(year_match.group(0))
    if not year:
        year_match = re.search(r'20\d{2}', full_text)
        if year_match:
            year = int(year_match.group(0))
    if not year:
        year = datetime.now().year
    try:
        return f"{year:04d}-{month:02d}-{day:02d}"
    except:
        return None

def scrape_harga_multi(url, article_title=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/121.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error mengakses artikel: {e}")
        return []
    
    soup = BeautifulSoup(resp.text, "lxml")
    paragraphs = soup.select("div.nv-content-wrap.entry-content p")
    harga_list = []
    
    for p in paragraphs:
        text = p.get_text()
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            if "KPB" in line.upper() and "CPO" in line.upper():
                print(f"DEBUG: Line ditemukan")
                print(f"DEBUG: Repr line original: {repr(line)}")
                
                pattern_with_date = r"([\d\.]+)\s*\((\d{1,2})\s*(\w+)['\u2019]?\)"
                
                matches = list(re.finditer(pattern_with_date, line))
                
                print(f"DEBUG: Jumlah matches: {len(matches)}")
                
                if matches:
                    for i, match in enumerate(matches):
                        print(f"DEBUG: Match {i+1} full: {match.group(0)}")
                        val = re.sub(r"[^\d]", "", match.group(1))
                        try:
                            harga = int(val)
                            day = match.group(2)
                            month_abbr = match.group(3)
                            date_str = f"{day} {month_abbr}"
                            parsed_date = parse_date_in_parentheses(date_str, line, article_title)
                            
                            harga_list.append({
                                "harga": harga,
                                "date_str": date_str,
                                "parsed_date": parsed_date
                            })
                            print(f"Harga {harga} Tanggal ({date_str}) Parsed {parsed_date}")
                        except Exception as e:
                            print(f"DEBUG: Error parsing match {i+1}: {e}")
                            continue
                    
                    return harga_list
                else:
                    match = re.search(r"IDR\s*([\d\.,]+)", line)
                    if match:
                        val = re.sub(r"[^\d]", "", match.group(1))
                        try:
                            harga = int(val)
                            harga_list.append({
                                "harga": harga,
                                "date_str": None,
                                "parsed_date": None
                            })
                            print(f"Harga tanpa tanggal: {harga}")
                            return harga_list
                        except:
                            continue
    
    if not harga_list:
        print("Tidak ditemukan harga")
    return harga_list

def update_excel_with_new_data(new_data_list):
    try:
        df_old = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
        print(f"Data lama: {len(df_old)} baris")
    except:
        df_old = pd.DataFrame(columns=["Upload_Dates", "Dates", "PX_LAST"])
        print("File baru akan dibuat")
    
    df_new = pd.DataFrame(new_data_list)
    
    df_final = pd.concat([df_old, df_new], ignore_index=True)
    
    df_final["Upload_Dates"] = pd.to_datetime(df_final["Upload_Dates"], errors='coerce')
    df_final["Dates"] = pd.to_datetime(df_final["Dates"], errors='coerce')
    
    df_final.drop_duplicates(subset=["Dates"], keep="last", inplace=True)
    
    df_final["Upload_Dates"] = df_final["Upload_Dates"].apply(
        lambda x: x.date() if pd.notna(x) and hasattr(x, 'date') else None
    )
    df_final["Dates"] = df_final["Dates"].apply(
        lambda x: x.date() if pd.notna(x) and hasattr(x, 'date') else None
    )
    
    df_final.sort_values("Dates", ascending=True, inplace=True)
    
    try:
        book = load_workbook(EXCEL_PATH)
        with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            writer._book = book
            df_final.to_excel(writer, index=False, sheet_name=SHEET_NAME)
    except FileNotFoundError:
        with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name=SHEET_NAME)
    
    print(f"\nData tersimpan: {len(df_final)} baris total")
    print(f"Data baru ditambahkan: {len(new_data_list)} baris")

def main_scraper_cpo():
    print("\n" + "="*60)
    print("GAPKI CPO PRICE SCRAPER")
    print("="*60 + "\n")
    last_date = get_last_upload_date()
    if not last_date:
        print("Tidak bisa melanjutkan tanpa tanggal terakhir")
        return
    new_articles = scrape_articles_until_last_date(last_date)
    if not new_articles:
        print("\nTidak ada artikel baru untuk di-scrape")
        return
    print(f"\nMengambil harga dari {len(new_articles)} artikel...")
    all_data = []
    for idx, article in enumerate(new_articles, 1):
        print(f"\n[{idx}/{len(new_articles)}] {article['title'][:50]}...")
        print(f"  {article['url']}")
        harga_list = scrape_harga_multi(article['url'], article['title'])
        if not harga_list:
            print(f"Skip - tidak ada harga ditemukan")
            continue
        if len(harga_list) > 1:
            print(f"Ditemukan {len(harga_list)} harga berbeda")

        for harga_data in harga_list:
            if harga_data["parsed_date"]:
                dates = harga_data["parsed_date"]
            else:
                dates = article["upload_date"]
            
            all_data.append({
                "Upload_Dates": article["upload_date"],
                "Dates": dates,
                "PX_LAST": harga_data["harga"]
            })
    
    if all_data:
        print(f"\n{'='*60}")
        print(f"Menyimpan {len(all_data)} data ke Excel...")
        print(f"{'='*60}")
        update_excel_with_new_data(all_data)
        print("\nSELESAI! Data berhasil diupdate")
    else:
        print("\nTidak ada data untuk disimpan")

if __name__ == "__main__":
    main_scraper_cpo()