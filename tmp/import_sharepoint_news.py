"""
Import semua artikel dari SharePoint Excel ke Azure SQL.
- Baca (News)Scrapping.xlsx dan (News)Scrapping_new.xlsx
- Untuk setiap sheet, map ke category di DB
- Skip artikel yang sudah ada (url + category)
- Insert yang belum ada
"""
import pyodbc, json, uuid, openpyxl, sys
from datetime import datetime, date

DRY_RUN = '--dry-run' in sys.argv

settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
with open(settings_path) as f:
    conn_str = json.load(f)['Values']['SQL_SERVER_CONNECTION_STRING']
conn_str = conn_str.replace("Encrypt=yes","Encrypt=no").replace("TrustServerCertificate=no","TrustServerCertificate=yes")

conn = pyodbc.connect(conn_str, timeout=30)
cursor = conn.cursor()

# Build source name → source_id lookup
cursor.execute("SELECT id, name FROM news_sources")
source_map_raw = {r[1]: r[0] for r in cursor.fetchall()}

# Normalize source name from Excel → DB source_id
SOURCE_NAME_MAP = {
    'CNBC':             source_map_raw.get('CNBC'),
    'CNBC_ID':          source_map_raw.get('CNBC_ID'),
    'KOMPAS':           source_map_raw.get('KOMPAS'),
    'Bisnis Indonesia': source_map_raw.get('BISNIS_INDONESIA') or source_map_raw.get('Bisnis Indonesia'),
    'BISNIS':           source_map_raw.get('BISNIS'),
    'KONTAN':           source_map_raw.get('KONTAN'),
    'Tempo':            source_map_raw.get('Tempo'),
    'THEGUARDIAN':      source_map_raw.get('THEGUARDIAN'),
    'EnergiesMedia':    source_map_raw.get('EnergiesMedia'),
    'SCMP':             source_map_raw.get('SCMP'),
    'OILPRICE':         source_map_raw.get('OILPRICE'),
    'S&P':              source_map_raw.get('S&P'),
    'S&P News':         source_map_raw.get('S&P News'),
    'CNN':              source_map_raw.get('CNN'),
    'BIOENERGYTIMES':   source_map_raw.get('BIOENERGYTIMES'),
    'BLOOMBERG_TECHNOZ':source_map_raw.get('BLOOMBERG_TECHNOZ'),
    'Bank Indonesia':   source_map_raw.get('Bank Indonesia'),
    'BANK_INDONESIA':   source_map_raw.get('BANK_INDONESIA'),
    'BPS':              source_map_raw.get('BPS'),
    'ESDM Biodiesel':   source_map_raw.get('ESDM Biodiesel'),
    'ESDM Bioetanol':   source_map_raw.get('ESDM Bioetanol'),
    'Migas EIA':        source_map_raw.get('Migas EIA'),
    'BISNIS_INDONESIA': source_map_raw.get('BISNIS_INDONESIA'),
    'SPGLOBAL':         source_map_raw.get('S&P') or source_map_raw.get('S&P News'),
    'TEMPO':            source_map_raw.get('Tempo'),
}

def get_source_id(source_name):
    if not source_name:
        return None
    # Exact match
    if source_name in SOURCE_NAME_MAP and SOURCE_NAME_MAP[source_name]:
        return SOURCE_NAME_MAP[source_name]
    # Try DB direct lookup (case-insensitive fallback)
    for db_name, db_id in source_map_raw.items():
        if db_name.upper() == source_name.upper():
            return db_id
    return None

def sheet_to_category(sheet_name):
    """Map sheet name to DB category."""
    cat = sheet_name.replace('(News)', '').strip()
    # Fix old typo sheets
    if cat == 'Crackspeed_BBM':
        cat = 'Crackspread_BBM'
    elif cat == 'Crackspeed_NonBBM':
        cat = 'Crackspread_NonBBM'
    return cat

