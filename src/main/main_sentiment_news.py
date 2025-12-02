import os
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime
from openpyxl import load_workbook

EXCEL_SCRAP_PATH = "../results/(News)Scrapping.xlsx"
EXCEL_DATA_PATH = "../results/Terstruktur(Data Scrapping).xlsx"
OUTPUT_PATH = "../results/(News)Sentiment.xlsx"

TOPICS = {
    "Harga Minyak": {
        "target_sheets": ["(News)Harga Minyak"],
        "output_sheet": "(Summary)Harga Minyak",
        "has_cpo": False
    },
    "Volume Minyak": {
        "target_sheets": ["(News)Volume Minyak"],
        "output_sheet": "(Summary)Volume Minyak",
        "has_cpo": False
    },
    "Harga Produk Kilang": {
        "target_sheets": ["(News)Harga Produk Kilang"],
        "output_sheet": "(Summary)Harga Produk Kilang",
        "has_cpo": False
    },
    "Volume Produk Kilang": {
        "target_sheets": ["(News)Volume Produk Kilang"],
        "output_sheet": "(Summary)Volume Produk Kilang",
        "has_cpo": False
    },
    "Bioenergi": {
        "target_sheets": ["(News)Bioenergi"],
        "output_sheet": "(Summary)Bioenergi",
        "has_cpo": True
    }
}

def setup_gemini():
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("API key tidak ditemukan di .env")
    genai.configure(api_key=api_key)
    print("Gemini berhasil dikonfigurasi.")
    return genai.GenerativeModel("gemini-2.5-flash")

def get_last_summary_date(output_path, sheet_name):
    if not os.path.exists(output_path):
        return None
    try:
        df = pd.read_excel(output_path, sheet_name=sheet_name)
        if "Tanggal akhir" in df.columns:
            last_date = pd.to_datetime(df["Tanggal akhir"].dropna()).max()
            print(f"Tanggal terakhir summary ({sheet_name}): {last_date.date()}")
            return last_date
    except Exception as e:
        print(f"Gagal membaca {sheet_name} di {output_path}: {e}")
    return None

def collect_news_from_sheets(excel_path, target_sheets, start_date, end_date):
    all_news_list = []
    for sheet in target_sheets:
        print(f"Ambil berita sheet: {sheet}")
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet)
            df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.normalize()
            mask = (df['date'] >= start_date) & (df['date'] <= end_date)
            df_new = df.loc[mask].dropna(subset=['content'])
            all_news_list.extend(df_new['content'].tolist())
            print(f"   ✓ {len(df_new)} berita dari {sheet}")
        except Exception as e:
            print(f"Gagal baca sheet {sheet}: {e}")
    return all_news_list

def summarize_all_news(model, all_news_list, start_date, end_date, sheet_names):
    if not all_news_list:
        print("⚠️ Tidak ada berita baru dari semua sheet.")
        return {
            "Tanggal awal": start_date.date(),
            "Tanggal akhir": end_date.date(),
            "Summary": "Tidak ada berita"
        }

    all_news_text = "\n\n".join(all_news_list)

    prompt = f"""
    Kamu adalah analis energi di Indonesia.
    Berikut kumpulan berita dari topik {', '.join(sheet_names)} antara tanggal {start_date.strftime('%d %B %Y')} dan {end_date.strftime('%d %B %Y')}:

    {all_news_text}

    Buatkan 3 poin ringkasan umum.
    Semua teks pada bagian ini jangan ada yang bold, dan tolong berikan nomor setiap poinnya.

    Pada hasil summary jangan menggunakan kalimat yang berlebihan seperti "signifikan", "dahsyat", dst. 
    Serta hasil summarynya fokus pada movement data saja, serta exclude kasus-kasus hukum!

    Format jawaban:
    ===SUMMARY===
    (isi ringkasan di sini)
    """

    try:
        response = model.generate_content(prompt)
        result = response.text
        summary = result.split("===SUMMARY===")[-1].strip() if "===SUMMARY===" in result else result.strip()

        print("✅ Summary news selesai.")
        return {
            "Tanggal awal": start_date.date(),
            "Tanggal akhir": end_date.date(),
            "Summary": summary
        }
    except Exception as e:
        print(f"❌ Gagal generate summary: {e}")
        return None

