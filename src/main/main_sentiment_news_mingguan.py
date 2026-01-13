import os
import time
import pandas as pd
import sys
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers.summary_helper import (
    setup_gemini,
    summarize_all_news
)
from helpers.onedrive_helper import (
    get_access_token,
    write_multiple_sheets_to_onedrive,
    download_excel_from_onedrive
)

load_dotenv()

ONEDRIVE_SCRAP_PATH = os.getenv("ONEDRIVE_FILE_PATH", "/results/(News)Scrapping.xlsx")
ONEDRIVE_DATA_PATH = "/results/(Terstruktur)Data Scrapping.xlsx"
ONEDRIVE_SENTIMENT_PATH = "/results/(News)Sentiment.xlsx"

TOPICS = {
    "Indeks Risiko Geopolitik": {
        "target_sheets": ["(News)indeks risiko geopolitik"],
        "output_sheet": "(Summary)Idx Risiko Geopolitik",
        "has_data_sentiment": False,
        "role_prompt" : "Ekonom",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
    },
    "Inflasi": {
        "target_sheets": ["(News)Inflasi"],
        "output_sheet": "(Summary)Inflasi",
        "has_data_sentiment": False,
        "role_prompt" : "Ekonom",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
    },
    "BI Rate": {
        "target_sheets": ["(News)BI Rate"],
        "output_sheet": "(Summary)BI-Rate",
        "has_data_sentiment": False,
        "role_prompt" : "Ekonom",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
    },
    "Indeks Penjualan Retail": {
        "target_sheets": ["(News)indeks sales retail"],
        "output_sheet": "(Summary)Idx Penjualan Retail",
        "has_data_sentiment": False,
        "role_prompt" : "Ekonom",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
    },
    "Indeks Keyakinan Konsumen": {
        "target_sheets": ["(News)indeks kepercayaan knsmn"],
        "output_sheet": "(Summary)Idx Keyakinan Konsumen",
        "has_data_sentiment": False,
        "role_prompt" : "Ekonom",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
    },

    "Indeks Kinerja Manufaktur": {
        "target_sheets": ["(News)indeks kinerja manufaktur"],
        "output_sheet": "(Summary)Idx PMI",
        "has_data_sentiment": False,
        "role_prompt" : "Ekonom",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
    },

    "Neraca Perdagangan": {
        "target_sheets": ["(News)neraca perdagangan"],
        "output_sheet": "(Summary)Neraca Perdagangan",
        "has_data_sentiment": False,
        "role_prompt" : "Ekonom",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
    },

    "PDB": {
        "target_sheets": ["(News)PDB"],
        "output_sheet": "(Summary)PDB",
        "has_data_sentiment": False,
        "role_prompt" : "Ekonom",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan Gunakan satuan dan "
                            "waktu secara konsisten (USD/bbl, mb/d, kuartal, tahun). Dan exclude kasus-kasus hukum!"
    },

    "Harga Minyak": {
        "target_sheets": ["(News)Harga Minyak"],
        "output_sheet": "(Summary)Harga Minyak",
        "has_data_sentiment": False,
        "role_prompt" : "industri minyak dan gas",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan Gunakan satuan dan "
                            "waktu secara konsisten (USD/bbl, mb/d, kuartal, tahun). Dan exclude kasus-kasus hukum!"
    },

    "Volume Minyak": {
        "target_sheets": ["(News)Volume Minyak"],
        "output_sheet": "(Summary)Volume Minyak",
        "has_data_sentiment": False,
        "role_prompt" : "industri minyak dan gas",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan Gunakan satuan dan "
                            "waktu secara konsisten (USD/bbl, mb/d, kuartal, tahun). Dan exclude kasus-kasus hukum!"
    },

    "Harga Produk Kilang": {
        "target_sheets": ["(News)Harga Produk Kilang"],
        "output_sheet": "(Summary)Harga Produk Kilang",
        "has_data_sentiment": False,
        "role_prompt" : "industri minyak dan gas",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan Gunakan satuan dan "
                            "waktu secara konsisten (USD/bbl, mb/d, kuartal, tahun). Dan exclude kasus-kasus hukum!"
    },

    "Volume Produk Kilang": {
        "target_sheets": ["(News)Volume Produk Kilang"],
        "output_sheet": "(Summary)Volume Produk Kilang",
        "has_data_sentiment": False,
        "role_prompt" : "industri minyak dan gas",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan Gunakan satuan dan "
                            "waktu secara konsisten (USD/bbl, mb/d, kuartal, tahun). Dan exclude kasus-kasus hukum!"
    },

    "Biodiesel": {
        "target_sheets": ["(News)Biodiesel"],
        "output_sheet": "(Summary)Biodiesel",
        "has_data_sentiment": True,
        "role_prompt" : "analis bioenergi",
        "spesific_prompt" : "Pada hasil summary jangan menggunakan kalimat yang berlebihan seperti signifikan, dahsyat, dst."
                            "Serta hasil summary fokus pada movement data saja, serta exclude kasus-kasus hukum!"
    },

    "Bioetanol": {
        "target_sheets": ["(News)Bioetanol"],
        "output_sheet": "(Summary)Bioetanol",
        "has_data_sentiment": True,
        "role_prompt" : "analis bioenergi",
        "spesific_prompt" : "Pada hasil summary jangan menggunakan kalimat yang berlebihan seperti signifikan, dahsyat, dst."
                            "Serta hasil summary fokus pada movement data saja, serta exclude kasus-kasus hukum!"
    },

    "RUPTL": {
        "target_sheets": ["(News)RUPTL"],
        "output_sheet": "(Summary)RUPTL",
        "has_data_sentiment": False,
        "role_prompt" : "analis ketenagalistrikan Indonesia",
        "spesific_prompt" : "Pada hasil summary jangan menggunakan kalimat yang berlebihan seperti signifikan, dahsyat, dst. "
                            "Batasan: 1 poin hanya 1 kalimat saja, serta exclude kasus-kasus hukum!"
    },

    "SAF": {
        "target_sheets": ["(News)SAF"],
        "output_sheet": "(Summary)SAF",
        "has_data_sentiment": True,
        "role_prompt" : "analis bioenergi",
        "spesific_prompt" : "Pada hasil summary jangan menggunakan kalimat yang berlebihan seperti signifikan, dahsyat, dst. "
                            "Batasan: 1 poin hanya 1 kalimat saja, serta exclude kasus-kasus hukum!"
    }
}

