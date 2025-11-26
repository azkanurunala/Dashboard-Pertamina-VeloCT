import pandas as pd
import os
from datetime import datetime
import shutil

def manage_excel(excel_path):
    if not os.path.exists(excel_path):
        print(f"File tidak ditemukan: {excel_path}")
        return
    
    df = pd.read_excel(excel_path, engine='openpyxl')
    
    print(f"\nTotal rows sebelum: {len(df)}")
    
    indices = [len(df)-2, len(df)-1]
    
    backup_folder = os.path.join(os.path.dirname(excel_path), "_backup")
    os.makedirs(backup_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_folder, f"backup_{timestamp}.xlsx")
    shutil.copy2(excel_path, backup_path)
    
    df = df.drop(indices, errors='ignore')
    df = df.reset_index(drop=True)
    
    if os.path.exists(excel_path):
        os.remove(excel_path)
    
    df.to_excel(excel_path, index=False, engine='openpyxl')
    
    print(f"Total rows setelah: {len(df)}")
    print(f"\n{df.to_string(index=True)}")

if __name__ == "__main__":
    path = '../hasil-scrapping/data_migas_eia.xlsx'
    manage_excel(path)