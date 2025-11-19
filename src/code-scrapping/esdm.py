import pandas as pd
import os
import shutil

def create_initial_excel_file():
    """
    Hapus file corrupt dan buat Excel baru dengan data awal.
    """
    print("\n" + "="*80)
    print("CREATE INITIAL EXCEL FILE")
    print("="*80 + "\n")
    
    excel_path = "../hasil-scrapping/data_migas_esdm.xlsx"
    backup_folder = "../hasil-scrapping/_backup"
    
    # Step 1: Check if file exists
    if os.path.exists(excel_path):
        print(f"[INFO] File ditemukan: {excel_path}")
        
        # Try to read it first
        try:
            df = pd.read_excel(excel_path)
            print(f"[INFO] File OK! Berisi {len(df)} baris data")
            print("\n[INFO] Preview data:")
            print(df.tail().to_string(index=False))
            
            response = input("\n[?] File sudah OK. Tetap replace dengan data baru? (y/n): ").strip().lower()
            if response != 'y':
                print("[INFO] Dibatalkan. File tidak diubah.")
                return
        
        except Exception as e:
            print(f"[ERROR] File corrupt: {str(e)[:100]}")
        
        # Backup corrupt file
        try:
            os.makedirs(backup_folder, exist_ok=True)
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_folder, f"data_migas_esdm_{timestamp}.xlsx")
            shutil.move(excel_path, backup_path)
            print(f"[SUCCESS] ✅ File lama dipindahkan ke: {backup_path}")
        except Exception as e:
            print(f"[WARN] Gagal backup: {e}")
            try:
                os.remove(excel_path)
                print(f"[SUCCESS] ✅ File lama dihapus")
            except Exception as e2:
                print(f"[ERROR] Gagal hapus: {e2}")
                return
    
    # Step 2: Create new Excel with initial data
    print("\n[INFO] Membuat file Excel baru...")
    
    # Data awal yang Anda mau
    initial_data = {
        'Tahun': [2025],
        'Bulan': ['September'],
        'Harga': ['86.87'],
        'Tanggal': ['4 Oktober']
    }
    
    df = pd.DataFrame(initial_data)
    
    # Create folder if not exists
    os.makedirs(os.path.dirname(excel_path), exist_ok=True)
    
    # Save to Excel
    try:
        df.to_excel(excel_path, index=False)
        print(f"[SUCCESS] File Excel baru berhasil dibuat!")
        print(f"\nPath: {excel_path}")
        print(f"Size: {os.path.getsize(excel_path)} bytes")
        
        print(f"\n{'='*80}")
        print("Data di Excel:")
        print(f"{'='*80}")
        print(df.to_string(index=False))
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"[ERROR] ❌ Gagal membuat Excel: {e}")

if __name__ == "__main__":
    create_initial_excel_file()