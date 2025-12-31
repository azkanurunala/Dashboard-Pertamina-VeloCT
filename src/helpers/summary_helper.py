
from dotenv import load_dotenv
import google.generativeai as genai
import os
import pandas as pd

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
    Pisahkan setiap poin dengan baris kosong (enter) agar lebih mudah dibaca.

    Gunakan panduan penulisan berikut:
    {spesific_prompt}

    Format jawaban (dengan baris kosong antar poin):
    ===SUMMARY===
    1) (poin pertama)

    2) (poin kedua)

    3) (poin ketiga)
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