def get_cpo_analysis(model, start_date, end_date):
    try:
        df = pd.read_excel(EXCEL_DATA_PATH, sheet_name="(Data)CPO", usecols=["Dates", "PX_LAST"])
        df["Dates"] = pd.to_datetime(df["Dates"]).dt.normalize()
        mask = (df["Dates"] >= start_date) & (df["Dates"] <= end_date)
        df = df[mask]
        if df.empty:
            print("Tidak ada data CPO untuk rentang tanggal ini")
            return None
        print(f"Data CPO ditemukan: {len(df)} rows")
        data_text = "\n".join([f"{row['Dates'].strftime('%Y-%m-%d')}: {row['PX_LAST']}" for _, row in df.iterrows()])
        prompt = f"""
        Buat ringkasan analisis tren harga CPO berikut ini, dalam 1 kalimat singkat saja. 
        Tunjukkan insight, tren naik/turun, dan highlight pergerakan penting.
        Data:
        {data_text}
        Semua teks pada bagian ini jangan ada yang bold.
        """
        response = model.generate_content(prompt)
        summary_text = response.text.strip()
        print("Analisis CPO selesai.")
        return summary_text
    except Exception as e:
        print(f"Error saat memproses CPO: {e}")
        return None

def save_to_excel_with_cpo(new_data, output_path, sheet_name, cpo_analysis=None):
    if not new_data:
        print("Tidak ada summary yang dihasilkan.")
        return
    new_df = pd.DataFrame(new_data)
    if cpo_analysis is not None:
        new_df["Summary Data"] = cpo_analysis
    if os.path.exists(output_path):
        book = load_workbook(output_path)
        try:
            existing_df = pd.read_excel(output_path, sheet_name=sheet_name)
            for col in ["Tanggal awal", "Tanggal akhir"]:
                if col in existing_df.columns:
                    existing_df[col] = pd.to_datetime(existing_df[col]).dt.date
            if cpo_analysis is not None and "Summary Data" not in existing_df.columns:
                existing_df["Summary Data"] = None
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            print(f"Menambahkan summary baru ke sheet '{sheet_name}'.")
        except Exception:
            combined_df = new_df
            print(f"Sheet '{sheet_name}' belum ada, membuat baru.")
        with pd.ExcelWriter(output_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            writer._book = book
            combined_df.to_excel(writer, index=False, sheet_name=sheet_name)
    else:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            new_df.to_excel(writer, index=False, sheet_name=sheet_name)
    print(f"Data berhasil disimpan ke {output_path} - {sheet_name}")

def process_topic(model, topic_name, config):
    print(f"\n{'='*60}")
    print(f"🔄 Memproses topik: {topic_name}")
    print(f"{'='*60}")
    target_sheets = config["target_sheets"]
    output_sheet = config["output_sheet"]
    has_cpo = config.get("has_cpo", False)
    last_date = get_last_summary_date(OUTPUT_PATH, output_sheet)
    if last_date is not None:
        start_date = last_date + pd.Timedelta(days=1)
    else:
        start_date = datetime(2025, 1, 1)
    end_date = pd.to_datetime("2025-11-25")
    print(f"Akan proses berita dari {start_date.date()} sampai {end_date.date()}")
    all_news_list = collect_news_from_sheets(EXCEL_SCRAP_PATH, target_sheets, start_date, end_date)
    if not all_news_list:
        print(f"⚠️ Tidak ada berita baru untuk {topic_name}")
        return
    print(f"Total berita ditemukan: {len(all_news_list)}")
    summary = summarize_all_news(model, all_news_list, start_date, end_date, target_sheets)
    cpo_analysis = None
    if has_cpo and summary:
        print(f"\nMengambil data CPO untuk rentang tanggal yang sama...")
        cpo_analysis = get_cpo_analysis(model, start_date, end_date)
    if summary:
        save_to_excel_with_cpo([summary], OUTPUT_PATH, output_sheet, cpo_analysis)
def main():
    print("Memulai proses summarization untuk semua topik...\n")
    model = setup_gemini()
    for topic_name, config in TOPICS.items():
        try:
            process_topic(model, topic_name, config)
        except Exception as e:
            print(f"❌ Error saat memproses {topic_name}: {e}")
            continue
    
    print(f"\n{'='*60}")
    print("✅ Semua proses selesai!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()