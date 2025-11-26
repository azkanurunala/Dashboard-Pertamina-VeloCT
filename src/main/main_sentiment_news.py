import os
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime
from openpyxl import load_workbook

EXCEL_SCRAP_PATH = "../results/(News)Scrapping.xlsx"
OUTPUT_PATH = "../results/(News)Sentiment.xlsx"
TOPICS = {
    "Harga Minyak": {
        "target_sheets": ["(News)Harga Minyak"],
        "output_sheet": "(Summary)Harga Minyak"
    },
    "Volume Minyak": {
        "target_sheets": ["(News)Volume Minyak"],
        "output_sheet": "(Summary)Volume Minyak"
    },
    "Harga Produk Kilang": {
        "target_sheets": ["(News)Harga Produk Kilang"],
        "output_sheet": "(Summary)Harga Produk Kilang"
    },
    "Volume Produk Kilang": {
        "target_sheets": ["(News)Volume Produk Kilang"],
        "output_sheet": "(Summary)Volume Produk Kilang"
    },
    "Bioenergi": {
        "target_sheets": ["(News)Bioenergi"],
        "output_sheet": "(Summary)Bioenergi"
    }
}
def setup_gemini():
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("API key tidak ditemukan di .env")
    genai.configure(api_key=api_key)
    print("✅ Gemini berhasil dikonfigurasi.")
    return genai.GenerativeModel("gemini-2.5-flash")

def get_last_summary_date(output_path, sheet_name):
    """Ambil tanggal terakhir dari summary yang sudah ada"""
    if not os.path.exists(output_path):
        return None
    try:
        df = pd.read_excel(output_path, sheet_name=sheet_name)
        if "Tanggal akhir" in df.columns:
            last_date = pd.to_datetime(df["Tanggal akhir"].dropna()).max()
            print(f"📅 Tanggal terakhir summary ({sheet_name}): {last_date.date()}")
            return last_date
    except Exception as e:
        print(f"⚠️ Gagal membaca {sheet_name} di {output_path}: {e}")
    return None

def collect_news_from_sheets(excel_path, target_sheets, start_date, end_date):
    """Kumpulkan berita dari sheets yang ditargetkan"""
    all_news_list = []
    for sheet in target_sheets:
        print(f"📄 Ambil berita sheet: {sheet}")
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet)
            df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.normalize()
            mask = (df['date'] >= start_date) & (df['date'] <= end_date)
            df_new = df.loc[mask].dropna(subset=['content'])
            all_news_list.extend(df_new['content'].tolist())
            print(f"   ✓ {len(df_new)} berita dari {sheet}")
        except Exception as e:
            print(f"⚠️ Gagal baca sheet {sheet}: {e}")
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

        print("✅ Summary selesai.")
        return {
            "Tanggal awal": start_date.date(),
            "Tanggal akhir": end_date.date(),
            "Summary": summary
        }
    except Exception as e:
        print(f"❌ Gagal generate summary: {e}")
        return None

def save_to_excel(new_data, output_path, sheet_name):
    """Simpan summary ke Excel"""
    if not new_data:
        print("⚠️ Tidak ada summary yang dihasilkan.")
        return

    new_df = pd.DataFrame(new_data)

    if os.path.exists(output_path):
        book = load_workbook(output_path)
        try:
            existing_df = pd.read_excel(output_path, sheet_name=sheet_name)

            # Konversi kolom tanggal lama agar hanya tanggal tanpa jam
            for col in ["Tanggal awal", "Tanggal akhir"]:
                if col in existing_df.columns:
                    existing_df[col] = pd.to_datetime(existing_df[col]).dt.date

            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            print(f"📎 Menambahkan summary baru ke sheet '{sheet_name}'.")
        except Exception:
            combined_df = new_df
            print(f"📄 Sheet '{sheet_name}' belum ada, membuat baru.")
        
        with pd.ExcelWriter(output_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            writer._book = book
            combined_df.to_excel(writer, index=False, sheet_name=sheet_name)
    else:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            new_df.to_excel(writer, index=False, sheet_name=sheet_name)

    print(f"💾 Data berhasil disimpan ke {output_path} - {sheet_name}")

def process_topic(model, topic_name, config):
    """Proses satu topik (Energi Fosil atau Bioenergi)"""
    print(f"\n{'='*60}")
    print(f"🔄 Memproses topik: {topic_name}")
    print(f"{'='*60}")
    
    target_sheets = config["target_sheets"]
    output_sheet = config["output_sheet"]
    
    # Ambil tanggal terakhir summary
    last_date = get_last_summary_date(OUTPUT_PATH, output_sheet)
    if last_date is not None:
        start_date = last_date + pd.Timedelta(days=1)
    else:
        start_date = datetime(2025, 1, 1)
    #end_date = pd.to_datetime(datetime.now()).normalize()
    end_date = pd.to_datetime("2025-11-25")

    print(f"🕒 Akan proses berita dari {start_date.date()} sampai {end_date.date()}")
    
    # Kumpulkan berita
    all_news_list = collect_news_from_sheets(EXCEL_SCRAP_PATH, target_sheets, start_date, end_date)
    
    if not all_news_list:
        print(f"⚠️ Tidak ada berita baru untuk {topic_name}")
    
    print(f"📊 Total berita ditemukan: {len(all_news_list)}")
    
    # Generate summary
    summary = summarize_all_news(model, all_news_list, start_date, end_date, target_sheets)
    
    # Simpan ke Excel
    if summary:
        save_to_excel([summary], OUTPUT_PATH, output_sheet)

def main():
    """Fungsi utama untuk memproses semua topik"""
    print("🚀 Memulai proses summarization untuk semua topik...\n")
    
    # Setup Gemini
    model = setup_gemini()
    
    # Proses setiap topik
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