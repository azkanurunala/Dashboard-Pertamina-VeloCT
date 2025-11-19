import os
import sys

def check_file_lock(filepath):
    """
    Deteksi proses mana yang lock file Excel
    """
    print("\n" + "="*80)
    print("🔍 FILE LOCK DETECTOR")
    print("="*80)
    print(f"File: {filepath}\n")
    
    if not os.path.exists(filepath):
        print("❌ File tidak ditemukan!")
        return
    
    # Method 1: Coba buka file
    print("📝 Test 1: Coba buka file...")
    try:
        with open(filepath, 'r+b') as f:
            print("✅ File TIDAK terkunci - bisa dibuka!\n")
            return
    except PermissionError as e:
        print(f"❌ File TERKUNCI: {e}\n")
    except Exception as e:
        print(f"⚠️  Error lain: {e}\n")
    
    # Method 2: Pakai psutil untuk cari proses
    print("📝 Test 2: Mencari proses yang lock file...")
    try:
        import psutil
        
        locked_by = []
        for proc in psutil.process_iter(['pid', 'name', 'open_files']):
            try:
                for file in proc.open_files():
                    if os.path.normpath(file.path) == os.path.normpath(filepath):
                        locked_by.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'path': file.path
                        })
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
        
        if locked_by:
            print(f"🔒 File di-lock oleh {len(locked_by)} proses:\n")
            for item in locked_by:
                print(f"   PID: {item['pid']}")
                print(f"   Nama: {item['name']}")
                print(f"   Path: {item['path']}\n")
        else:
            print("❓ Tidak ditemukan proses yang lock (mungkin system lock)")
    
    except ImportError:
        print("⚠️  psutil tidak terinstall. Install dengan: pip install psutil")
    
    # Method 3: Check file attributes
    print("📝 Test 3: File attributes...")
    try:
        import stat
        file_stat = os.stat(filepath)
        mode = file_stat.st_mode
        
        print(f"   Permissions: {oct(stat.S_IMODE(mode))}")
        print(f"   Read-only: {not (mode & stat.S_IWRITE)}")
        print(f"   Size: {file_stat.st_size} bytes")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Method 4: Check for temp files (Excel lock indicator)
    print("\n📝 Test 4: Cek file temporary Excel...")
    folder = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    
    temp_patterns = [
        f"~${filename}",  # Excel temp file
        f".~lock.{filename}#",  # LibreOffice lock
        "~$*.xlsx",  # Generic Excel temp
    ]
    
    temp_files = []
    try:
        for file in os.listdir(folder):
            for pattern in temp_patterns:
                if pattern.replace('*', '') in file or file.startswith('~$'):
                    temp_files.append(file)
        
        if temp_files:
            print(f"   🔒 Ditemukan {len(temp_files)} file temporary:")
            for tf in temp_files:
                print(f"      - {tf}")
        else:
            print("   ✅ Tidak ada file temporary Excel")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "="*80)
    print("💡 SARAN:")
    print("="*80)
    print("1. Tutup SEMUA aplikasi Excel/LibreOffice")
    print("2. Cek Task Manager → cari 'EXCEL.EXE' → End Task")
    print("3. Hapus file temporary (~$*.xlsx) di folder")
    print("4. Restart Windows Explorer (Ctrl+Shift+Esc → Restart 'Windows Explorer')")
    print("5. Kalau masih gagal, restart komputer")
    print("="*80 + "\n")


if __name__ == "__main__":
    # Ganti dengan path file Anda
    excel_path = "../hasil-scrapping/data_migas_esdm.xlsx"
    
    # Convert to absolute path
    excel_path = os.path.abspath(excel_path)
    
    check_file_lock(excel_path)
    
    input("\nTekan ENTER untuk exit...")