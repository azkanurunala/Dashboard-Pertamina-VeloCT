import os
import re
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.onedrive_helper import (
    get_access_token,
    read_excel_sheet_from_onedrive,
    write_multiple_sheets_to_onedrive,
    download_excel_from_onedrive,
)

from code_scrapping.bisnis_indonesia import main_bisnis_indonesia
from code_scrapping.bloomberg_technoz import main_bloomberg_technoz
from code_scrapping.bank_indonesia import main_bank_indonesia
from code_scrapping.bps import main_bps
from code_scrapping.cnbc import main_google_news_cnbc
from code_scrapping.cnbc_id import main_cnbc
from code_scrapping.cnn import main_google_news_cnn
from code_scrapping.kompas import main_kompas
from code_scrapping.kontan import scrape_kontan
from code_scrapping.kontan_bbm import scrape_kontan_bbm
from code_scrapping.kontan_biodiesel import scrape_kontan_biodiesel
from code_scrapping.oilprice import scrape_oilprice
from code_scrapping.scrape_sandp_news import scrape_spglobal
from code_scrapping.tempo import scrape_tempo

load_dotenv()

# Config

ONEDRIVE_FILE_PATH = os.getenv("ONEDRIVE_FILE_PATH", "/results/(News)Scrapping_new.xlsx")

# Keyword synonyms — add/remove entries to control what gets searched

