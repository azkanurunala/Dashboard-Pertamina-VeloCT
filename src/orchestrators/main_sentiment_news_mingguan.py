import os
import sys
import time
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.storage_backend import storage
from helpers.summary_helper import setup_gemini, summarize_all_news


# Constants

# Default start date used when no prior summary exists
DEFAULT_START_DATE = datetime(2026, 4, 17)

# Maximum number of articles passed to the summarization model per topic
MAX_NEWS_PER_TOPIC = 200

# Weekly summary window in days
SUMMARY_WINDOW_DAYS = 6


# Topic Configuration

TOPICS: dict[str, dict] = {
    "Indeks Risiko Geopolitik": {
        "target_sheets": ["(News)Indeks Risiko Geopolitik"],
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

    "Indeks Penjualan Ritel": {
        "target_sheets": ["(News)Indeks Penjualan Ritel"],
        "output_sheet": "(Summary)Idx Penjualan Ritel",
        "has_data_sentiment": False,
        "role_prompt" : "Ekonom",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
    },

    "Indeks Kepercayaan Konsumen": {
        "target_sheets": ["(News)Indeks Kepercayaan Knsmn"],
        "output_sheet": "(Summary)Idx Kepercayaan Konsum",
        "has_data_sentiment": False,
        "role_prompt" : "Ekonom",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
    },

    "Indeks PMI": {
        "target_sheets": ["(News)Indeks Kinerja Manufaktur", "(News)Indeks Kinerja Jasa"],
        "output_sheet": "(Summary)Idx PMI",
        "has_data_sentiment": False,
        "role_prompt" : "Ekonom",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
    },

    "Neraca Perdagangan": {
        "target_sheets": ["(News)Neraca Perdagangan"],
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
        "spesific_prompt": "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama "
                           "yang mempengaruhi HARGA minyak. Fokus pada pergerakan harga, faktor "
                           "pendorong harga (supply shock, kebijakan OPEC, sanksi, geopolitik), "
                           "dan level harga terkini (USD/bbl). Berikan data kuantitatif bila ada. "
                           "Gaya Bahasa: Factual dan profesional, tanpa opini atau spekulasi, "
                           "hindari tanda baca berlebihan, gunakan satuan konsisten (USD/bbl). "
                           "Exclude kasus-kasus hukum!"
    },

    "Volume Minyak": {
        "target_sheets": ["(News)Volume Minyak"],
        "output_sheet": "(Summary)Volume Minyak",
        "has_data_sentiment": False,
        "role_prompt" : "industri minyak dan gas",
        "spesific_prompt": "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama "
                           "yang mempengaruhi VOLUME/PRODUKSI minyak. Fokus pada lifting, produksi, "
                           "impor/ekspor, kapasitas kilang, dan kuota produksi (mb/d). "
                           "Berikan data kuantitatif bila ada. "
                           "Gaya Bahasa: Factual dan profesional, tanpa opini atau spekulasi, "
                           "hindari tanda baca berlebihan, gunakan satuan konsisten (mb/d, bbl). "
                           "Exclude kasus-kasus hukum!"
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


    "SAF": {
        "target_sheets": ["(News)SAF"],
        "output_sheet": "(Summary)SAF",
        "has_data_sentiment": True,
        "role_prompt" : "analis bioenergi",
        "spesific_prompt" : "Pada hasil summary jangan menggunakan kalimat yang berlebihan seperti signifikan, dahsyat, dst. "
                            "Batasan: 1 poin hanya 1 kalimat saja, serta exclude kasus-kasus hukum!"
    },

    "RUPTL": {
        "target_sheets": ["(News)RUPTL"],
        "output_sheet": "(Summary)RUPTL",
        "has_data_sentiment": False,
        "role_prompt" : "analis ketenagalistrikan Indonesia",
        "spesific_prompt" : "Pada hasil summary jangan menggunakan kalimat yang berlebihan seperti signifikan, dahsyat, dst. "
                            "Batasan: 1 poin hanya 1 kalimat saja, serta exclude kasus-kasus hukum!"
    },

    "Harga EBT": {
        "target_sheets": ["(News)EBT"],
        "output_sheet": "(Summary)Harga EBT",
        "has_data_sentiment": False,
        "role_prompt": "analis ketenagalistrikan Indonesia",
        "spesific_prompt": "ringkasan menggambarkan situasi yang mempengaruhi HARGA listrik EBT. "
                           "Fokus pada pergerakan harga jual listrik EBT, kebijakan tarif, LCOE, "
                           "dan keputusan PLN/pemerintah terkait harga pembelian listrik EBT. "
                           "Berikan data kuantitatif bila ada (Rp/kWh, USD/kWh). "
                           "Gunakan bahasa ringkas dan netral, 1 poin hanya 1 kalimat, "
                           "exclude kasus hukum!"
    },

    "Kapasitas EBT": {
        "target_sheets": ["(News)EBT"],
        "output_sheet": "(Summary)Kapasitas EBT",
        "has_data_sentiment": False,
        "role_prompt": "analis ketenagalistrikan Indonesia",
        "spesific_prompt": "ringkasan menggambarkan situasi yang mempengaruhi KAPASITAS pembangkit EBT. "
                           "Fokus pada penambahan kapasitas terpasang, target RUPTL, realisasi COD, "
                           "pipeline proyek EBT, dan kebijakan pengembangan kapasitas EBT. "
                           "Berikan data kuantitatif bila ada (MW, GW). "
                           "Gunakan bahasa ringkas dan netral, 1 poin hanya 1 kalimat, "
                           "exclude kasus hukum!"
    },

    "WTE": {
        "target_sheets": ["(News)WTE"],
        "output_sheet": "(Summary)WTE",
        "has_data_sentiment": False,
        "role_prompt": "analis ketenagalistrikan Indonesia",
        "spesific_prompt": "Pada hasil summary jangan menggunakan kalimat yang berlebihan seperti signifikan, dahsyat, dst. "
                           "Batasan: 1 poin hanya 1 kalimat saja, serta exclude kasus-kasus hukum! "
                           "Saat melakukan summary exclude berita-berita yang hanya terkait dengan masalah sampah yang tidak ada kaitannya dengan pembangkit listrik"
    },

    "Nuklir": {
        "target_sheets": ["(News)Nuklir"],
        "output_sheet": "(Summary)Nuklir",
        "has_data_sentiment": False,
        "role_prompt": "analis ketenagalistrikan Indonesia",
        "spesific_prompt": "Gunakan bahasa ringkas dan netral tanpa kata hiperbolik seperti \"signifikan\", \"dahsyat\", dan sejenisnya. "
                           "Setiap poin ringkasan hanya satu kalimat, serta kecualikan kasus hukum. "
                           "Saat merangkum, abaikan berita tentang nuklir yang hanya terkait senjata dan tidak berkaitan dengan pembangkit listrik."
    },

    # "Crackspread_BBM": {
    #     "target_sheets": ["(News)Crackspread BBM"],
    #     "output_sheet": "(Summary)Crackspread BBM",
    #     "has_data_sentiment": False,
    #     "role_prompt": "analis pasar energi dan BBM di Indonesia",
    #     "spesific_prompt": (
    #         "Gunakan bahasa yang ringkas, faktual, dan netral tanpa kata hiperbolik seperti \"signifikan\", \"dahsyat\", atau sejenisnya. "
    #         "Setiap poin ringkasan harus terdiri dari satu kalimat. "
    #         "Fokus pada isu yang memengaruhi crack spread BBM seperti Pertamax, Pertalite, Solar, Avtur, harga minyak mentah, margin kilang, biaya produksi, distribusi, dan kebijakan harga BBM. "
    #         "Kecualikan berita yang bersifat kasus hukum, kriminal, atau politik yang tidak berdampak langsung pada harga atau margin BBM."
    #     ),
    # },

    "Crackspread Non-BBM": {
        "target_sheets": ["(News)Crackspread Non-BBM"],
        "output_sheet": "(Summary)Crackspread Non-BBM",
        "has_data_sentiment": False,
        "role_prompt": "analis pasar energi dan produk kilang non-BBM di Indonesia",
        "spesific_prompt": (
            "Gunakan bahasa yang ringkas, faktual, dan netral tanpa kata hiperbolik seperti \"signifikan\", \"dahsyat\", atau sejenisnya. "
            "Setiap poin ringkasan harus terdiri dari satu kalimat. "
            "Fokus pada isu yang memengaruhi crack spread dan margin produk non-BBM seperti LPG, petrokimia, nafta, propilena, butilena, sulfur, dan produk samping kilang lainnya. "
            "Perhatikan faktor harga minyak mentah, margin kilang, biaya produksi, permintaan industri, distribusi, serta kebijakan energi yang berdampak langsung pada produk non-BBM. "
            "Kecualikan berita yang bersifat kasus hukum, kriminal, atau politik yang tidak berdampak langsung pada harga atau margin produk non-BBM."
        ),
    },

    "Harga Produk Petrokimia": {
        "target_sheets": ["(News)Crackspread Non-BBM"],
        "output_sheet": "(Summary)Harga Petrokimia",
        "has_data_sentiment": False,
        "role_prompt": "analis pasar petrokimia dan harga produk turunan kilang di Indonesia",
        "spesific_prompt": (
            "Gunakan bahasa yang ringkas, faktual, dan netral tanpa kata hiperbolik seperti \"signifikan\", \"dahsyat\", atau sejenisnya. "
            "Setiap poin ringkasan harus terdiri dari satu kalimat. "
            "Fokus khusus pada pergerakan harga produk petrokimia seperti nafta, propilena, polipropilena, etilena, polietilena, butadiene, benzena, dan produk turunan petrokimia lainnya. "
            "Perhatikan faktor harga minyak mentah sebagai bahan baku, permintaan dari industri manufaktur dan plastik, kapasitas produksi, gangguan pasokan, serta dinamika harga di pasar Asia yang memengaruhi harga produk petrokimia. "
            "Kecualikan berita yang bersifat kasus hukum, kriminal, atau politik yang tidak berdampak langsung pada harga produk petrokimia."
        ),
    },

    "Volume Produk Petrokimia": {
        "target_sheets": ["(News)Crackspread Non-BBM"],
        "output_sheet": "(Summary)Volume Petrokimia",
        "has_data_sentiment": False,
        "role_prompt": "analis pasar petrokimia dan volume produksi/permintaan produk kilang non-BBM di Indonesia",
        "spesific_prompt": (
            "Gunakan bahasa yang ringkas, faktual, dan netral tanpa kata hiperbolik seperti \"signifikan\", \"dahsyat\", atau sejenisnya. "
            "Setiap poin ringkasan harus terdiri dari satu kalimat. "
            "Fokus khusus pada volume produksi, ekspor-impor, kapasitas kilang, serta permintaan pasar untuk produk petrokimia seperti nafta, propilena, polipropilena, etilena, polietilena, dan produk turunan lainnya. "
            "Perhatikan faktor kapasitas produksi kilang, gangguan operasional (maintenance/turnaround), kebijakan ekspor-impor, serta pertumbuhan permintaan industri yang memengaruhi volume produk petrokimia. "
            "Kecualikan berita yang bersifat kasus hukum, kriminal, atau politik yang tidak berdampak langsung pada volume produk petrokimia."
        ),
    },

    # Shares its news source with Crackspread_Non_BBM above (no dedicated
    # "Volume Petrokimia" scraper exists) -- kept as a separate topic/output_sheet
    # with a VOLUME-focused prompt (production/kapasitas, not harga/margin) so its
    # Summary text doesn't just duplicate Crackspread_Non_BBM's for the same week
    # (the original complaint, QA Revisi II, when this reused the same prompt).
    "Volume_Petrokimia": {
        "target_sheets": ["(News)Crackspread Non-BBM"],
        "output_sheet": "(Summary)Volume Petrokimia",
        "has_data_sentiment": False,
        "role_prompt": "analis pasar energi dan produk kilang non-BBM di Indonesia",
        "spesific_prompt": (
            "Gunakan bahasa yang ringkas, faktual, dan netral tanpa kata hiperbolik seperti \"signifikan\", \"dahsyat\", atau sejenisnya. "
            "Setiap poin ringkasan harus terdiri dari satu kalimat. "
            "Fokus HANYA pada VOLUME/PRODUKSI produk petrokimia (LPG, nafta, propilena, butilena, sulfur, dan produk samping kilang lainnya): "
            "kapasitas produksi, realisasi produksi, ekspor-impor, permintaan industri, dan distribusi. "
            "JANGAN bahas harga, margin, atau crack spread -- itu di luar scope, sudah dicakup topik lain. "
            "Kecualikan berita yang bersifat kasus hukum, kriminal, atau politik yang tidak berdampak langsung pada volume produk non-BBM."
        ),
    },
}


# Data Comparison Utilities

def _get_prev_period(existing_df: pd.DataFrame) -> tuple["pd.Timestamp | None", "pd.Timestamp | None"]:
    """
    Extract the start and end dates of the most recent summary period from an existing DataFrame.

    Returns (None, None) if the DataFrame is empty or the columns are unavailable.
    """
    try:
        row = _latest_row(existing_df)
        if row is None:
            return None, None
        start_prev = pd.to_datetime(row["Tanggal awal"])
        end_prev = pd.to_datetime(row["Tanggal akhir"])
        return start_prev, end_prev
    except Exception:
        return None, None


def _latest_row(existing_df: pd.DataFrame) -> "pd.Series | None":
    """
    Row with the latest "Tanggal akhir" in an existing DataFrame.

    NOT existing_df.iloc[-1] -- rows come back ordered by DB id (insertion
    order), which drifts from date order once backfills/reruns write out of
    chronological sequence. iloc[-1] silently picked a stale row in that case
    (confirmed on Biodiesel/Bioetanol), corrupting the same-month Summary Data
    copy and the previous-period comparison below.
    """
    if existing_df.empty:
        return None
    akhir = pd.to_datetime(existing_df["Tanggal akhir"])
    return existing_df.loc[akhir.idxmax()]


def _compute_cpo_biodiesel(
    start_date: "pd.Timestamp",
    end_date: "pd.Timestamp",
) -> tuple[float | None, float | None]:
    """
    Compute average CPO (daily) and Biodiesel HIP (monthly) values for a date range.

    Returns (None, None) if the data is unavailable.
    """
    # CPO (daily)
    df_cpo = storage.read_structured_sheet("(Data)CPO")
    if df_cpo.empty:
        return None, None
    df_cpo = df_cpo[["Dates", "PX_LAST"]].copy()
    df_cpo["Dates"] = pd.to_datetime(df_cpo["Dates"])
    mask_cpo = (df_cpo["Dates"] >= start_date) & (df_cpo["Dates"] <= end_date)
    cpo_mean = df_cpo.loc[mask_cpo, "PX_LAST"].mean()

    # Biodiesel (monthly)
    df_bio = storage.read_structured_sheet("(Data)Biodesel")
    if df_bio.empty:
        return cpo_mean, None
    df_bio = df_bio[["Date", "HIP Biodiesel IDR/L"]].copy()
    df_bio["Date"] = pd.to_datetime(df_bio["Date"])
    mask_bio = (
        (df_bio["Date"].dt.year  == end_date.year) &
        (df_bio["Date"].dt.month == end_date.month)
    )
    bio_mean = df_bio.loc[mask_bio, "HIP Biodiesel IDR/L"].mean()

    return cpo_mean, bio_mean


def _get_comparison(
    start_date: "pd.Timestamp",
    end_date: "pd.Timestamp",
    start_date_prev: "pd.Timestamp | None",
    end_date_prev: "pd.Timestamp | None",
) -> dict:
    """
    Compute CPO and Biodiesel averages for the current and previous periods,
    returning values and percentage changes.
    """
    # CPO (daily)
    df_cpo = storage.read_structured_sheet("(Data)CPO")
    if df_cpo.empty:
        return {"cpo": None, "bio": None, "cpo_change": None, "bio_change": None, "same_month": False}
    df_cpo = df_cpo[["Dates", "PX_LAST"]].copy()
    df_cpo["Dates"] = pd.to_datetime(df_cpo["Dates"]).dt.normalize()

    cur_mask = (df_cpo["Dates"] >= start_date) & (df_cpo["Dates"] <= end_date)
    cpo_current = df_cpo.loc[cur_mask, "PX_LAST"].mean() if not df_cpo.loc[cur_mask].empty else None

    if start_date_prev is not None and end_date_prev is not None:
        prev_mask = (df_cpo["Dates"] >= start_date_prev) & (df_cpo["Dates"] <= end_date_prev)
        cpo_previous = df_cpo.loc[prev_mask, "PX_LAST"].mean() if not df_cpo.loc[prev_mask].empty else None
    else:
        cpo_previous = None

    if cpo_current is None or cpo_previous in (None, 0):
        cpo_change = None
    else:
        cpo_change = round(((cpo_current - cpo_previous) / cpo_previous) * 100, 2)

    # Biodiesel (monthly)
    df_bio = storage.read_structured_sheet("(Data)Biodesel")
    if df_bio.empty:
        bio_current = None
        bio_previous = None
    else:
        df_bio = df_bio[["Date", "HIP Biodiesel IDR/L"]].copy()
        df_bio["Date"] = pd.to_datetime(df_bio["Date"])

        cur_year = end_date.year
        cur_month = end_date.month
        bio_current_rows = df_bio[(df_bio["Date"].dt.year == cur_year) & (df_bio["Date"].dt.month == cur_month)]
        bio_current = bio_current_rows["HIP Biodiesel IDR/L"].mean() if not bio_current_rows.empty else None

        if end_date_prev is not None:
            prev_year = end_date_prev.year
            prev_month = end_date_prev.month
            bio_prev_rows = df_bio[(df_bio["Date"].dt.year == prev_year) & (df_bio["Date"].dt.month == prev_month)]
            bio_previous = bio_prev_rows["HIP Biodiesel IDR/L"].mean() if not bio_prev_rows.empty else None
        else:
            bio_previous = None

    if bio_current is None or bio_previous in (None, 0):
        bio_change = None
    else:
        bio_change = round(((bio_current - bio_previous) / bio_previous) * 100, 2)

    same_month = (
        end_date_prev is not None
        and end_date.month == end_date_prev.month
        and end_date.year  == end_date_prev.year
    )

    def _r(x: float | None) -> float | None:
        return None if x is None else round(x, 2)

    return {
        "cpo": _r(cpo_current),
        "bio": _r(bio_current),
        "cpo_change": cpo_change,
        "bio_change": bio_change,
        "same_month": same_month,
    }


def _get_comparison_bioetanol(
    start_date: "pd.Timestamp",
    end_date: "pd.Timestamp",
    start_date_prev: "pd.Timestamp | None",
    end_date_prev: "pd.Timestamp | None",
) -> dict:
    """
    Compute Bioetanol and Tetes Tebu averages for the current and previous months,
    returning values and percentage changes.
    """
    df_bio = storage.read_structured_sheet("(Data)Bioetanol")
    if df_bio.empty:
        return {
            "bioetanol": None, "tetes_tebu": None,
            "bioetanol_change": None, "tetes_change": None, "same_month": False,
        }

    df_bio = df_bio[["Date", "HIP Bioetanol IDR/L", "Harga Tetes Tebu"]].copy()
    df_bio["Date"] = pd.to_datetime(df_bio["Date"])

    cur_year = end_date.year
    cur_month = end_date.month
    bio_current_rows = df_bio[
        (df_bio["Date"].dt.year == cur_year) & (df_bio["Date"].dt.month == cur_month)
    ]
    bioetanol_current = bio_current_rows["HIP Bioetanol IDR/L"].mean() if not bio_current_rows.empty else None
    tetes_current = bio_current_rows["Harga Tetes Tebu"].mean()    if not bio_current_rows.empty else None

    if end_date_prev is not None:
        prev_year = end_date_prev.year
        prev_month = end_date_prev.month
        bio_prev_rows = df_bio[
            (df_bio["Date"].dt.year == prev_year) & (df_bio["Date"].dt.month == prev_month)
        ]
        bioetanol_previous = bio_prev_rows["HIP Bioetanol IDR/L"].mean() if not bio_prev_rows.empty else None
        tetes_previous = bio_prev_rows["Harga Tetes Tebu"].mean()    if not bio_prev_rows.empty else None
    else:
        bioetanol_previous = None
        tetes_previous = None

    def _pct(cur: float | None, prev: float | None) -> float | None:
        if cur is None or prev in (None, 0):
            return None
        return round(((cur - prev) / prev) * 100, 2)

    same_month = (
        end_date_prev is not None
        and end_date.month == end_date_prev.month
        and end_date.year  == end_date_prev.year
    )

    def _r(x: float | None) -> float | None:
        return None if x is None else round(x, 2)

    return {
        "bioetanol": _r(bioetanol_current),
        "tetes_tebu": _r(tetes_current),
        "bioetanol_change": _pct(bioetanol_current, bioetanol_previous),
        "tetes_change": _pct(tetes_current,     tetes_previous),
        "same_month": same_month,
    }


def _get_comparison_saf(
    start_date: "pd.Timestamp",
    end_date: "pd.Timestamp",
    start_date_prev: "pd.Timestamp | None",
    end_date_prev: "pd.Timestamp | None",
) -> dict:
    """
    Compute SAF and UCO averages for the current and previous periods,
    returning values and percentage changes.
    """
    df = storage.read_structured_sheet("(Data)SAF")
    if df.empty:
        return {"saf": None, "uco": None, "saf_change": None, "uco_change": None}

    df = df[["assessDate", "value_SAF", "value_UCO"]].copy()
    df["assessDate"] = pd.to_datetime(df["assessDate"]).dt.normalize()

    cur_mask = (df["assessDate"] >= start_date) & (df["assessDate"] <= end_date)
    df_cur = df.loc[cur_mask]

    saf_current = df_cur["value_SAF"].mean() if not df_cur["value_SAF"].dropna().empty else None
    uco_current = df_cur["value_UCO"].mean() if not df_cur["value_UCO"].dropna().empty else None

    if start_date_prev is not None and end_date_prev is not None:
        prev_mask = (df["assessDate"] >= start_date_prev) & (df["assessDate"] <= end_date_prev)
        df_prev = df.loc[prev_mask]
        saf_prev = df_prev["value_SAF"].mean() if not df_prev["value_SAF"].dropna().empty else None
        uco_prev = df_prev["value_UCO"].mean() if not df_prev["value_UCO"].dropna().empty else None
    else:
        saf_prev = None
        uco_prev = None

    def _pct(cur: float | None, prev: float | None) -> float | None:
        if cur is None or prev in (None, 0):
            return None
        return round(((cur - prev) / prev) * 100, 2)

    return {
        "saf": None if saf_current is None else round(saf_current, 2),
        "uco": None if uco_current is None else round(uco_current, 2),
        "saf_change": _pct(saf_current, saf_prev),
        "uco_change": _pct(uco_current, uco_prev),
    }


# Topic Processing

def process_topic(
    model,
    topic_name: str,
    config: dict,
    existing_df: pd.DataFrame,
) -> pd.DataFrame | None:
    """
    Process a single topic: determine the weekly date range, collect matching
    news from storage, optionally compute data sentiment, generate a summary,
    and return the result as a single-row DataFrame.

    Returns None if no articles are found.
    """
    print(f"\n{'=' * 60}")
    print(f"[Topic] Processing: {topic_name}")
    print(f"{'=' * 60}")

    target_sheets = config["target_sheets"]
    has_data_sentiment = config.get("has_data_sentiment", False)

    # Determine start date from the last processed date or fall back to default
    last_date = None
    if not existing_df.empty and "Tanggal akhir" in existing_df.columns:
        try:
            last_date = pd.to_datetime(existing_df["Tanggal akhir"].max())
        except Exception:
            pass

    start_date = last_date + pd.Timedelta(days=1) if last_date is not None else DEFAULT_START_DATE
    today = pd.to_datetime(datetime.now().date())
    end_date = min(start_date + pd.Timedelta(days=SUMMARY_WINDOW_DAYS), today)

    print(f"[Topic] Date range: {start_date.date()} — {end_date.date()}")
    print(f"[Topic] Fetching scraping data...")

    # Collect matching articles from each target sheet
    all_news_list: list[str] = []

    for sheet in target_sheets:
        print(f"[Topic] Reading sheet: {sheet}")
        df_news = storage.read_news_sheet(sheet)
        if not df_news.empty and "date" in df_news.columns:
            df_news["date"] = pd.to_datetime(df_news["date"], errors="coerce").dt.normalize()
            mask = (df_news["date"] >= start_date) & (df_news["date"] <= end_date)
            filtered_news = df_news[mask].sort_values("date", ascending=False)
            for _, row in filtered_news.iterrows():
                if pd.notna(row.get("content")):
                    all_news_list.append(str(row["content"]))
            print(f"  [Topic] {len(filtered_news)} article(s) from '{sheet}'.")

    if not all_news_list:
        print(f"[Topic] No new articles found for '{topic_name}'.")
        return None

    original_count = len(all_news_list)
    if original_count > MAX_NEWS_PER_TOPIC:
        all_news_list = all_news_list[:MAX_NEWS_PER_TOPIC]
        print(f"[Topic] Truncated to {MAX_NEWS_PER_TOPIC} article(s) (was {original_count}).")
    else:
        print(f"[Topic] {original_count} article(s) found.")

    summary = summarize_all_news(
        model,
        all_news_list,
        start_date,
        end_date,
        target_sheets,
        config["role_prompt"],
        config["spesific_prompt"],
    )

    # Compute data sentiment if required by this topic's config
    summary_data: str | None = None
    if has_data_sentiment and summary:
        start_prev, end_prev = _get_prev_period(existing_df)

        if topic_name == "Biodiesel":
            if start_prev and end_prev:
                comparison = _get_comparison(start_date, end_date, start_prev, end_prev)

                if comparison["same_month"]:
                    print("[Topic] Same month — copying Summary Data from previous period.")
                    try:
                        latest = _latest_row(existing_df)
                        summary_data = latest["Summary Data"] if latest is not None and "Summary Data" in existing_df.columns else None
                    except Exception:
                        summary_data = None

                elif comparison["cpo"] is None or comparison["bio"] is None:
                    print("[Topic] CPO or Biodiesel data not available.")
                    summary_data = None

                else:
                    cpo_trend = "kenaikan" if comparison["cpo_change"] >= 0 else "penurunan"
                    bio_trend = "kenaikan" if comparison["bio_change"] >= 0 else "penurunan"
                    summary_data = (
                        f"Pada periode {start_date.month}/{start_date.day}/{start_date.year} sampai "
                        f"{end_date.month}/{end_date.day}/{end_date.year}, "
                        f"rata-rata CPO {comparison['cpo']:.2f} dan rata-rata Biodiesel {comparison['bio']:.2f}. "
                        f"Periode ini mengalami {cpo_trend} {abs(comparison['cpo_change']):.2f}% nilai CPO "
                        f"dan {bio_trend} {abs(comparison['bio_change']):.2f}% biodiesel dibanding bulan sebelumnya."
                    )

        elif topic_name == "Bioetanol":
            if start_prev and end_prev:
                comparison = _get_comparison_bioetanol(start_date, end_date, start_prev, end_prev)

                if comparison["same_month"]:
                    print("[Topic] Same month — copying Summary Data from previous period.")
                    try:
                        latest = _latest_row(existing_df)
                        summary_data = latest["Summary Data"] if latest is not None and "Summary Data" in existing_df.columns else None
                    except Exception:
                        summary_data = None

                elif comparison["bioetanol"] is None or comparison["tetes_tebu"] is None:
                    print("[Topic] Bioetanol or Tetes Tebu data not available.")
                    summary_data = None

                else:
                    bioetanol_trend = "kenaikan" if comparison["bioetanol_change"] >= 0 else "penurunan"
                    tetes_trend = "kenaikan" if comparison["tetes_change"]     >= 0 else "penurunan"
                    summary_data = (
                        f"Pada bulan {end_date.strftime('%B %Y')}, "
                        f"rata-rata Bioetanol {comparison['bioetanol']:.2f} dan rata-rata Tetes Tebu {comparison['tetes_tebu']:.2f}. "
                        f"Periode ini mengalami {bioetanol_trend} {abs(comparison['bioetanol_change']):.2f}% nilai Bioetanol "
                        f"dan {tetes_trend} {abs(comparison['tetes_change']):.2f}% Tetes Tebu dibanding bulan sebelumnya."
                    )

        elif topic_name == "SAF":
            if start_prev and end_prev:
                comparison = _get_comparison_saf(start_date, end_date, start_prev, end_prev)

                def _fmt_pct(value: float | None) -> str:
                    return f"{abs(value):.2f}%" if value is not None else "N/A"

                def _trend(value: float | None) -> str:
                    if value is None:
                        return "tidak tersedia"
                    return "kenaikan" if value >= 0 else "penurunan"

                if comparison["saf"] is None or comparison["uco"] is None:
                    print("[Topic] SAF or UCO data not available.")
                    summary_data = None
                else:
                    summary_data = (
                        f"Pada periode {start_date.month}/{start_date.day}/{start_date.year} sampai "
                        f"{end_date.month}/{end_date.day}/{end_date.year}, "
                        f"rata-rata SAF tercatat {comparison['saf']:.2f} dan rata-rata UCO {comparison['uco']:.2f}. "
                        f"Secara periodik, SAF mengalami {_trend(comparison['saf_change'])} {_fmt_pct(comparison['saf_change'])} "
                        f"dan UCO mengalami {_trend(comparison['uco_change'])} {_fmt_pct(comparison['uco_change'])} dibanding periode sebelumnya."
                    )
            else:
                print("[Topic] No previous period data available.")
                summary_data = None

    if summary:
        return pd.DataFrame([{
            "Tanggal awal": start_date.date(),
            "Tanggal akhir": end_date.date(),
            "Summary": summary,
            "Summary Data": summary_data,
        }])

    return None


# Main

def main() -> None:
    """
    Run the weekly news summarization workflow with optional data sentiment:
    authenticate, load existing OneDrive sentiment data, process each active
    topic, and save the updated results back to OneDrive.
    """
    print("\n" + "=" * 60)
    print("NEWS SENTIMENT SUMMARIZATION (WEEKLY)")
    print("=" * 60)

    print("\n[Main] Setting up Gemini model...")
    model = setup_gemini()

    print(f"\n[Main] Loading existing sentiment data...")

    sheet_names = [config["output_sheet"] for config in TOPICS.values()]
    all_sheets  = storage.read_all_sentiment_sheets(sheet_names)

    # --- Summarization ---
    print("\n" + "=" * 60)
    print("STARTING SUMMARIZATION")
    print("=" * 60)

    for topic_name, config in TOPICS.items():
        try:
            output_sheet = config["output_sheet"]
            existing_df  = all_sheets.get(output_sheet, pd.DataFrame())

            print(f"\n{'-' * 60}")
            print(f"[Main] Topic: {topic_name}")
            print(f"[Main] Output sheet: {output_sheet}")
            print(f"{'-' * 60}")

            new_data = process_topic(model, topic_name, config, existing_df)

            if new_data is not None:
                if not existing_df.empty:
                    combined_df = pd.concat([existing_df, new_data], ignore_index=True)
                    print(f"\n  Existing rows: {len(existing_df)}")
                    print(f"  New rows: {len(new_data)}")
                else:
                    combined_df = new_data
                    print(f"\n  New rows: {len(new_data)}")

                all_sheets[output_sheet] = combined_df
                print(f"  Total: {len(combined_df)} row(s)")
            else:
                print("[Main] No new data for this topic.")

            print("\n[Main] Waiting 60 seconds before next topic...")
            time.sleep(60)

        except Exception as exc:
            print(f"[Main] Error processing '{topic_name}': {exc}")
            continue

    # --- Save ---
    print("\n" + "=" * 60)
    print("SAVING")
    print("=" * 60)

    try:
        storage.write_sentiment_file(all_sheets)

        print("\n" + "=" * 60)
        print("DONE!")
        print(f"[Main] Sheets: {len(all_sheets)}")
        print("=" * 60 + "\n")

    except Exception as exc:
        print(f"\n[Main] Error while saving: {exc}")
        raise


# Script Entry Point

if __name__ == "__main__":
    main()