import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import date, timedelta
from openpyxl import load_workbook

EXCEL_PATH = "../results/Terstruktur(Data Scrapping)"
SHEET_NAME = "(Data)CPO"

def extract_rupiah(text):
    match = re.search(r"Rp[\s\.]*([\d\.,]+)", text)
    if match:
        val = re.sub(r"[^\d]", "", match.group(1))
        try:
            return int(val)
        except:
            return None
    return None

def get_article_link_by_date(target_date):
    bulan_id = {
        "January": "Januari", "February": "Februari", "March": "Maret",
        "April": "April", "May": "Mei", "June": "Juni", "July": "Juli",
        "August": "Agustus", "September": "September", "October": "Oktober",
        "November": "November", "December": "Desember"
    }

    bulan_ing = target_date.strftime("%B")
    bulan_ind = bulan_id[bulan_ing]

    target_full_en = target_date.strftime("%d %B %Y")     
    target_full_id = target_date.strftime(f"%d {bulan_ind} %Y") 
    target_nozero_en = target_full_en.lstrip("0")
    target_nozero_id = target_full_id.lstrip("0")

    tahun = target_date.year
    bulan = target_date.month
    archive_url = f"https://gapki.id/news/{tahun}/{bulan:02d}/"

    print(f"🔍 Mencari artikel untuk {target_full_id} di arsip {bulan:02d}/{tahun}...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/121.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(archive_url, headers=headers, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Gagal konek ke arsip GAPKI: {e}")
        return None, None

    soup = BeautifulSoup(resp.text, "lxml")

    for a in soup.select("a"):
        text = a.get_text(" ", strip=True)
        if "Posisi Harga Komoditas" in text and (
            target_full_en in text or target_nozero_en in text or
            target_full_id in text or target_nozero_id in text
        ):
            print(f"✅ Ditemukan artikel: {text}")
            return a["href"], target_date

    print(f"❌ Artikel tanggal {target_full_id} tidak ditemukan di arsip bulan {target_date.strftime('%B')}.")
    return None, None

def scrape_harga(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/121.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    paragraphs = soup.select("div.nv-content-wrap.entry-content p")

    for p in paragraphs:
        text = " ".join(p.stripped_strings).replace("’", "'")
        if any(key in text.upper() for key in ["KPB", "CPO", "KPBN"]):
            match = re.search(r"(?:IDR|Rp)[\s\.]*([\d\.,]+)", text)
            if match:
                val = re.sub(r"[^\d]", "", match.group(1))
                try:
                    harga = int(val)
                    print(f"✅ Ketemu baris harga: {harga}")
                    return harga
                except:
                    continue

    print("❌ Tidak ditemukan baris harga yang cocok.")
    return None

def update_excel(date_value, harga_value):
    try:
        df_old = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
        if "Dates" in df_old.columns:
            df_old["Dates"] = pd.to_datetime(df_old["Dates"]).dt.date
    except Exception:
        df_old = pd.DataFrame(columns=["Dates", "PX_LAST"])

    new_row = pd.DataFrame([{"Dates": date_value.strftime("%Y-%m-%d"), "PX_LAST": harga_value}])
    df_final = pd.concat([df_old, new_row], ignore_index=True)
    df_final.drop_duplicates(subset=["Dates"], inplace=True)

    try:
        book = load_workbook(EXCEL_PATH)
        with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            writer._book = book 
            df_final.to_excel(writer, index=False, sheet_name=SHEET_NAME)
    except FileNotFoundError:
        with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name=SHEET_NAME)

    print(f"💾 Data tersimpan di sheet '{SHEET_NAME}'. Total {len(df_final)} baris.")

def update_harga_komoditas_gapki():
    try:
        df_old = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
        if not df_old.empty and "Dates" in df_old.columns:
            last_date = pd.to_datetime(df_old["Dates"]).max().date()
            print(f"📘 Tanggal terakhir di Excel: {last_date}")
        else:
            last_date = date.today() - timedelta(days=1)
            print("⚠️ Sheet kosong, mulai dari kemarin.")
    except Exception:
        last_date = date.today() - timedelta(days=1)
        print("⚠️ File belum ada, mulai dari kemarin.")

    next_date = last_date + timedelta(days=1)
    while next_date.weekday() >= 5:
        next_date += timedelta(days=1)

    print(f"🎯 Target scraping berikutnya: {next_date.strftime('%d %B %Y')}")

    url, tanggal = get_article_link_by_date(next_date)
    if not url:
        print("❌ Artikel tidak ditemukan untuk tanggal tersebut.")
        return

    harga = scrape_harga(url)
    if not harga:
        return

    update_excel(tanggal, harga)
    print("✨ Update selesai!")

if __name__ == "__main__":
    update_harga_komoditas_gapki()