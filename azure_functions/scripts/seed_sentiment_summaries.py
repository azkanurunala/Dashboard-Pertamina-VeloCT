import os
import csv
import uuid
import json
import pyodbc
from datetime import datetime

def load_conn_str():
    # Try local.settings.json first
    settings_path = os.path.join(os.path.dirname(__file__), '..', 'local.settings.json')
    if os.path.exists(settings_path):
        with open(settings_path, 'r') as f:
            data = json.load(f)
            return data.get('Values', {}).get('SQL_SERVER_CONNECTION_STRING')
    
    # Try .env.azure
    env_azure_path = os.path.join(os.path.dirname(__file__), '..', '.env.azure')
    if os.path.exists(env_azure_path):
        with open(env_azure_path, 'r') as f:
            for line in f:
                if line.startswith('SQL_SERVER_CONNECTION_STRING='):
                    return line.split('=', 1)[1].strip().strip('"')
    
    return None

def seed_sentiment_data():
    conn_str = load_conn_str()
    if not conn_str:
        print("Error: Could not find SQL_SERVER_CONNECTION_STRING")
        return

    # Fix connection string for local run if needed (Encrypt/TrustServerCertificate)
    if "TrustServerCertificate=no" in conn_str:
        conn_str = conn_str.replace("TrustServerCertificate=no", "TrustServerCertificate=yes")
    if "Encrypt=yes" in conn_str:
        conn_str = conn_str.replace("Encrypt=yes", "Encrypt=no")

    print(f"Connecting to database...")
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    sentiment_dir = os.path.join(os.path.dirname(__file__), '..', 'references', 'sentiment')
    csv_files = [f for f in os.listdir(sentiment_dir) if f.startswith('(Summary)') and f.endswith('.csv')]

    print(f"Found {len(csv_files)} CSV files to process.")

    total_inserted = 0

    for filename in csv_files:
        filepath = os.path.join(sentiment_dir, filename)
        # Extract topic from filename: (Summary)Topic.csv -> Topic
        topic = filename.replace('(Summary)', '').replace('.csv', '').strip()
        print(f"Processing {filename} (Topic: {topic})...")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                for row in rows:
                    start_date_str = row.get('Tanggal awal')
                    end_date_str = row.get('Tanggal akhir')
                    summary = row.get('Summary') or row.get('Summary Data') or ""

                    if not start_date_str or not end_date_str or not summary or summary == "-":
                        continue

                    # Parse dates
                    try:
                        # Some might have time, some not
                        if ' ' in start_date_str:
                            start_date = datetime.strptime(start_date_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                        else:
                            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                            
                        if ' ' in end_date_str:
                            end_date = datetime.strptime(end_date_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                        else:
                            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                    except Exception as e:
                        print(f"  Warning: Could not parse dates in row: {e}")
                        continue

                    # Insert into sentiment_analyses
                    analysis_id = str(uuid.uuid4())
                    now = datetime.utcnow()

                    insert_query = """
                    INSERT INTO sentiment_analyses 
                    (id, analysis_date, date_range_start, date_range_end, sentiment_score, 
                     sentiment_label, confidence, summary, model_version, role_context, article_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    
                    try:
                        cursor.execute(insert_query, (
                            analysis_id,
                            now,
                            start_date,
                            end_date,
                            0.0, # Default score
                            'neutral', # Default label
                            1.0, # Default confidence
                            summary,
                            'manual-seed-v1',
                            topic,
                            0 # Default article count
                        ))
                        total_inserted += 1
                    except Exception as e:
                        print(f"  Error inserting row: {e}")

            conn.commit()
            print(f"  Finished {filename}")

        except Exception as e:
            print(f"  Error processing file {filename}: {e}")

    conn.close()
    print(f"\nSeeding completed. Total records inserted: {total_inserted}")

if __name__ == "__main__":
    seed_sentiment_data()