def get_prev_period(existing_df):
    """
    Mengambil periode sebelumnya dari DataFrame existing
    """
    try:
        if existing_df.empty:
            return None, None
        row = existing_df.iloc[-1]
        start_prev = pd.to_datetime(row["Tanggal awal"])
        end_prev = pd.to_datetime(row["Tanggal akhir"])
        return start_prev, end_prev
    except:
        return None, None

def compute_cpo_biodiesel(start_date, end_date, access_token):
    # Download data from OneDrive
    excel_buffer = download_excel_from_onedrive(access_token, ONEDRIVE_DATA_PATH)
    if excel_buffer is None:
        return None, None

    # --- CPO (harian) ---
    df_cpo = pd.read_excel(excel_buffer, sheet_name="(Data)CPO", usecols=["Dates", "PX_LAST"])
    df_cpo["Dates"] = pd.to_datetime(df_cpo["Dates"])
    mask_cpo = (df_cpo["Dates"] >= start_date) & (df_cpo["Dates"] <= end_date)
    cpo_mean = df_cpo.loc[mask_cpo, "PX_LAST"].mean()

    # --- Biodiesel (bulanan) ---
    excel_buffer.seek(0)
    df_bio = pd.read_excel(excel_buffer, sheet_name="(Data)Biodesel", usecols=["Date", "HIP Biodiesel IDR/L"])
    df_bio["Date"] = pd.to_datetime(df_bio["Date"])

    mask_bio = (
        (df_bio["Date"].dt.year == end_date.year) &
        (df_bio["Date"].dt.month == end_date.month)
    )
    bio_mean = df_bio.loc[mask_bio, "HIP Biodiesel IDR/L"].mean()

    return cpo_mean, bio_mean