SINONIM_DICT = {
    # "indeks risiko geopolitik ": ["tekanan geopolitik ", "geopolitik "],
    # "indeks volatilitas ": ["volatilitas "],
    # "kurs ": [
    #     "nilai tukar rupiah ", 
    #     "dolar ", 
    #     "kurs rupiah ", "kurs dolar ",
    #     ],
    # "ihsg ": ["pasar saham "],
    # "inflasi ": [],
    # "bi rate ": ["suku bunga ", "bunga bi "],
    # "indonia ": [],
    # "indeks sales retail ": [
    #     "indeks penjualan ritel ", "indeks ritel "
    #     "indeks penjualan retail ", "indeks retail ", 
    #     "survei penjualan eceran "
    #     ],
    # "indeks kepercayaan konsumen ": [
    #     "indeks kepercayaan pelanggan ", "ekspektasi konsumen ", 
    #     # "kondisi ekonomi terkini ", "kepercayaan konsumen ", "kondisi ekonomi saat ini ",
    #     "indeks keyakinan konsumen ", "survei konsumen bi ", "keyakinan konsumen "],
    # "indeks kinerja manufaktur ": [
    #     "kinerja manufaktur ",
    #     "pmi manufaktur ", "pmi indonesia "
    #     ],
    # "indeks kinerja jasa ": [
    #     "kinerja jasa ",
    #     "pmi jasa ", "pmi sektor jasa "
    #     ],
    # "neraca perdagangan ": [
    #     "trade balance ",
    #     "neraca dagang "
    #     ],
    # "pertumbuhan domestik bruto ": [
    #     "PDB ", "pertumbuhan ekonomi ",
    #     "produk domestik bruto "
    #     ],
    # "biodiesel ": [
    #     "minyak kelapa sawit ", "crude palm oil ", "CPO ", "minyak sawit ", "kelapa sawit ", "sawit ",
    #     "HIP BBN Biodesel ", "biodiesel ", "harga fame ", "harga indeks pasar biodiesel ", "b40 ", "b50 ", "biodiesel ", "biofuel "
    #     ],
    "bioetanol ": [
        "tebu ", 
        "gula ", # just for bisnis indonesia, kecuali lifestyle.bisnis.com
        "molase ", "etanol ", "ethanol ", "bioethanol ", "tetes tebu ",
        "gula tebu ", "industri gula "
        ],
    # "RUPTL ": [
    #     # "listrik ", "transmisi ", "distribusi ", 
    #     "PLN ", "IPP ", "PJBL ", "pembangkit ", "ketenagalistrikan ", 
    #     "elektrifikasi ", "batubara ", "batu bara ", "panas bumi ",
    #     "surya ", "nuklir ", "BESS ", "PLTA ", "PLTAL ", "PLTB ", "PLTBg ", "PLTBm ", "PLTD ", "PLTG ",
    #     "PLTGU ", "PLTM ", "PLTMG ", "PLTN ", "PLTP ", "PLTS ", "PLTSa ", "PLTU ",
    #     "transmisi listrik ", "transmisi tenaga listrik "
    #     ],
    # "harga minyak ": [
    #     "minyak mentah ",
    #     "harga minyak mentah ", "icp ", "wti ", "brent "
    #     ],
    # "volume minyak ": [
    #     "volume bbm ", "minyak mentah ",
    #     "lifting minyak ", "produksi minyak ", "impor minyak mentah "
    #     ],
    # "harga produk kilang pertamina ": [
    #     "bbm ", "harga kilang pertamina ", "kilang pertamina ", "kilang ", "refinery ", "harga pertamina ",
    #     "harga bbm pertamina ", "harga pertamax ", "harga pertalite ", "harga solar ", "harga avtur ", "rdmp "
    #     ],
    # "volume produk kilang pertamina ": [
    #     "bbm ", "volume kilang pertamina ", "volume kilang ", "refinery ", "volume pertamina ",
    #     "kilang pertamina ", "produksi bbm ", "rdmp ", "kapasitas kilang ", "kilang balikpapan ", "kilang tuban ", "impor bbm "
    #     ],
    # "SAF ": [
    #     "UCO ", "CORSIA ", "SAFCo ", "biorefinery ", "minyak jelantah ", "bioavtur ",
    #     "bioavtur pertamina", "pome",
    #     ],
    # "RON 92 ": [
    #     "pertamax ", "RON 95 ", "RON 97 ", "Residual FO ", "Fuel Oil", "Jet Fuel ", "Avtur ",
    #     "Kerosene ", "refinery ", "refined products ", "refining ", "oil products ", "Gasoline ",
    #     "Heavy Oil ", "Diesel ", "Gasoil ", "Naphtha ", "LPG ", "Biodiesel ", "Biogasoline ",
    #     "Petroleum Coke ", "Oil price ", 
    #     # "Fuel ",
    #     "harga minyak ", "fuel cost ", "fuel price "
    # ],
    # "Petrochemical ": [
    #     "chemical ", "aromatic ", "olefin ", "polymer ", "LPG ",
    #     "Paraxylene ", "Propylene ", "Benzene ", "Green Coke ",
    #     "petrochemicals ", "petrokimia ", "petrochemical complex ", 
    #     "aromatic compound ", "BTX aromatic ", "senyawa aromatik ", 
    #     "green petroleum coke ", "petroleum coke "
    # ],
    # "LCOE ": [
    #     "harga jual listrik EBT ", "harga listrik EBT ", "tarif listrik EBT "
    #     ],
    # "WTE ": [
    #     "waste to energy ", 
    #     # "sampah ", # kecuali foto.bisnis.com and hijau.bisnis.com
    #     "sampah jadi listrik ", "sampah jadi energi ", "insinerator ", "PSEL "
    #     ],
    # "Pembangkit listrik nuklir ": [
    #     "reaktor nuklir ", "energi nuklir "
    #     ],
}

# Ketenagalistrikan, energi baru dan terbarukan sub-category keyword filters

EBT_KEYWORDS = [
    "PLTA ", "PLTS ", "PLTB ", "BESS ", "PLTBm ", "panas bumi ", "PLTP ", "PLTBg ",
    "listrik ", "PLN ", "IPP ", "PJBL ", "pembangkit ", "ketenagalistrikan ",
    "transmisi ", "distribusi ", "elektrifikasi ",
]
WTE_KEYWORDS = ["PLTSa "]
NUKLIR_KEYWORDS = ["nuklir ", "PLTN "]

# Scraping sources per keyword

SUMBER_DICT = {
    # "indeks risiko geopolitik ": [main_bloomberg_technoz],
    # "indeks volatilitas ": [main_bloomberg_technoz],
    # "kurs ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    # "ihsg ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    # "inflasi ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc, main_bps],
    # "bi rate ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc, main_bank_indonesia],
    # "indonia ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc, main_bank_indonesia],
    # "indeks sales retail ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc, main_bank_indonesia],
    # "indeks kepercayaan konsumen ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc, main_bank_indonesia],
    # "indeks kinerja manufaktur ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    # "indeks kinerja jasa ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    # "neraca perdagangan ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc, main_bps],
    # "pertumbuhan domestik bruto ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc, main_bps],
    # "biodiesel ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    "bioetanol ": [
        # scrape_kontan_biodiesel, main_bisnis_indonesia, 
        main_bloomberg_technoz],
    # "RUPTL ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    # "harga minyak ": [scrape_kontan_bbm, main_bisnis_indonesia, main_bloomberg_technoz],
    # "volume minyak ": [scrape_kontan_bbm, main_bisnis_indonesia, main_bloomberg_technoz],
    # "harga produk kilang pertamina ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    # "volume produk kilang pertamina ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    # "SAF ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    # "RON 92 ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    # "Petrochemical ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    # "LCOE ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    # "WTE ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    # "Pembangkit listrik nuklir ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
}