def parse_date(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        val = val.strip()
        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y'):
            try:
                return datetime.strptime(val[:10], fmt).date()
            except:
                pass
    return None

# Load all existing (url, category) pairs from DB into memory for fast dedup
print("Loading existing articles from DB...")
cursor.execute("SELECT url, category FROM news_articles WHERE url IS NOT NULL")
existing = set()
for r in cursor.fetchall():
    if r[0] and r[1]:
        existing.add((r[0].strip(), r[1].strip()))
print(f"  {len(existing)} existing (url, category) pairs loaded")

EXCEL_FILES = [
    'sharepoint_data/(News)Scrapping.xlsx',
    'sharepoint_data/(News)Scrapping_new.xlsx',
]

total_inserted = 0
total_skipped = 0
total_no_source = 0
total_no_date = 0
results_per_cat = {}

for excel_path in EXCEL_FILES:
    print(f"\n{'='*60}")
    print(f"Processing: {excel_path}")
    print(f"{'='*60}")

    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)

    for sheet_name in wb.sheetnames:
        category = sheet_to_category(sheet_name)
        ws = wb[sheet_name]

        # Read header row
        header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
        if not header_row:
            continue
        headers = [str(h).lower().strip() if h else '' for h in header_row]

        # Find column indices
        try:
            idx_title   = headers.index('title')
            idx_date    = headers.index('date')
            idx_url     = headers.index('url')
            idx_content = headers.index('content') if 'content' in headers else -1
            idx_source  = headers.index('source')
        except ValueError as e:
            print(f"  [{sheet_name}] SKIP - missing column: {e}")
            continue

        inserted = skipped = no_source = no_date = no_url = 0
        rows_to_insert = []

        for row in ws.iter_rows(min_row=2, values_only=True):
            title = row[idx_title] if idx_title < len(row) else None
            if not title:
                continue

            url = row[idx_url] if idx_url < len(row) else None
            if not url:
                no_url += 1
                continue

            url = str(url).strip()

            # Skip if already in DB with this category
            if (url, category) in existing:
                skipped += 1
                continue

            pub_date = parse_date(row[idx_date] if idx_date < len(row) else None)
            if not pub_date:
                no_date += 1
                continue

            source_name = str(row[idx_source]).strip() if idx_source < len(row) and row[idx_source] else None
            source_id = get_source_id(source_name)
            if not source_id:
                no_source += 1
                continue

            content = row[idx_content] if idx_content >= 0 and idx_content < len(row) else None

            rows_to_insert.append({
                'id': str(uuid.uuid4()),
                'title': str(title)[:2000],
                'content': str(content) if content else None,
                'url': url,
                'source_id': source_id,
                'published_date': pub_date,
                'category': category,
            })
            # Add to existing set to prevent duplicate across files
            existing.add((url, category))

        # Batch insert
        if not DRY_RUN:
            for r in rows_to_insert:
                try:
                    cursor.execute("""
                        INSERT INTO news_articles
                            (id, title, content, url, source_id, published_date, scraped_date, language, author, category)
                        VALUES (?, ?, ?, ?, ?, ?, GETDATE(), 'id', NULL, ?)
                    """, r['id'], r['title'], r['content'], r['url'],
                        r['source_id'], r['published_date'], r['category'])
                    inserted += 1
                except pyodbc.IntegrityError:
                    skipped += 1
            if inserted > 0:
                conn.commit()
        else:
            inserted = len(rows_to_insert)

        total_inserted += inserted
        total_skipped += skipped
        total_no_source += no_source
        total_no_date += no_date

        cat_key = f"{category}"
        if cat_key not in results_per_cat:
            results_per_cat[cat_key] = {'inserted': 0, 'skipped': 0}
        results_per_cat[cat_key]['inserted'] += inserted
        results_per_cat[cat_key]['skipped'] += skipped

        status = "DRY-RUN" if DRY_RUN else "OK"
        if inserted > 0 or no_source > 0:
            print(f"  [{status}] {sheet_name:40} | +{inserted:4} inserted | {skipped:5} exist | {no_source:3} no-source | {no_date:3} no-date")

    wb.close()

print(f"\n{'='*60}")
print(f"{'DRY RUN - ' if DRY_RUN else ''}SELESAI")
print(f"{'='*60}")
print(f"Total inserted  : {total_inserted}")
print(f"Total skipped   : {total_skipped}")
print(f"Total no-source : {total_no_source}")
print(f"Total no-date   : {total_no_date}")

print(f"\nPer kategori (yang ada insert):")
for cat, v in sorted(results_per_cat.items()):
    if v['inserted'] > 0:
        print(f"  {cat:40} | +{v['inserted']:5} | {v['skipped']:5} exist")

conn.close()
