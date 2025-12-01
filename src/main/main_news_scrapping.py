import pandas as pd
import time
from datetime import datetime, timedelta
import sys
import os
import re 

# Daftarkan parent folder agar Python bisa melihat folder tetangga
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from code_scrapping.bisnis_indonesia import main_bisnis_indonesia
from code_scrapping.kompas import main_kompas
from code_scrapping.tempo import scrape_tempo
from code_scrapping.cnn import scrape_cnn_international 
from code_scrapping.kontan_bbm import scrape_kontan_bbm
from code_scrapping.kontan_biodiesel import scrape_kontan_biodiesel
from code_scrapping.kontan import scrape_kontan
from code_scrapping.cnn import scrape_cnn_international
from code_scrapping.cnbc_id import main_cnbc
from code_scrapping.cnbc import scrape_cnbc_international
from code_scrapping.oilprice import scrape_oilprice
from code_scrapping.bloomberg_technoz import main_bloomberg_technoz

# === SINONIM KEYWORD ===
sinonim_dict = {
    # "indeks risiko geopolitik": ["tekanan geopolitik", "geopolitical risk", "geopolitical pressure"],
    # "indeks volatilitas": ["volatility index"],
    # "kurs": ["nilai tukar rupiah"],
    # "ihsg": ["pasar saham"],
    # "inflasi": ["inflation"],
    # "bi rate": ["suku bunga", "bunga bi"],
    # "jibor": ["jakarta interbank offered rate"],
    # "indeks sales retail": ["indeks penjualan ritel", "indeks penjualan retail", "indeks retail", "indeks ritel"],
    # "indeks kepercayaan konsumen": ["indeks kepercayaan pelanggan"],
    # "indeks kinerja manufaktur": ["purchasing manufaktur index"],
    # "indeks kinerja jasa": ["purchasing services index"],
    # "neraca perdagangan": ["trade balance"],
    # "pertumbuhan domestik bruto": ["PDB", "pertumbuhan ekonomi"],
    "bioenergi": ["minyak kelapa sawit", "crude palm oil", "CPO", "minyak sawit", "kelapa sawit", "sawit", 
                  "HIP BBN Biodesel","biodiesel", "harga fame", "harga indeks pasar biodiesel", "b40", "b50", "biodiesel", "biofuel"],
    "harga bbm" : ["oil price", "minyak mentah","crude oil"], 
    "volume bbm" : ["volume bbm", "oil volume", "minyak mentah", "volume minyak"], 
    "harga produk kilang pertamina" : ["bbm","harga kilang pertamina", "kilang pertamina", "kilang", "refinery", "harga pertamina"], 
    "volume produk kilang pertamina" : ["bbm", "volume kilang pertamina", "volume kilang", "refinery", "volume pertamina"]
}