def get_comparison(start_date, end_date, start_date_prev, end_date_prev, access_token):
    """
    Mengambil rata-rata CPO untuk rentang sekarang dan rentang sebelumnya,
    mengambil nilai biodiesel untuk bulan sekarang & bulan sebelumnya,
    lalu menghitung perubahan persen.
    """
    # Download data from OneDrive
    excel_buffer = download_excel_from_onedrive(access_token, ONEDRIVE_DATA_PATH)
    if excel_buffer is None:
        return {
            "cpo": None,
            "bio": None,
            "cpo_change": None,
            "bio_change": None,
            "same_month": False
        }

    # --- CPO harian ---
    df_cpo = pd.read_excel(excel_buffer, sheet_name="(Data)CPO", usecols=["Dates", "PX_LAST"])
    df_cpo["Dates"] = pd.to_datetime(df_cpo["Dates"]).dt.normalize()

    # current
    cur_mask = (df_cpo["Dates"] >= start_date) & (df_cpo["Dates"] <= end_date)
    cpo_current = df_cpo.loc[cur_mask, "PX_LAST"].mean() if not df_cpo.loc[cur_mask].empty else None

    # previous
    if start_date_prev is not None and end_date_prev is not None:
        prev_mask = (df_cpo["Dates"] >= start_date_prev) & (df_cpo["Dates"] <= end_date_prev)
        cpo_previous = df_cpo.loc[prev_mask, "PX_LAST"].mean() if not df_cpo.loc[prev_mask].empty else None
    else:
        cpo_previous = None

    # change CPO
    if cpo_current is None:
        cpo_current = None
        cpo_change = None
    elif cpo_previous in (None, 0):
        cpo_change = None
    else:
        cpo_change = round(((cpo_current - cpo_previous) / cpo_previous) * 100, 2)

    # --- Biodiesel bulanan ---
    excel_buffer.seek(0)
    df_bio = pd.read_excel(excel_buffer, sheet_name="(Data)Biodesel", usecols=["Date", "HIP Biodiesel IDR/L"])
    df_bio["Date"] = pd.to_datetime(df_bio["Date"])

    # Current month (berdasarkan end_date)
    cur_year = end_date.year
    cur_month = end_date.month
    bio_current_rows = df_bio[(df_bio["Date"].dt.year == cur_year) & (df_bio["Date"].dt.month == cur_month)]
    bio_current = bio_current_rows["HIP Biodiesel IDR/L"].mean() if not bio_current_rows.empty else None

    # Previous month
    if end_date_prev is not None:
        prev_year = end_date_prev.year
        prev_month = end_date_prev.month
        bio_prev_rows = df_bio[(df_bio["Date"].dt.year == prev_year) & (df_bio["Date"].dt.month == prev_month)]
        bio_previous = bio_prev_rows["HIP Biodiesel IDR/L"].mean() if not bio_prev_rows.empty else None
    else:
        bio_previous = None

    # change biodiesel
    if bio_current is None:
        bio_change = None
    elif bio_previous in (None, 0):
        bio_change = None
    else:
        bio_change = round(((bio_current - bio_previous) / bio_previous) * 100, 2)

    # Cek apakah bulan sama (bandingkan end_date dengan end_date_prev)
    same_month = False
    if end_date_prev is not None:
        same_month = (end_date.month == end_date_prev.month and end_date.year == end_date_prev.year)

    def _r(x):
        return None if x is None else round(x, 2)

    return {
        "cpo": _r(cpo_current),
        "bio": _r(bio_current),
        "cpo_change": cpo_change,
        "bio_change": bio_change,
        "same_month": same_month
    }

