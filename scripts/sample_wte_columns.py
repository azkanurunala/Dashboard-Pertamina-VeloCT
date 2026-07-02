"""
Utility: print WTE column names from SIPSN API.
Run once to see the full column list, then add them manually to create_tables.sql if desired.
The columns will be auto-created by neon_helper.create_table_if_needed() on first wte_sipsn.py run.
"""

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from structured_data.wte_sipsn import fetch_all_data

data = fetch_all_data("2024")
for jenis, df in data.items():
    print(f"\n=== {jenis} ===")
    print(f"Columns ({len(df.columns)}): {df.columns.tolist()}")
    print(f"Sample row:\n{df.head(1).to_string()}")
