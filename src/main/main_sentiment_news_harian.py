import os
import time
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime
from openpyxl import load_workbook

EXCEL_SCRAP_PATH = "../results/(News)Scrapping.xlsx"
EXCEL_DATA_PATH = "../results/Terstruktur(Data Scrapping).xlsx"
OUTPUT_PATH = "../results/(News)Sentiment.xlsx"

TOPICS = {
   
    "Indeks Volatilitas": {
        "target_sheets": ["(News)indeks volatilitas"],
        "output_sheet": "(Summary)Idx Volatilitas",
        "has_data_sentiment": False,
        "role_prompt" : "industri minyak dan gas",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
    },
    
    "Nilai Tukar Rupiah": {
        "target_sheets": ["(News)Kurs"],
        "output_sheet": "(Summary)Nilai Tukar Rupiah",
        "has_data_sentiment": False,
        "role_prompt" : "industri minyak dan gas",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
    },
    
    "IHSG": {
        "target_sheets": ["(News)IHSG"],
        "output_sheet": "(Summary)IHSG",
        "has_data_sentiment": False,
        "role_prompt" : "industri minyak dan gas",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
    },
    
    "JIBOR": {
        "target_sheets": ["(News)JIBOR"],
        "output_sheet": "(Summary)JIBOR",
        "has_data_sentiment": False,
        "role_prompt" : "industri minyak dan gas",
        "spesific_prompt" : "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. Fokus pada waktu, aktor utama, dan "
                            "dampaknya secara global atau regional dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
                            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan em dash/semicolon), dan exclude kasus-kasus hukum!"
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

def summarize_all_news(model, all_news_list, start_date, end_date, sheet_names, role_prompt, spesific_prompt):
    if not all_news_list:
        print("⚠️ Tidak ada berita baru dari semua sheet.")
        return {
            "Tanggal awal": start_date.date(),
            "Tanggal akhir": end_date.date(),
            "Summary": "Tidak ada berita"
        }

    all_news_text = "\n\n".join(all_news_list)

    prompt = f"""
    Kamu adalah analis {role_prompt} di Indonesia.

    Berikut kumpulan berita dari topik {', '.join(sheet_names)}
    antara tanggal {start_date.strftime('%d %B %Y')} dan {end_date.strftime('%d %B %Y')}:

    {all_news_text}

    Buatkan 3 poin ringkasan umum.
    Semua teks pada bagian ini jangan ada yang bold, dan tolong berikan nomor setiap poinnya.

    Gunakan panduan penulisan berikut:
    {spesific_prompt}

    Format jawaban:
    ===SUMMARY===
    (isi ringkasan di sini)
    """

    try:
        response = model.generate_content(prompt)
        result = response.text
        summary = result.split("===SUMMARY===")[-1].strip() if "===SUMMARY===" in result else result.strip()

        print("✅ Summary news selesai.")
        return summary
    except Exception as e:
        print(f"❌ Gagal generate summary: {e}")
        return None

def get_prev_period():
    try:
        df = pd.read_excel(OUTPUT_PATH, sheet_name="(Summary)Bioenergi")

        # Ambil baris terakhir (previous)
        row = df.iloc[-1]

        start_prev = pd.to_datetime(row["Tanggal awal"])
        end_prev = pd.to_datetime(row["Tanggal akhir"])

        return start_prev, end_prev
    except:
        return None, None

def compute_cpo_biodiesel(start_date, end_date):
    # --- CPO (harian) ---
    df_cpo = pd.read_excel(EXCEL_DATA_PATH, sheet_name="(Data)CPO", usecols=["Dates", "PX_LAST"])
    df_cpo["Dates"] = pd.to_datetime(df_cpo["Dates"])
    mask_cpo = (df_cpo["Dates"] >= start_date) & (df_cpo["Dates"] <= end_date)
    cpo_mean = df_cpo.loc[mask_cpo, "PX_LAST"].mean()

    # --- Biodiesel (bulanan) ---
    df_bio = pd.read_excel(EXCEL_DATA_PATH, sheet_name="(Data)Biodesel", usecols=["Date", "HIP Biodiesel IDR/L"])
    df_bio["Date"] = pd.to_datetime(df_bio["Date"])

    mask_bio = (
        (df_bio["Date"].dt.year == end_date.year) &
        (df_bio["Date"].dt.month == end_date.month)
    )
    bio_mean = df_bio.loc[mask_bio, "HIP Biodiesel IDR/L"].mean()

    return cpo_mean, bio_mean

def get_comparison(start_date, end_date, start_date_prev, end_date_prev):
    """
    Mengambil rata-rata CPO untuk rentang sekarang dan rentang sebelumnya,
    mengambil nilai biodiesel untuk bulan sekarang & bulan sebelumnya,
    lalu menghitung perubahan persen.
    Mengembalikan dict: cpo, bio, cpo_change, bio_change, same_month
    """
    # --- CPO harian ---
    df_cpo = pd.read_excel(EXCEL_DATA_PATH, sheet_name="(Data)CPO", usecols=["Dates", "PX_LAST"])
    df_cpo["Dates"] = pd.to_datetime(df_cpo["Dates"]).dt.normalize()

    # current
    cur_mask = (df_cpo["Dates"] >= start_date) & (df_cpo["Dates"] <= end_date)
    cpo_current = df_cpo.loc[cur_mask, "PX_LAST"].mean() if not df_cpo.loc[cur_mask].empty else None

    # previous (rentang yang disediakan)
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
    df_bio = pd.read_excel(EXCEL_DATA_PATH, sheet_name="(Data)Biodiesel", usecols=["Date", "HIP Biodiesel IDR/L"])
    df_bio["Date"] = pd.to_datetime(df_bio["Date"])

    # pilih bulan berdasarkan start_date (kamu bisa ubah nanti jadi mid_date rule jika mau)
    cur_year = start_date.year
    cur_month = start_date.month
    bio_current_rows = df_bio[(df_bio["Date"].dt.year == cur_year) & (df_bio["Date"].dt.month == cur_month)]
    bio_current = bio_current_rows["HIP Biodiesel IDR/L"].mean() if not bio_current_rows.empty else None

    if start_date_prev is not None:
        prev_year = start_date_prev.year
        prev_month = start_date_prev.month
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

    # apakah minggu sebelumnya ada di bulan yang sama? (bandingkan start_date dan start_date_prev)
    same_month = False
    if start_date_prev is not None:
        same_month = (start_date.month == start_date_prev.month)

    # round numbers for output
    def _r(x): 
        return None if x is None else round(x, 2)

    return {
        "cpo": _r(cpo_current),
        "bio": _r(bio_current),
        "cpo_change": cpo_change,
        "bio_change": bio_change,
        "same_month": same_month
    }

def save_to_excel_with_cpo(new_data, output_path, sheet_name):
    if not new_data:
        print("Tidak ada summary yang dihasilkan.")
        return
    new_df = pd.DataFrame(new_data)
    need_summary_col = "Summary Data" in new_df.columns
    if os.path.exists(output_path):
        book = load_workbook(output_path)
        try:
            existing_df = pd.read_excel(output_path, sheet_name=sheet_name)
            for col in ["Tanggal awal", "Tanggal akhir"]:
                if col in existing_df.columns:
                    existing_df[col] = pd.to_datetime(existing_df[col]).dt.date
            if need_summary_col and "Summary Data" not in existing_df.columns:
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
    has_data_sentiment = config.get("has_data_sentiment", False)
    last_date = get_last_summary_date(OUTPUT_PATH, output_sheet)
    if last_date is not None:
        start_date = last_date + pd.Timedelta(days=1)
    else:
        start_date = datetime(2025, 1, 1)
    end_date = pd.to_datetime("2025-12-17")
    print(f"Akan proses berita dari {start_date.date()} sampai {end_date.date()}")
    all_news_list = collect_news_from_sheets(EXCEL_SCRAP_PATH, target_sheets, start_date, end_date)
    if not all_news_list:
        print(f"⚠️ Tidak ada berita baru untuk {topic_name}")
        return
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
        start_prev, end_prev = get_prev_period()
        if start_prev and end_prev:
            cpo_now, bio_now = compute_cpo_biodiesel(start_date, end_date)
            cpo_prev, bio_prev = compute_cpo_biodiesel(start_prev, end_prev)
            cpo_change = ((cpo_now - cpo_prev) / cpo_prev) * 100 if cpo_prev != 0 else 0
            bio_change = ((bio_now - bio_prev) / bio_prev) * 100 if bio_prev != 0 else 0
            cpo_trend = "kenaikan" if cpo_change >= 0 else "penurunan"
            bio_trend = "kenaikan" if bio_change >= 0 else "penurunan"
            summary_data = (
                f"Pada periode {start_date.date()} sampai {end_date.date()}, rata-rata CPO {cpo_now:.2f} dan rata-rata Biodiesel {bio_now:.2f}."
                f"Periode ini mengalami {cpo_trend} {abs(cpo_change):.2f}% nilai CPO "
                f"dan {bio_trend} {abs(bio_change):.2f}% biodiesel dibanding week sebelumnya."
            )

    if summary:
        save_to_excel_with_cpo(
            [{
                "Tanggal awal": start_date.date(),
                "Tanggal akhir": end_date.date(),
                "Summary": summary,
                "Summary Data": summary_data
            }],
            OUTPUT_PATH,
            output_sheet
        )

def main():
    print("Memulai proses summarization untuk semua topik...\n")
    model = setup_gemini()
    for topic_name, config in TOPICS.items():
        try:
            process_topic(model, topic_name, config)
            #print("⏸️ Istirahat 1 menit sebelum lanjut ke topik berikutnya...")
            #time.sleep(60)
        except Exception as e:
            print(f"❌ Error saat memproses {topic_name}: {e}")
            continue
    
    print(f"\n{'='*60}")
    print("✅ Semua proses selesai!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()