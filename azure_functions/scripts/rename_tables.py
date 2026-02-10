
import pyodbc

conn_str = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=no;TrustServerCertificate=yes;Connection Timeout=30;"

def rename_tables():
    tables_to_rename = {
        'biodiesel_hip': 'data_biodiesel_hip',
        'bioetanol_hip': 'data_bioetanol_hip',
        'cpo_prices': 'data_cpo_prices',
        'saf_uco_prices': 'data_saf_uco_prices',
        'oil_crackspreads': 'data_oil_crackspreads',
        'market_indicators': 'data_market_indicators',
        'ruptl_projects': 'data_ruptl_projects',
        'petrochemical_prices': 'data_petrochemical_prices',
        'fossil_predictions': 'data_fossil_prediction',
        'oil_prices': 'data_oil_prices',
        'volatility_index': 'data_volatility_index',
        'geopolitical_risk_index': 'data_geopolitical_risk_index',
        'wte_waste_data': 'data_wte_waste',
        'eia_market_data': 'data_eia_market',
        'renewable_energy_data': 'data_renewable_energy',
        'nuclear_data': 'data_nuclear',
        'manual_input_data': 'data_fossil'
    }
    
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Get existing tables
        existing_tables = [t.table_name for t in cursor.tables(tableType='TABLE')]
        
        for old_name, new_name in tables_to_rename.items():
            if old_name in existing_tables:
                print(f"Renaming {old_name} to {new_name}...")
                try:
                    cursor.execute(f"EXEC sp_rename '{old_name}', '{new_name}'")
                    conn.commit()
                    print(f"Success: {old_name} -> {new_name}")
                except Exception as e:
                    print(f"Failed to rename {old_name}: {e}")
            elif new_name in existing_tables:
                print(f"Info: Table {new_name} already exists.")
            else:
                print(f"Warning: Table {old_name} not found.")
                
        conn.close()
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    rename_tables()
