
import pyodbc

conn_str = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=no;TrustServerCertificate=yes;Connection Timeout=30;"

def check_schema():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        print("--- Columns in data_fossil ---")
        for column in cursor.columns(table='data_fossil'):
            print(f"Column: {column.column_name}, Type: {column.type_name}")
        
        print("\n--- Columns in data_fossil_prediction ---")
        for column in cursor.columns(table='data_fossil_prediction'):
            print(f"Column: {column.column_name}, Type: {column.type_name}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()
