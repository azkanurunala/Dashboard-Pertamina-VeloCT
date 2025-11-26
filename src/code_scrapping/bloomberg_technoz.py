import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import re
import locale
import time
import os


locale.setlocale(locale.LC_TIME, "C")
# ============================== Fungsi: Bersihkan dan format tanggal ==============================
def clean_date(raw_date: str) -> str:
    now = datetime.now()
    raw_date = raw_date.replace("|", "").strip().lower()
    if "menit yang lalu" in raw_date or "jam yang lalu" in raw_date:
        match_jam = re.search(r"(\d+)\s*jam", raw_date)
        hours_ago = int(match_jam.group(1)) if match_jam else 0
        match_menit = re.search(r"(\d+)\s*menit", raw_date)
        minutes_ago = int(match_menit.group(1)) if match_menit else 0
        delta = timedelta(hours=hours_ago, minutes=minutes_ago)
        target_datetime = now - delta
        return target_datetime.strftime("%d %b %Y")
    if match_hari := re.search(r"(\d+)\s*hari(?:\s*yang)?\s*lalu", raw_date):
        days_ago = int(match_hari.group(1))
        target_date = now - timedelta(days=days_ago)
        return target_date.strftime("%d %b %Y")
    if match_tanggal := re.match(r"(\d{1,2}\s+\w+\s+\d{4})", raw_date):
        return match_tanggal.group(1).strip()
    return raw_date 

# ============================== FUNGSI: Ambil konten artikel ==============================
def scrape_article_content(url: str, headers: dict) -> str:
    try:
        all_text_lines = []
        page = 1
        while True:
            if page == 1:
                page_url = url
            else:
                page_url = f"{url}/{page}"
            print(f"  [Konten] Mengambil halaman {page}: {page_url}")
            r = requests.get(page_url, headers=headers, timeout=10)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            articles = soup.find_all("div", class_="article")
            if not articles:
                print(f"  [Konten] Tidak ada article di halaman {page}, berhenti.")
                break
            found_content = False
            for article in articles:
                detail_div = article.find("div", class_="detail-in")
                if not detail_div:
                    continue
                found_content = True
                for p in detail_div.find_all("p"):
                    text = p.get_text(strip=True)
                    if text and "Baca Juga" not in text:
                        all_text_lines.append(text)
                for ol in detail_div.find_all("ol"):
                    for li in ol.find_all("li", recursive=False):
                        text = li.get_text(strip=True)
                        if text:
                            all_text_lines.append(text)
            if not found_content:
                print(f"  [Konten] Tidak ada konten di halaman {page}, berhenti.")
                break
            status_div = soup.find("div", class_="status")
            if status_div:
                no_more = status_div.find("div", class_="no-more")
                if no_more and no_more.get_text(strip=True) == "No more pages":
                    print(f"  [Konten] Mencapai akhir artikel.")
                    break
            page += 1
            if page > 10:
                print(f"  [Konten] Batas maksimal 10 halaman tercapai.")
                break
            time.sleep(1) 
        print(f"  [Konten] Total baris text dari semua halaman: {len(all_text_lines)}")
        content = "\n".join(all_text_lines)
        return content
        
    except Exception as e:
        print(f"  [Konten] Gagal mengambil artikel {url}: {e}")
        import traceback
        traceback.print_exc()
        return ""
            
# ============================== Fungsi: Ambil total jumlah halaman dari pagination ==============================
def get_total_pages(soup) -> int:
    pagination = soup.find("ul", class_="pagging") if soup else None
    if not pagination:
        return 1 
    page_links = pagination.find_all("a", href=True)
    nums = []
    for a in page_links:
        match = re.search(r"pagenum=(\d+)", a["href"])
        if match:
            nums.append(int(match.group(1)))
    return max(nums) if nums else 1

# ============================== Fungsi: Parse DAFTAR halaman ==============================
def parse_page_list(url: str, headers: dict, base_url: str):
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"Gagal mengakses halaman list {url}: {e}")
        return [], None
    soup = BeautifulSoup(r.text, "html.parser")
    cards = soup.find_all("div", class_="card-box")
    page_results = []
    for card in cards:
        a_tag = card.find("a", href=True)
        title_tag = card.find("h2", class_="title")
        date_tag = card.find("span", class_="cl-gray")
        title = title_tag.get_text(strip=True) if title_tag else ""
        link = a_tag["href"] if a_tag else ""
        if link and not link.startswith("http"):
            link = base_url + link
        raw_date = date_tag.get_text(strip=True) if date_tag else ""
        pub_date = clean_date(raw_date)
        if not title or not link:
            continue 
        page_results.append({
            "title": title,
            "date": pub_date,
            "link": link,
        })  
    return page_results, soup