def get_comparison_bioetanol(start_date, end_date, start_date_prev, end_date_prev, access_token):
    """
    Mengambil nilai bioetanol dan tetes tebu untuk bulan sekarang & bulan sebelumnya,
    lalu menghitung perubahan persen. Karena data bulanan, perbandingan berdasarkan bulan.
    """
    # Download data from OneDrive
    excel_buffer = download_excel_from_onedrive(access_token, ONEDRIVE_DATA_PATH)
    if excel_buffer is None:
        return {
            "bioetanol": None,
            "tetes_tebu": None,
            "bioetanol_change": None,
            "tetes_change": None,
            "same_month": False
        }

    df_bio = pd.read_excel(excel_buffer, sheet_name="(Data)Bioetanol",
                           usecols=["Date", "HIP Bioetanol IDR/L", "Harga Tetes Tebu"])
    df_bio["Date"] = pd.to_datetime(df_bio["Date"])

    # Current month (berdasarkan end_date)
    cur_year = end_date.year
    cur_month = end_date.month
    bio_current_rows = df_bio[(df_bio["Date"].dt.year == cur_year) &
                              (df_bio["Date"].dt.month == cur_month)]
    bioetanol_current = bio_current_rows["HIP Bioetanol IDR/L"].mean() if not bio_current_rows.empty else None
    tetes_current = bio_current_rows["Harga Tetes Tebu"].mean() if not bio_current_rows.empty else None

    # Previous month (berdasarkan end_date_prev)
    if end_date_prev is not None:
        prev_year = end_date_prev.year
        prev_month = end_date_prev.month
        bio_prev_rows = df_bio[(df_bio["Date"].dt.year == prev_year) &
                               (df_bio["Date"].dt.month == prev_month)]
        bioetanol_previous = bio_prev_rows["HIP Bioetanol IDR/L"].mean() if not bio_prev_rows.empty else None
        tetes_previous = bio_prev_rows["Harga Tetes Tebu"].mean() if not bio_prev_rows.empty else None
    else:
        bioetanol_previous = None
        tetes_previous = None

    # Calculate changes
    if bioetanol_current is None:
        bioetanol_change = None
    elif bioetanol_previous in (None, 0):
        bioetanol_change = None
    else:
        bioetanol_change = round(((bioetanol_current - bioetanol_previous) / bioetanol_previous) * 100, 2)

    if tetes_current is None:
        tetes_change = None
    elif tetes_previous in (None, 0):
        tetes_change = None
    else:
        tetes_change = round(((tetes_current - tetes_previous) / tetes_previous) * 100, 2)

    # Cek apakah bulan sama (bandingkan end_date dengan end_date_prev)
    same_month = False
    if end_date_prev is not None:
        same_month = (end_date.month == end_date_prev.month and end_date.year == end_date_prev.year)

    def _r(x):
        return None if x is None else round(x, 2)

    return {
        "bioetanol": _r(bioetanol_current),
        "tetes_tebu": _r(tetes_current),
        "bioetanol_change": bioetanol_change,
        "tetes_change": tetes_change,
        "same_month": same_month
    }

