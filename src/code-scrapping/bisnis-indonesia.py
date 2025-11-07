import requests
from bs4 import BeautifulSoup
import re
import time
import pandas as pd
from datetime import datetime
import os

def change_format_date(teks):
    """Mengubah format tanggal dari 'DD NamaBulan YYYY' ke 'YYYY-MM-DD'."""
    bulan = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12',
        'januari': '01', 'februari': '02', 'maret': '03', 'april': '04',
        'mei': '05', 'juni': '06', 'juli': '07', 'agustus': '08',
        'september': '09', 'oktober': '10', 'november': '11', 'desember': '12'
    }
    try:
        part = teks.lower().split()
        if len(part) >= 3:
            day = part[0].zfill(2)
            month = bulan.get(part[1], '01') 
            year = part[2]
            return f"{year}-{month}-{day}"
    except:
        pass 
    return None

def clean_teks(teks):
    if not teks or teks == 'N/A':
        return teks
    teks = re.sub(r'Baca Juga.*', '', teks, flags=re.IGNORECASE | re.DOTALL)
    teks = re.sub(r'\n{3,}', '\n\n', teks)
    return teks.strip()

def get_total_pages_bisnis(soup) -> int:
    pagination_list = soup.find("ol", class_="pagingList")
    if not pagination_list:
        print("  -> Tidak menemukan <ol class='pagingList'>, asumsi 1 halaman.")
        return 1 
    page_links = pagination_list.find_all("a", href=True)
    if not page_links:
        print("  -> 'pagingList' ditemukan, tapi tidak ada link (a), asumsi 1 halaman.")
        return 1
    nums = []
    for a in page_links:
        page_text = a.get_text(strip=True)
        if page_text.isdigit():
            nums.append(int(page_text))
    if not nums:
        return 1
    return max(nums)

def scrap_all_article(keyword, halaman, headers):
    url = f"https://search.bisnis.com/?q={keyword}" + (f"&page={halaman}" if halaman > 1 else "")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status() 
        soup = BeautifulSoup(r.content, 'html.parser')
        return soup.find_all('div', class_='artItem'), soup
    except Exception as e:
        print(f"  -> Gagal mengambil halaman {halaman}: {e}")
        return [], None
    
def get_article_content(url, headers):
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html.parser')
        main_container = soup.find('article', class_='detailsContent')
        if not main_container:
            print(f"    -> Peringatan: Tidak menemukan 'detailsContent', mencari di 'div.col--main' {url}")
            main_container = soup.find('div', class_='col--main')
            if not main_container:
                print(f"    -> Gagal menemukan kontainer konten di {url}")
                return 'N/A'
        for junk_ad in main_container.find_all('div', class_='billboard'):
            junk_ad.decompose()
        for junk_baca in main_container.find_all('div', class_='baca-juga-box'):
            junk_baca.decompose()
        for junk_baca_inline in main_container.find_all(class_='baca-juga-inline'):
            junk_baca_inline.decompose()
        elements = main_container.find_all(['p', 'li'])
        text_lines = []
        for el in elements:
            text = el.get_text(strip=True)
            if text:
                text_lines.append(text)
        if not text_lines:
            return 'N/A' 
        konten = '\n\n'.join(text_lines)
        return clean_teks(konten)
    except Exception as e:
        print(f"    -> Gagal ambil konten {url}: {e}")
        return 'N/A'

def scrape_bisnis(keyword, tanggal, headers):
    """Scrape semua halaman berdasarkan pagination, lalu filter."""
    hasil = []
    total_halaman = 1 
    print("Mengambil halaman 1 untuk cek pagination...")
    item_halaman_1, soup_halaman_1 = scrap_all_article(keyword, 1, headers)
    if not soup_halaman_1:
        print("Gagal mengambil halaman pertama. Proses dihentikan.")
        return []
    total_halaman = get_total_pages_bisnis(soup_halaman_1)
    print(f"Ditemukan total {total_halaman} halaman.")
    for i in item_halaman_1:
        try:
            judul_tag = i.find('h4', class_='artTitle')
            if not judul_tag:
                continue
            judul = judul_tag.get_text(strip=True)
            link = i.find('a', class_='artLink')['href']
            tanggal_asli = i.find('div', class_='artDate').get_text(strip=True)
            tgl = change_format_date(tanggal_asli)
            if tgl == tanggal:
                hasil.append({'judul': judul, 'link': link, 'tanggal': tgl})
        except:
            continue
    for halaman in range(2, total_halaman + 1):
        print(f"Mengambil daftar artikel halaman {halaman}/{total_halaman}...")
        item_list, _ = scrap_all_article(keyword, halaman, headers)
        if not item_list:
            print(f"  -> Tidak ada item di halaman {halaman}, mungkin selesai.")
            break 
        for i in item_list:
            try:
                judul_tag = i.find('h4', class_='artTitle')
                if not judul_tag:
                    continue
                judul = judul_tag.get_text(strip=True)
                link = i.find('a', class_='artLink')['href']
                tanggal_asli = i.find('div', class_='artDate').get_text(strip=True)
                tgl = change_format_date(tanggal_asli)
                
                if tgl == tanggal:
                    hasil.append({'judul': judul, 'link': link, 'tanggal': tgl})
            except:
                continue
        time.sleep(1.5) 
    print(f"\nDitemukan {len(hasil)} artikel yang cocok dengan tanggal {tanggal}.")
    if hasil:
        print("Mulai mengambil konten untuk artikel yang difilter...")
        for i, h in enumerate(hasil):
            print(f"  ({i+1}/{len(hasil)}) Mengambil konten: {h['judul'][:50]}...")
            h['konten'] = get_article_content(h['link'], headers)
            time.sleep(1.5) 
    return hasil

def save_excel(data, keyword, folder_path):
    try:
        os.makedirs(folder_path, exist_ok=True)
    except OSError as e:
        print(f"Gagal membuat folder {folder_path}: {e}")
        folder_path = "."
    nama_file = f"bisnis_{keyword.replace(' ', '_')}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    path_lengkap = os.path.join(folder_path, nama_file)
    pd.DataFrame(data).to_excel(path_lengkap, index=False, engine='openpyxl')
    print(f"\nData disimpan ke {path_lengkap}")

def main_bisnis_indonesia():
    keyword = "Purbaya"
    tanggal = "2025-10-22" 
    results_folder = "../hasil-scrapping"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )
    }
    print(f"Memulai scrape Bisnis.com untuk keyword: '{keyword}' pada tanggal: {tanggal}")
    data = scrape_bisnis(keyword, tanggal, headers)
    if data:
        save_excel(data, keyword, results_folder)
        print("\n=== PRATINJAU HASIL ===")
        for d in data[:3]: 
            print(f"\nJudul: {d['judul']}")
            print(f"Tanggal: {d['tanggal']}")
            print(f"Link: {d['link']}")
            print(f"Konten: {d['konten'][:120]}...")
    else:
        print("Tidak ada artikel ditemukan yang sesuai dengan kriteria.")

if __name__ == "__main__":
    main_bisnis_indonesia()