# ============================== Fungsi utama (MODIFIKASI): Scrape semua halaman ==============================
def scrape_bloomberg_technoz_all(query: str, headers: dict, filter_date: str = None):
    base_url = "https://www.bloombergtechnoz.com"
    search_base = f"{base_url}/search?query={query}&type=berita"
    
    filter_datetime = None
    if filter_date:
        try:
            filter_datetime = datetime.strptime(filter_date, "%d %b %Y")
            print(f"Filter tanggal: {filter_datetime.strftime('%d %b %Y')}")
        except Exception as e:
            print(f"Warning: Gagal parse filter_date '{filter_date}': {e}")
            filter_datetime = None
    
    all_results, soup_first = parse_page_list(search_base, headers, base_url)
    total_pages = get_total_pages(soup_first)
    print(f"Ditemukan total {total_pages} halaman hasil untuk '{query}'")
    
    should_stop = False
    
    if filter_datetime and all_results:
        for r in all_results[:]:
            try:
                article_date = datetime.strptime(r["date"], "%d %b %Y")
                if article_date < filter_datetime:
                    print(f"Ditemukan berita dengan tanggal lebih lama ({r['date']}) di halaman 1, berhenti scraping")
                    should_stop = True
                    break
            except Exception as e:
                print(f"Warning: Gagal parse tanggal '{r['date']}': {e}")
        all_results = [r for r in all_results if datetime.strptime(r["date"], "%d %b %Y") == filter_datetime]
    
    if not should_stop:
        for page_num in range(2, total_pages + 1):
            print(f"\nMengambil halaman {page_num}/{total_pages}...")
            next_url = f"{search_base}&pagenum={page_num}"
            page_results, _ = parse_page_list(next_url, headers, base_url)
            
            if not page_results:
                print(f"Tidak ada hasil di halaman {page_num}, berhenti.")
                break
            
            if filter_datetime:
                matching_results = []
                for r in page_results:
                    try:
                        article_date = datetime.strptime(r["date"], "%d %b %Y")
                        if article_date < filter_datetime:
                            print(f"Ditemukan berita dengan tanggal lebih lama ({r['date']}) di halaman {page_num}, berhenti scraping")
                            should_stop = True
                            break
                        elif article_date == filter_datetime:
                            matching_results.append(r)
                    except Exception as e:
                        print(f"Warning: Gagal parse tanggal '{r['date']}': {e}")
                
                all_results.extend(matching_results)
                if should_stop:
                    break
            else:
                all_results.extend(page_results)
            
            time.sleep(1)
    
    print(f"\nScraping daftar selesai. Total berita yang lolos filter: {len(all_results)}")
    
    if not all_results:
        print("Tidak ada berita yang lolos filter.")
        return []
    
    final_results_with_content = []
    total_filtered = len(all_results)
    print(f"\nMemulai pengambilan konten untuk {total_filtered} berita yang relevan...")
    
    for i, article in enumerate(all_results, 1):
        print(f"[{i}/{total_filtered}] Mengambil konten: {article['title']}")
        konten = scrape_article_content(article['link'], headers)
        article['konten'] = konten
        final_results_with_content.append(article)
    
    print("Pengambilan konten selesai.")
    return final_results_with_content


# ============================== Main script (MODIFIKASI) ==============================
def main_bloomberg_technoz(query: str, filter_tanggal: str = None, output_filename: str = None):
    if filter_tanggal is None:
        filter_tanggal = datetime.now().strftime("%d %b %Y")
    else:
        if re.match(r"\d{4}-\d{2}-\d{2}", filter_tanggal):
            try:
                temp_date = datetime.strptime(filter_tanggal, "%Y-%m-%d")
                filter_tanggal = temp_date.strftime("%d %b %Y")
                print(f"Format tanggal dikonversi: {filter_tanggal}")
            except Exception as e:
                print(f"Warning: Gagal konversi tanggal '{filter_tanggal}': {e}")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )
    }
    print(f"Memulai scraping untuk query='{query}' dengan filter tanggal='{filter_tanggal}'\n")
    results = scrape_bloomberg_technoz_all(query, headers, filter_date=filter_tanggal)
    if not results:
        print("\nTidak ada hasil ditemukan.")
        return None
    df = pd.DataFrame(results)
    df['date'] = pd.to_datetime(df['date'], format="%d %b %Y")
    df['date'] = df['date'].dt.date
    df = df.rename(
        columns={
            'konten' : 'content', 
            'link' : 'url'
        }
    )
    return df

if __name__ == "__main__":
    df = main_bloomberg_technoz("Biodiesel", filter_tanggal="2025-09-20")