# Sheet name → keyword mapping

SHEET_TO_KEYWORD = {
    # "(News)indeks risiko geopolitik": "indeks risiko geopolitik ",
    # "(News)indeks volatilitas": "indeks volatilitas ",
    # "(News)Kurs": "kurs ",
    # "(News)IHSG": "ihsg ",
    # "(News)Inflasi": "inflasi ",
    # "(News)BI Rate": "bi rate ",
    # "(News)Indonia": "indonia ",
    # "(News)indeks sales retail": "indeks sales retail ",
    # "(News)indeks kepercayaan knsmn": "indeks kepercayaan konsumen ",
    # "(News)indeks kinerja manufaktur": "indeks kinerja manufaktur ",
    # "(News)indeks kinerja jasa": "indeks kinerja jasa ",
    # "(News)neraca perdagangan": "neraca perdagangan ",
    # "(News)PDB": "pertumbuhan domestik bruto ",
    # "(News)Biodiesel": "biodiesel ",
    "(News)Bioetanol": "bioetanol ",
    # "(News)RUPTL": "RUPTL ",
    # "(News)Harga Minyak": "harga minyak ",
    # "(News)Volume Minyak": "volume minyak ",
    # "(News)Harga Produk Kilang": "harga produk kilang pertamina ",
    # "(News)Volume Produk Kilang": "volume produk kilang pertamina ",
    # "(News)SAF": "SAF ",
    # "(News)Crackspread_BBM": "RON 92 ",
    # "(News)Crackspread_NonBBM": "Petrochemical ",
    # "(News)Harga EBT": "LCOE ",
    # "(News)Harga WTE": "WTE ",
    # "(News)Nuklir": "Pembangkit listrik nuklir ",
}

# Sheets to process (must match keys in SHEET_TO_KEYWORD)
ACTIVE_SHEETS = [
    # "(News)indeks risiko geopolitik",
    # "(News)indeks volatilitas",
    # "(News)Kurs",
    # "(News)IHSG",
    # "(News)Inflasi",
    # "(News)BI Rate",
    # "(News)Indonia",
    # "(News)indeks sales retail",
    # "(News)indeks kepercayaan knsmn",
    # "(News)indeks kinerja manufaktur",
    # "(News)indeks kinerja jasa",
    # "(News)neraca perdagangan",
    # "(News)PDB",
    # "(News)Biodiesel",
    "(News)Bioetanol",
    # "(News)RUPTL",
    # "(News)Harga Minyak",
    # "(News)Volume Minyak",
    # "(News)Harga Produk Kilang",
    # "(News)Volume Produk Kilang",
    # "(News)SAF",
    # "(News)Crackspread_BBM",
    # "(News)Crackspread_NonBBM",
    # "(News)Harga EBT",
    # "(News)Harga WTE",
    # "(News)Nuklir",
]

# Canonical source name overrides
SOURCE_NAME_MAP = {
    "KONTAN_BBM": "KONTAN",
    "KONTAN_BIODIESEL": "KONTAN",
    "GOOGLE_NEWS_CNN": "CNN",
    "GOOGLE_NEWS_CNBC": "CNBC",
    "NEWS_SAP": "S&P",
}

# Column rename map for standardization
COLUMN_RENAME_MAP = {
    "Judul": "title",
    "judul": "title",
    "Title": "title",
    "Tanggal": "date",
    "tanggal": "date",
    "Date": "date",
    "Link": "url",
    "link": "url",
    "URL": "url",
    "Konten": "content",
    "konten": "content",
    "Content": "content",
}