# === PEMETAAN SUMBER PER KEYWORD ===
sumber_dict = {
    # "indeks risiko geopolitik": [scrape_cnn_international, scrape_cnbc_international],
    # "indeks volatilitas": [scrape_cnn_international, scrape_cnbc_international],
    # "kurs": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    # "ihsg": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    # "inflasi": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    # "bi rate": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    # "jibor": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    # "indeks sales retail": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    # "indeks kepercayaan konsumen": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    # "indeks kinerja manufaktur": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    # "indeks kinerja jasa": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    # "neraca perdagangan": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    # "pertumbuhan domestik bruto": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "bioenergi": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    "harga bbm" : [scrape_kontan_bbm, main_bisnis_indonesia, scrape_oilprice, main_bloomberg_technoz], 
    "volume bbm" : [scrape_kontan_bbm, main_bisnis_indonesia, scrape_oilprice, main_bloomberg_technoz], 
    "harga produk kilang pertamina" : [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    "volume produk kilang pertamina" : [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz]
}

def standardize_format(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["title", "date", "url", "content", "source", "keyword"])
    column_mapping = {
        'Judul': 'title',
        'judul': 'title',
        'Title': 'title',
        'Tanggal': 'date',
        'tanggal': 'date',
        'Date': 'date',
        'Link': 'url',
        'link': 'url',
        'URL': 'url',
        'Konten': 'content',
        'konten': 'content',
        'Content': 'content',
    }
    df = df.rename(columns=column_mapping)
    required_columns = ["title", "date", "url", "content"]
    for col in required_columns:
        if col not in df.columns:
            df[col] = "N/A"
    def clean_date(date_str):
        """Extract YYYY-MM-DD from various date formats"""
        if pd.isna(date_str) or date_str == "N/A" or date_str == "-":
            return "N/A"
        date_str = str(date_str).strip()
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
        if 'T' in date_str or ' ' in date_str:
            date_str = date_str.split('T')[0].split(' ')[0]
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
        return "N/A"
    df['date'] = df['date'].apply(clean_date)
    column_order = ["title", "date", "url", "content", "source", "keyword"]
    existing_cols = [col for col in column_order if col in df.columns]
    df = df[existing_cols]
    return df

# === FUNCTION UTAMA UNTUK SCRAPING SATU KEYWORD ===
def scrape_keyword(keyword, tanggal_filter):
    hasil_final = pd.DataFrame()
    semua_keyword = [keyword] + sinonim_dict.get(keyword, [])

    sumber = sumber_dict.get(keyword, [main_kompas, main_bisnis_indonesia, scrape_tempo, scrape_kontan])

    for kata in semua_keyword:
        print(f"\n🔍 Mencoba scraping dengan kata kunci: '{kata}'")
        hasil_list = []

        for scrape_func in sumber:
            nama_sumber = scrape_func.__name__.replace("scrape_", "").replace("main_", "").upper()
            print(f"   → Scraping dari {nama_sumber}...")

            try:
                data = scrape_func(kata, tanggal_filter)
                if data is not None and len(data) > 0:
                    df_temp = pd.DataFrame(data)
                    df_temp["source"] = nama_sumber
                    df_temp = standardize_format(df_temp)
                    hasil_list.append(df_temp)
                    print(f"     ✅ Dapat {len(df_temp)} berita dari {nama_sumber}.")
                else:
                    print(f"     ⚠️ Tidak ada berita dari {nama_sumber}.")
            except Exception as e:
                print(f"     ❌ Gagal scrape {nama_sumber}: {e}")

        if hasil_list:
            df_temp_keyword = pd.concat(hasil_list, ignore_index=True)
            df_temp_keyword["keyword"] = kata
            hasil_final = pd.concat([hasil_final, df_temp_keyword], ignore_index=True)

    if hasil_final.empty:
        hasil_final = pd.DataFrame(columns=["title", "date", "url", "content", "source", "keyword"])

    return hasil_final

# === MAIN ===

sheet_to_keyword = {
    # "(News)indeks risiko geopolitik": "indeks risiko geopolitik",
    # "(News)indeks volatilitas": "indeks volatilitas",
    # "(News)Kurs": "kurs",
    # "(News)IHSG": "ihsg",
    # "(News)Inflasi": "inflasi",
    # "(News)BI Rate": "bi rate",
    # "(News)JIBOR": "jibor",
    # "(News)indeks sales retail": "indeks sales retail",
    # "(News)indeks kepercayaan knsmn": "indeks kepercayaan konsumen",
    # "(News)indeks kinerja manufaktur": "indeks kinerja manufaktur",
    # "(News)indeks kinerja jasa": "indeks kinerja jasa",
    # "(News)neraca perdagangan": "neraca perdagangan",
    # "(News)PDB": "pertumbuhan domestik bruto",
    "(News)Bioenergi": "bioenergi",
    "(News)Harga Minyak": "harga bbm",
    "(News)Volume Minyak" : "volume bbm",
    "(News)Harga Produk Kilang" : "harga produk kilang pertamina", 
    "(News)Volume Produk Kilang" : "volume produk kilang pertamina"
}

def main():
    # tanggal_filter = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    tanggal_filter = "2025-11-30"
    filename = "../results/(News)Scrapping.xlsx"

    sheet_names = [
                #    "(News)indeks risiko geopolitik",
                #    "(News)indeks volatilitas",
                #    "(News)Kurs",
                #    "(News)IHSG",
                #    "(News)Inflasi",
                #    "(News)BI Rate",
                #    "(News)JIBOR",
                #    "(News)indeks sales retail",
                #    "(News)indeks kepercayaan knsmn",
                #    "(News)indeks kinerja manufaktur",
                #    "(News)indeks kinerja jasa",
                #    "(News)neraca perdagangan",
                #    "(News)PDB",
                   "(News)Bioenergi",
                   "(News)Harga Minyak",
                   "(News)Volume Minyak",
                   "(News)Harga Produk Kilang", 
                   "(News)Volume Produk Kilang"]

    with pd.ExcelWriter(filename, engine="openpyxl", mode="a", if_sheet_exists="overlay") as writer:
        for sheet_name in sheet_names:
            # Ambil keyword asli dari mapping
            keyword_asli = sheet_to_keyword.get(sheet_name)
            if not keyword_asli:
                print(f"⚠️ Keyword untuk sheet '{sheet_name}' tidak ditemukan di mapping. Lewati.")
                continue

            print(f"\n==========================")
            print(f"🚀 MULAI SCRAPING UNTUK: {sheet_name.upper()} (keyword: {keyword_asli.upper()})")
            print(f"==========================")

            hasil_df = scrape_keyword(keyword_asli, tanggal_filter)

            # Gabungkan dengan sheet lama jika ada
            try:
                existing_df = pd.read_excel(filename, sheet_name=sheet_name)
                combined_df = pd.concat([existing_df, hasil_df], ignore_index=True)
            except Exception:
                combined_df = hasil_df

            # Simpan ke sheet sesuai nama yang sudah ada
            combined_df.to_excel(writer, sheet_name=sheet_name, index=False)

            print(f"✅ Selesai scraping untuk '{sheet_name}'. Total berita: {len(combined_df)}")
            print("⏳ Istirahat 1 menit sebelum lanjut...\n")
            time.sleep(60)

    print("\n🎉 Semua keyword selesai diproses!")


if __name__ == "__main__":
    main()