def get_comparison_saf(start_date, end_date, start_date_prev, end_date_prev, access_token):

    excel_buffer = download_excel_from_onedrive(access_token, ONEDRIVE_DATA_PATH)
    if excel_buffer is None:
        return {
            "saf": None,
            "uco": None,
            "saf_change": None,
            "uco_change": None
        }

    df = pd.read_excel(
        excel_buffer,
        sheet_name="(Data)SAF",
        usecols=["assessDate", "value_SAF", "value_UCO"]
    )

    df["assessDate"] = pd.to_datetime(df["assessDate"]).dt.normalize()

    # ======================
    # Current period
    # ======================
    cur_mask = (df["assessDate"] >= start_date) & (df["assessDate"] <= end_date)
    df_cur = df.loc[cur_mask]

    saf_current = df_cur["value_SAF"].mean() if not df_cur["value_SAF"].dropna().empty else None
    uco_current = df_cur["value_UCO"].mean() if not df_cur["value_UCO"].dropna().empty else None

    # ======================
    # Previous period
    # ======================
    if start_date_prev is not None and end_date_prev is not None:
        prev_mask = (df["assessDate"] >= start_date_prev) & (df["assessDate"] <= end_date_prev)
        df_prev = df.loc[prev_mask]

        saf_prev = df_prev["value_SAF"].mean() if not df_prev["value_SAF"].dropna().empty else None
        uco_prev = df_prev["value_UCO"].mean() if not df_prev["value_UCO"].dropna().empty else None
    else:
        saf_prev = None
        uco_prev = None

    # ======================
    # Percentage change
    # ======================
    def pct_change(cur, prev):
        if cur is None or prev in (None, 0):
            return None
        return round(((cur - prev) / prev) * 100, 2)

    return {
        "saf": None if saf_current is None else round(saf_current, 2),
        "uco": None if uco_current is None else round(uco_current, 2),
        "saf_change": pct_change(saf_current, saf_prev),
        "uco_change": pct_change(uco_current, uco_prev)
    }