REQUIRED_COLUMNS = ["title", "date", "url", "content"]
COLUMN_ORDER = ["title", "date", "url", "content", "source", "keyword"]
EMPTY_DF = pd.DataFrame(columns=COLUMN_ORDER)

# Helpers

def _clean_date(date_str) -> str:
    """Normalize a date value to YYYY-MM-DD or 'N/A'."""
    if pd.isna(date_str) or date_str in ("N/A", "-"):
        return "N/A"
    date_str = str(date_str).strip().split("T")[0].split(" ")[0]
    return date_str if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str) else "N/A"


def standardize_format(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns, fill missing required columns, and normalize dates."""
    if df is None or df.empty:
        return EMPTY_DF.copy()

    df = df.rename(columns=COLUMN_RENAME_MAP)

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = "N/A"

    df["date"] = df["date"].apply(_clean_date)

    existing_cols = [col for col in COLUMN_ORDER if col in df.columns]
    return df[existing_cols]


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop duplicate rows based on URL."""
    if df.empty:
        return df
    return df.drop_duplicates(subset=["url"], keep="first")


def _filter_by_keywords(df: pd.DataFrame, keywords: list[str]) -> pd.DataFrame:
    """Return rows whose 'keyword' column matches any of the given keywords."""
    if df is None or df.empty:
        return EMPTY_DF.copy()
    pattern = "|".join(keywords)
    mask = df["keyword"].str.contains(pattern, case=False, na=False)
    return df[mask].copy()


def filter_ebt_from_ruptl(df: pd.DataFrame) -> pd.DataFrame:
    return _filter_by_keywords(df, EBT_KEYWORDS)


def filter_wte_from_ruptl(df: pd.DataFrame) -> pd.DataFrame:
    return _filter_by_keywords(df, WTE_KEYWORDS)


def filter_nuklir_from_ruptl(df: pd.DataFrame) -> pd.DataFrame:
    return _filter_by_keywords(df, NUKLIR_KEYWORDS)

# Core scraping logic

def scrape_keyword(keyword: str, tanggal_filter: str) -> pd.DataFrame:
    """Scrape all synonyms of a keyword from all configured sources."""
    hasil_final = pd.DataFrame()
    semua_keyword = [keyword] + SINONIM_DICT.get(keyword, [])
    sumber = SUMBER_DICT.get(keyword, [main_kompas, main_bisnis_indonesia, scrape_tempo, scrape_kontan])

    for kata in semua_keyword:
        print(f"\n  Kata kunci: '{kata}'")
        hasil_list = []

        for scrape_func in sumber:
            raw_name = scrape_func.__name__.replace("scrape_", "").replace("main_", "").upper()
            nama_sumber = SOURCE_NAME_MAP.get(raw_name, raw_name)
            print(f"    Scraping dari {nama_sumber}...")

            try:
                data = scrape_func(kata, tanggal_filter)
                if isinstance(data, pd.DataFrame):
                    df_temp = data
                elif data:
                    df_temp = pd.DataFrame(data)
                else:
                    df_temp = pd.DataFrame()

                if not df_temp.empty:
                    df_temp["source"] = nama_sumber
                    df_temp = standardize_format(df_temp)
                    hasil_list.append(df_temp)
                    print(f"    {len(df_temp)} berita dari {nama_sumber}")
                else:
                    print(f"    Tidak ada berita dari {nama_sumber}")

            except Exception as e:
                print(f"    Gagal scrape {nama_sumber}: {e}")

        if hasil_list:
            df_kata = pd.concat(hasil_list, ignore_index=True)
            df_kata["keyword"] = kata
            hasil_final = pd.concat([hasil_final, df_kata], ignore_index=True)

    return hasil_final if not hasil_final.empty else EMPTY_DF.copy()

# Main

def main():
    print("\n" + "=" * 60)
    print("NEWS SCRAPING TO ONEDRIVE")
    print("=" * 60)

    print("\nAuthenticating to Microsoft Graph API...")
    try:
        access_token = get_access_token()
        print("Authentication successful")
    except Exception as e:
        print(f"Authentication failed: {e}")
        return

    tanggal_filter = None
    # tanggal_filter = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"\nTanggal filter: {tanggal_filter}")

    # --- Load existing sheets from OneDrive ---
    print(f"\nLoading existing data from OneDrive...")
    print(f"File: {ONEDRIVE_FILE_PATH}")

    excel_buffer = download_excel_from_onedrive(access_token, ONEDRIVE_FILE_PATH)
    all_sheets: dict[str, pd.DataFrame] = {}

    if excel_buffer is None:
        print("File tidak ditemukan, akan membuat file baru")
        for sheet_name in ACTIVE_SHEETS:
            all_sheets[sheet_name] = pd.DataFrame()
    else:
        print("File ditemukan, membaca semua sheets...")
        excel_buffer.seek(0)
        excel_file = pd.ExcelFile(excel_buffer)

        for sheet_name in ACTIVE_SHEETS:
            try:
                if sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    all_sheets[sheet_name] = df
                    print(f"  '{sheet_name}': {len(df)} baris")
                else:
                    print(f"  '{sheet_name}': tidak ada, akan dibuat baru")
                    all_sheets[sheet_name] = pd.DataFrame()
            except Exception as e:
                print(f"  '{sheet_name}': error ({e}), akan dibuat baru")
                all_sheets[sheet_name] = pd.DataFrame()

        excel_file.close()

    # --- Scraping ---
    print("\n" + "=" * 60)
    print("MULAI SCRAPING")
    print("=" * 60)

    hasil_ruptl: pd.DataFrame | None = None

    for sheet_name in ACTIVE_SHEETS:
        keyword_asli = SHEET_TO_KEYWORD.get(sheet_name)
        if not keyword_asli:
            print(f"\nKeyword untuk '{sheet_name}' tidak ditemukan di mapping. Lewati.")
            continue

        print(f"\n{'-' * 60}")
        print(f"Sheet  : {sheet_name}")
        print(f"Keyword: {keyword_asli}")
        print(f"{'-' * 60}")

        hasil_df = scrape_keyword(keyword_asli, tanggal_filter)

        # Cache RUPTL results for downstream sheets
        if sheet_name == "(News)RUPTL":
            hasil_ruptl = hasil_df.copy()

        # Enrich EBT / WTE / Nuklir sheets with RUPTL sub-categories
        ruptl_filters = {
            "(News)Harga EBT": (filter_ebt_from_ruptl, "EBT"),
            "(News)Harga WTE": (filter_wte_from_ruptl, "WTE"),
            "(News)Nuklir": (filter_nuklir_from_ruptl, "Nuklir"),
        }

        if sheet_name in ruptl_filters:
            filter_fn, label = ruptl_filters[sheet_name]
            print(f"\n  Menambahkan filter {label} dari hasil RUPTL...")
            if hasil_ruptl is not None and not hasil_ruptl.empty:
                filtered = filter_fn(hasil_ruptl)
                print(f"  Hasil filter {label} dari RUPTL: {len(filtered)} baris")
                hasil_df = pd.concat([hasil_df, filtered], ignore_index=True)
            else:
                print(f"  Tidak ada data RUPTL untuk difilter")

        # Merge with existing data and deduplicate
        existing = all_sheets.get(sheet_name, pd.DataFrame())
        if not existing.empty:
            combined_df = pd.concat([existing, hasil_df], ignore_index=True)
            print(f"\n  Data existing : {len(existing)} baris")
            print(f"  Data baru     : {len(hasil_df)} baris")
        else:
            combined_df = hasil_df
            print(f"\n  Data baru: {len(hasil_df)} baris")

        combined_df = remove_duplicates(combined_df)
        all_sheets[sheet_name] = combined_df
        print(f"  Total (setelah deduplikasi): {len(combined_df)} baris")

        if sheet_name != "(News)Harga EBT":
            print("\nIstirahat 60 detik...")
            # time.sleep(60)

    # --- Save to OneDrive ---
    print("\n" + "=" * 60)
    print("MENYIMPAN KE ONEDRIVE")
    print("=" * 60)

    try:
        print("\nMendapatkan fresh token untuk menyimpan...")
        access_token = get_access_token()
        write_multiple_sheets_to_onedrive(access_token, ONEDRIVE_FILE_PATH, all_sheets)

        print("\n" + "=" * 60)
        print("SELESAI!")
        print(f"File  : {ONEDRIVE_FILE_PATH}")
        print(f"Sheets: {len(ACTIVE_SHEETS)}")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\nError saat menyimpan: {e}")
        raise


if __name__ == "__main__":
    main()