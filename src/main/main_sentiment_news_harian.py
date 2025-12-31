import os
import time
import pandas as pd
import sys
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers.summary_helper import (
    setup_gemini, summarize_all_news
)
from helpers.onedrive_helper import (
    get_access_token,
    write_multiple_sheets_to_onedrive,
    download_excel_from_onedrive
)

load_dotenv()

ONEDRIVE_SCRAP_PATH = os.getenv("ONEDRIVE_FILE_PATH", "/results/(News)Scrapping.xlsx")
ONEDRIVE_SENTIMENT_PATH = "/results/(News)Sentiment.xlsx"

TOPICS = {
   
    "Indeks Volatilitas": {
        "target_sheets": ["(News)indeks volatilitas"],
        "output_sheet": "(Summary)Idx Volatilitas",
        "role_prompt" : "industri minyak dan gas",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
    },

    "Nilai Tukar Rupiah": {
        "target_sheets": ["(News)Kurs"],
        "output_sheet": "(Summary)Nilai Tukar Rupiah",
        "role_prompt" : "industri minyak dan gas",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
    },

    "IHSG": {
        "target_sheets": ["(News)IHSG"],
        "output_sheet": "(Summary)IHSG",
        "role_prompt" : "industri minyak dan gas",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
    },

    "JIBOR": {
        "target_sheets": ["(News)JIBOR"],
        "output_sheet": "(Summary)JIBOR",
        "role_prompt" : "industri minyak dan gas",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
    }
}

def process_topic(model, topic_name, config, existing_df, access_token):
    print(f"\n{'='*60}")
    print(f"🔄 Memproses topik: {topic_name}")
    print(f"{'='*60}")
    target_sheets = config["target_sheets"]
    output_sheet = config["output_sheet"]

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
        start_date = datetime(2025, 1, 1)
    end_date = start_date

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
            df_news = pd.read_excel(excel_file, sheet_name=sheet)
            # Filter by date
            if not df_news.empty and "date" in df_news.columns:
                df_news["date"] = pd.to_datetime(df_news["date"], errors='coerce')
                mask = (df_news["date"] >= start_date) & (df_news["date"] <= end_date)
                filtered_news = df_news[mask]

                # Collect content
                for _, row in filtered_news.iterrows():
                    if pd.notna(row.get("content")):
                        all_news_list.append(str(row["content"]))

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

    if summary:
        new_data = {
            "Tanggal awal": start_date.date(),
            "Tanggal akhir": end_date.date(),
            "Summary": summary
        }
        return pd.DataFrame([new_data])

    return None

def main():
    print("\n" + "="*60)
    print("NEWS SENTIMENT SUMMARIZATION TO ONEDRIVE")
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