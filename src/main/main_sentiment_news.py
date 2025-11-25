import os
import pandas as pd
import google.genai as genai
from dotenv import load_dotenv
from datetime import date

# ===========================================================
# 1. SETUP GEMINI CLIENT
# ===========================================================
dotenv_path = os.path.join(os.getcwd(), '.env')
load_dotenv(dotenv_path)
try:
    client = genai.Client()
    print("✅ Klien Gemini berhasil diinisialisasi.")
except Exception as e:
    print(f"❌ Gagal inisialisasi klien Gemini. Detail: {e}")
    exit()

# ===========================================================
# 2. KONFIGURASI DASAR
# ===========================================================
SOURCE_FILE = "Scrapping.xlsx"
NEWS_COLUMN = "content"
DATE_COLUMN = "date"
TANGGAL_PILIHAN = "2025-10-28"
today = pd.to_datetime(TANGGAL_PILIHAN).normalize()

# ===========================================================
# 3. DEFINISI TOPIK MANUAL
# ===========================================================
TOPIC_MAP = {
    "(News)HIP": "harga industri primer",
    "(News)Kurs": "nilai tukar rupiah",
    "(News)CPO": "harga minyak sawit mentah",
    "(News)BBM": "harga bahan bakar minyak",
    "(News)Emas": "harga emas",
    # tambahkan lagi jika ada sheet lain
}

# ===========================================================
# 4. LOOP UNTUK SETIAP SHEET
# ===========================================================
xls = pd.ExcelFile(SOURCE_FILE)
news_sheets = [s for s in xls.sheet_names if s.startswith("(News)")]

if not news_sheets:
    print("⚠️ Tidak ditemukan sheet yang diawali '(News)'.")
    exit()

all_summaries = []  # kumpulan rekap semua topik

with pd.ExcelWriter(SOURCE_FILE, mode="a", engine="openpyxl", if_sheet_exists="replace") as writer:
    for sheet in news_sheets:
        print(f"\n================== MEMPROSES {sheet} ==================")

        # Ambil topik dari mapping, fallback ke nama sheet
        topik = TOPIC_MAP.get(sheet, sheet.replace("(News)", "").strip())

        try:
            df = pd.read_excel(SOURCE_FILE, sheet_name=sheet)
        except Exception as e:
            print(f"❌ Gagal membaca sheet {sheet}: {e}")
            continue

        if NEWS_COLUMN not in df.columns or DATE_COLUMN not in df.columns:
            print(f"⚠️ Sheet {sheet} tidak memiliki kolom '{NEWS_COLUMN}' atau '{DATE_COLUMN}'. Lewati.")
            continue

        # Filter data tanggal tertentu
        df = df.dropna(subset=[NEWS_COLUMN])
        df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], errors="coerce").dt.normalize()
        df_today = df[df[DATE_COLUMN] == today].copy()

        if df_today.empty:
            print(f"⚠️ Tidak ada berita untuk {today.date()} di sheet {sheet}.")
            continue

        # ===========================================================
        # 5. SIAPKAN PROMPT UNTUK GEMINI
        # ===========================================================
        all_news = "\n\n".join([f"{i+1}. {n}" for i, n in enumerate(df_today[NEWS_COLUMN])])
        prompt = f"""
Kamu adalah analis berita ekonomi Indonesia.

Berikut adalah kumpulan berita tentang {topik} dari tanggal {today.strftime('%d %B %Y')}:

{all_news}

Tolong buatkan ringkasan singkat (3–4 poin utama)
yang menjelaskan arah sentimen keseluruhan dan dampaknya terhadap {topik}.
Jangan gunakan teks tebal atau huruf kapital berlebihan, dan beri nomor di setiap poin.

Format jawaban:
===SUMMARY===
(isi ringkasan di sini)
"""

        print(f"⏳ Mengirim berita tentang '{topik}' ke Gemini...")
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            output_text = response.text
            print("✅ Respons diterima dari Gemini.")
        except Exception as e:
            print(f"❌ Gagal mengirim ke Gemini. Detail: {e}")
            continue

        # ===========================================================
        # 6. AMBIL BAGIAN SUMMARY
        # ===========================================================
        try:
            summary_part = output_text.split("===SUMMARY===")[1].strip()
        except Exception:
            summary_part = output_text.strip()

        senti_sheet = sheet.replace("(News)", "(Senti)")
        summary_df = pd.DataFrame({
            "date": [today.date()],
            "topic": [topik],
            "summary": [summary_part]
        })

        # Simpan sheet hasil
        summary_df.to_excel(writer, index=False, sheet_name=senti_sheet)
        print(f"💾 Ringkasan '{topik}' disimpan ke sheet '{senti_sheet}'.")

        # Simpan juga ke list rekap
        all_summaries.append(summary_df)

    # ===========================================================
    # 7. BUAT SHEET GABUNGAN ALL SUMMARY
    # ===========================================================
    if all_summaries:
        all_summary_df = pd.concat(all_summaries, ignore_index=True)
        all_summary_df.to_excel(writer, index=False, sheet_name="All_Summary")
        print("\n🧾 Rekap semua topik disimpan di sheet 'All_Summary'.")

print("\n✅ Semua sheet selesai diproses!")
