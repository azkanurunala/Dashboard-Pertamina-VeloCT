import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv
import google.generativeai as genai

def setup_gemini():
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    api_key = os.getenv('GEMINI_API_KEY')
    try:
        if not api_key:
            raise ValueError("API key tidak ditemukan di file .env")
        genai.configure(api_key=api_key)
        print("✅ Klien Gemini berhasil dikonfigurasi.")
        return genai.GenerativeModel("gemini-2.5-flash")
    except Exception as e:
        print(f"❌ Gagal inisialisasi Gemini: {e}")
        exit()

def get_last_analysis_date(sentiment_file, sheet_name):
    if os.path.exists(sentiment_file):
        xl = pd.ExcelFile(sentiment_file)
        if sheet_name in xl.sheet_names:
            df = pd.read_excel(sentiment_file, sheet_name=sheet_name)
            if not df.empty:
                return pd.to_datetime(df["Tanggal akhir"].max()), df
    return None, pd.DataFrame(columns=["Tanggal awal", "Tanggal akhir", "Summary"])

def get_new_cpo_data(source_file, source_sheet, date_col="Dates", price_col="PX_LAST", last_date=None):
    df = pd.read_excel(source_file, sheet_name=source_sheet, usecols=[date_col, price_col])
    df[date_col] = pd.to_datetime(df[date_col])
    today = pd.Timestamp.today().normalize()
    if last_date is not None:
        df = df[df[date_col] > last_date]
    df = df[df[date_col] <= today]
    return df

def analyze_trend_with_gemini(model, df, date_col="Dates", price_col="PX_LAST"):
    if df.empty:
        return None

    data_text = "\n".join([f"{row[date_col].strftime('%Y-%m-%d')}: {row[price_col]}" for _, row in df.iterrows()])
    prompt = (f'''
        Buat ringkasan analisis tren harga CPO berikut ini, dalam 1 kalimat singkat saja. 
        Tunjukkan insight, tren naik/turun, dan highlight pergerakan penting.\n\nData:\n{data_text}
        Semua teks pada bagian ini jangan ada yang bold.'''
    )

    response = model.generate_content(prompt)
    summary_text = response.text.strip()

    df[date_col] = pd.to_datetime(df[date_col]).dt.normalize()
    tanggal_awal = df[date_col].min().date()
    tanggal_akhir = df[date_col].max().date()

    summary_df = pd.DataFrame({
        "Tanggal awal": [tanggal_awal],
        "Tanggal akhir": [tanggal_akhir],
        "Summary": [summary_text]
    })
    return summary_df

def save_summary_to_excel(summary_df, sentiment_file="../results/(Data)Sentiment.xlsx", sheet_name="(Summary)CPO", old_df=None):
    if summary_df is None or summary_df.empty:
        print("Tidak ada data baru untuk disimpan.")
        return

    if old_df is not None and not old_df.empty:
        final_df = pd.concat([old_df, summary_df], ignore_index=True)
    else:
        final_df = summary_df

    for col in ["Tanggal awal", "Tanggal akhir"]:
        if col in final_df.columns:
            final_df[col] = pd.to_datetime(final_df[col], errors='coerce').dt.strftime("%Y-%m-%d")

    if os.path.exists(sentiment_file):
        with pd.ExcelWriter(sentiment_file, mode="a", engine="openpyxl", if_sheet_exists="overlay") as writer:
            final_df.to_excel(writer, index=False, sheet_name=sheet_name)
    else:
        final_df.to_excel(sentiment_file, index=False, sheet_name=sheet_name)

    print(f"✅ Analisis baru berhasil ditambahkan ke file {sentiment_file}")


def run_cpo_analysis():
    sentiment_file = "../results/Terstruktur(Data Scrapping).xlsx"
    source_file = "../results/Terstruktur(Data Scrapping).xlsx"
    source_sheet = "(Data)CPO"
    output_sheet = "(Data)Summary CPO"

    model = setup_gemini()
    last_date, old_df = get_last_analysis_date(sentiment_file, output_sheet)
    print(f"Tanggal terakhir analisis: {last_date}")
    new_data = get_new_cpo_data(source_file, source_sheet, last_date=last_date)
    print("New Data")
    print(new_data)
    summary_df = analyze_trend_with_gemini(model, new_data)
    save_summary_to_excel(summary_df, sentiment_file, output_sheet, old_df)
    if summary_df is not None:
        print(summary_df)

if __name__ == "__main__":
    run_cpo_analysis()