def process_topic(model, topic_name, config, existing_df, access_token):
    print(f"\n{'='*60}")
    print(f"🔄 Memproses topik: {topic_name}")
    print(f"{'='*60}")
    target_sheets = config["target_sheets"]
    output_sheet = config["output_sheet"]
    has_data_sentiment = config.get("has_data_sentiment", False)

    # Get last date from existing_df instead of file
    last_date = None
    if not existing_df.empty and "Tanggal akhir" in existing_df.columns:
        try:
            last_date = pd.to_datetime(existing_df["Tanggal akhir"].max())
        except:
            pass

    if last_date is not None:
        start_date = last_date + pd.Timedelta(days=1)
    else:
        start_date = datetime(2025, 12, 29)

    today = pd.to_datetime(datetime.now().date())
    end_date = min(start_date + pd.Timedelta(days=6), today)

    print(f"Akan proses berita dari {start_date.date()} sampai {end_date.date()}")

    # Download scrapping data from OneDrive
    print(f"Mengambil data scrapping dari OneDrive: {ONEDRIVE_SCRAP_PATH}")
    excel_buffer = download_excel_from_onedrive(access_token, ONEDRIVE_SCRAP_PATH)

    if excel_buffer is None:
        print(f"⚠️ File scrapping tidak ditemukan di OneDrive")
        return None

    # Collect news from the downloaded data
    all_news_list = []
    excel_file = pd.ExcelFile(excel_buffer)

    for sheet in target_sheets:
        if sheet in excel_file.sheet_names:
            print(f"Ambil berita sheet: {sheet}")
            df_news = pd.read_excel(excel_file, sheet_name=sheet)
            # Filter by date
            if not df_news.empty and "date" in df_news.columns:
                df_news["date"] = pd.to_datetime(df_news["date"], errors='coerce').dt.normalize()
                mask = (df_news["date"] >= start_date) & (df_news["date"] <= end_date)
                filtered_news = df_news[mask]

                # Collect content
                for _, row in filtered_news.iterrows():
                    if pd.notna(row.get("content")):
                        all_news_list.append(str(row["content"]))
                print(f"   ✓ {len(filtered_news)} berita dari {sheet}")

    excel_file.close()

    if not all_news_list:
        print(f"⚠️ Tidak ada berita baru untuk {topic_name}")
        return None

    print(f"Total berita ditemukan: {len(all_news_list)}")
    summary = summarize_all_news(
        model,
        all_news_list,
        start_date,
        end_date,
        target_sheets,
        config["role_prompt"],
        config["spesific_prompt"]
    )

    summary_data = None
    if has_data_sentiment and summary:
        # Ambil periode sebelumnya dari existing_df
        start_prev, end_prev = get_prev_period(existing_df)

        if topic_name == "Biodiesel":
            if start_prev and end_prev:
                comparison = get_comparison(start_date, end_date, start_prev, end_prev, access_token)

                # Cek apakah same_month, jika ya copy Summary Data dari periode sebelumnya
                if comparison["same_month"]:
                    print("⚠️ Masih bulan yang sama, copy Summary Data dari periode sebelumnya")
                    try:
                        summary_data = existing_df.iloc[-1]["Summary Data"] if "Summary Data" in existing_df.columns else None
                    except:
                        summary_data = None
                elif comparison["cpo"] is None or comparison["bio"] is None:
                    print("⚠️ Data CPO atau Biodiesel tidak tersedia")
                    summary_data = None
                else:
                    cpo_trend = "kenaikan" if comparison["cpo_change"] >= 0 else "penurunan"
                    bio_trend = "kenaikan" if comparison["bio_change"] >= 0 else "penurunan"
                    summary_data = (
                        f"Pada periode {start_date.date()} sampai {end_date.date()}, "
                        f"rata-rata CPO {comparison['cpo']:.2f} dan rata-rata Biodiesel {comparison['bio']:.2f}. "
                        f"Periode ini mengalami {cpo_trend} {abs(comparison['cpo_change']):.2f}% nilai CPO "
                        f"dan {bio_trend} {abs(comparison['bio_change']):.2f}% biodiesel dibanding bulan sebelumnya."
                    )

        elif topic_name == "Bioetanol":
            if start_prev and end_prev:
                comparison = get_comparison_bioetanol(start_date, end_date, start_prev, end_prev, access_token)

                # Cek apakah same_month, jika ya copy Summary Data dari periode sebelumnya
                if comparison["same_month"]:
                    print("⚠️ Masih bulan yang sama, copy Summary Data dari periode sebelumnya")
                    try:
                        summary_data = existing_df.iloc[-1]["Summary Data"] if "Summary Data" in existing_df.columns else None
                    except:
                        summary_data = None
                elif comparison["bioetanol"] is None or comparison["tetes_tebu"] is None:
                    print("⚠️ Data Bioetanol atau Tetes Tebu tidak tersedia")
                    summary_data = None
                else:
                    bioetanol_trend = "kenaikan" if comparison["bioetanol_change"] >= 0 else "penurunan"
                    tetes_trend = "kenaikan" if comparison["tetes_change"] >= 0 else "penurunan"
                    summary_data = (
                        f"Pada bulan {end_date.strftime('%B %Y')}, "
                        f"rata-rata Bioetanol {comparison['bioetanol']:.2f} dan rata-rata Tetes Tebu {comparison['tetes_tebu']:.2f}. "
                        f"Periode ini mengalami {bioetanol_trend} {abs(comparison['bioetanol_change']):.2f}% nilai Bioetanol "
                        f"dan {tetes_trend} {abs(comparison['tetes_change']):.2f}% Tetes Tebu dibanding bulan sebelumnya."
                    )
        
        elif topic_name == "SAF":
            if start_prev and end_prev:
                comparison = get_comparison_saf(
                    start_date,
                    end_date,
                    start_prev,
                    end_prev,
                    access_token
                )

                # Helper function untuk format persentase
                def format_change(value):
                    return f"{abs(value):.2f}%" if value is not None else "N/A"
                
                # Helper function untuk trend
                def get_trend(value):
                    if value is None:
                        return "tidak tersedia"
                    return "kenaikan" if value >= 0 else "penurunan"

                if comparison["saf"] is None or comparison["uco"] is None:
                    print("⚠️ Data SAF atau UCO tidak tersedia")
                    summary_data = None
                else:
                    saf_trend = get_trend(comparison["saf_change"])
                    uco_trend = get_trend(comparison["uco_change"])
                    saf_pct = format_change(comparison["saf_change"])
                    uco_pct = format_change(comparison["uco_change"])

                    summary_data = (
                        f"Pada periode {start_date.date()} sampai {end_date.date()}, "
                        f"rata-rata SAF tercatat {comparison['saf']:.2f} dan rata-rata UCO {comparison['uco']:.2f}. "
                        f"Secara periodik, SAF mengalami {saf_trend} {saf_pct} "
                        f"dan UCO mengalami {uco_trend} {uco_pct} dibanding periode sebelumnya."
                    )
            else:
                print("⚠️ Tidak ada data periode sebelumnya")
                summary_data = None


    if summary:
        new_data = {
            "Tanggal awal": start_date.date(),
            "Tanggal akhir": end_date.date(),
            "Summary": summary,
            "Summary Data": summary_data
        }
        return pd.DataFrame([new_data])

    return None

