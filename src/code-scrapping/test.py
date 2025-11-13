import pandas as pd
import os

path = r"D:\Pekerjaan\Dashboard-Pertamina-VeloCT\src\hasil-scrapping\Biodiesel.xlsx"

if not os.path.exists(path):
    print("⚠️ File tidak ditemukan.")
else:
    try:
        df = pd.read_excel(path)
        print("✅ Dibaca sebagai Excel.")
    except Exception as e:
        print(f"⚠️ Gagal baca Excel ({e}), coba baca sebagai CSV...")
        try:
            df = pd.read_csv(path)
            print("✅ Dibaca sebagai CSV.")
        except Exception as e2:
            print(f"❌ Tetap gagal: {e2}")
            df = None

if df is not None:
    print(df.head())