def main():
    print("\n" + "="*60)
    print("NEWS SENTIMENT SUMMARIZATION (MINGGUAN) TO ONEDRIVE")
    print("="*60)

    print("\nAuthenticating to Microsoft Graph API...")
    try:
        access_token = get_access_token()
        print("Authentication successful")
    except Exception as e:
        print(f"Authentication failed: {e}")
        return

    print("\nSetting up Gemini model...")
    model = setup_gemini()

    # Load existing sentiment data from OneDrive
    print(f"\nLoading existing sentiment data from OneDrive...")
    print(f"File: {ONEDRIVE_SENTIMENT_PATH}")

    excel_buffer = download_excel_from_onedrive(access_token, ONEDRIVE_SENTIMENT_PATH)

    all_sheets = {}
    if excel_buffer is None:
        print("File tidak ditemukan, akan membuat file baru")
        for topic_name, config in TOPICS.items():
            all_sheets[config["output_sheet"]] = pd.DataFrame()
    else:
        print("File ditemukan, membaca semua sheets...")
        excel_buffer.seek(0)
        excel_file = pd.ExcelFile(excel_buffer)

        for topic_name, config in TOPICS.items():
            sheet_name = config["output_sheet"]
            try:
                if sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    all_sheets[sheet_name] = df
                    print(f"  Sheet '{sheet_name}': {len(df)} baris")
                else:
                    print(f"  Sheet '{sheet_name}': tidak ada, akan dibuat baru")
                    all_sheets[sheet_name] = pd.DataFrame()
            except Exception as e:
                print(f"  Sheet '{sheet_name}': error - {e}, akan dibuat baru")
                all_sheets[sheet_name] = pd.DataFrame()

        excel_file.close()

    print("\n" + "="*60)
    print("MULAI SUMMARIZATION")
    print("="*60)

    for topic_name, config in TOPICS.items():
        try:
            output_sheet = config["output_sheet"]
            existing_df = all_sheets.get(output_sheet, pd.DataFrame())

            print(f"\n{'-'*60}")
            print(f"Topic: {topic_name}")
            print(f"Output Sheet: {output_sheet}")
            print(f"{'-'*60}")

            new_data = process_topic(model, topic_name, config, existing_df, access_token)

            if new_data is not None:
                if not existing_df.empty:
                    combined_df = pd.concat([existing_df, new_data], ignore_index=True)
                    print(f"\n  Data existing: {len(existing_df)} baris")
                    print(f"  Data baru: {len(new_data)} baris")
                else:
                    combined_df = new_data
                    print(f"\n  Data baru: {len(new_data)} baris")

                all_sheets[output_sheet] = combined_df
                print(f"  Total: {len(combined_df)} baris")
            else:
                print(f"  Tidak ada data baru")

            print("\n⏸️ Istirahat 1 menit sebelum lanjut ke topik berikutnya...")
            time.sleep(60)
        except Exception as e:
            print(f"❌ Error saat memproses {topic_name}: {e}")
            continue

    print("\n" + "="*60)
    print("MENYIMPAN KE ONEDRIVE")
    print("="*60)

    try:
        write_multiple_sheets_to_onedrive(access_token, ONEDRIVE_SENTIMENT_PATH, all_sheets)

        print("\n" + "="*60)
        print("SELESAI!")
        print(f"File: {ONEDRIVE_SENTIMENT_PATH}")
        print(f"Total sheets: {len(all_sheets)}")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\nError saat menyimpan: {e}")
        raise

if __name__ == "__main__":
    main()