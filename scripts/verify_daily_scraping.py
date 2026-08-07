"""verify_daily_scraping.py -- Prove daily scraping ran by checking Neon for
rows dated the last completed workday.

Checks two tables:
  - news_articles   : raw scraped articles (date column) -- ALL topics,
                       since the scraper (ACTIVE_SHEETS in
                       main_news_scraping_lokal.py / _internasional.py) runs
                       daily for every topic regardless of summary cadence.
  - news_sentiment  : Gemini summaries ("Tanggal akhir" column) -- only the
                       topics whose summary is aggregated daily; weekly/
                       monthly summary topics would false-positive here.

Usage:
    python scripts/verify_daily_scraping.py                  # checks yesterday (or last Friday if today is Mon)
    python scripts/verify_daily_scraping.py --date 2026-08-05
"""

import argparse
import os
import sys
from datetime import date, timedelta

import psycopg2
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, "..", ".env"))

# All news topics scraped daily (source: ACTIVE_SHEETS in
# main_news_scraping_lokal.py -- internasional.py scrapes a subset of the
# same topic names into the same table).
ALL_NEWS_TOPICS = [
    "(News)Indeks Risiko Geopolitik",
    "(News)Indeks Volatilitas",
    "(News)Kurs",
    "(News)IHSG",
    "(News)Inflasi",
    "(News)BI Rate",
    "(News)Indonia",
    "(News)Indeks Penjualan Ritel",
    "(News)Indeks Kepercayaan Knsmn",
    "(News)Indeks Kinerja Manufaktur",
    "(News)Indeks Kinerja Jasa",
    "(News)Neraca Perdagangan",
    "(News)PDB",
    "(News)Harga Minyak",
    "(News)Volume Minyak",
    "(News)Harga Produk Kilang",
    "(News)Volume Produk Kilang",
    "(News)Crackspread BBM",
    "(News)Crackspread Non-BBM",
    "(News)Biodiesel",
    "(News)SAF",
    "(News)Bioetanol",
    "(News)RUPTL",
    "(News)EBT",
    "(News)WTE",
    "(News)Nuklir",
]

# Topics whose SUMMARY (not raw news) is aggregated daily
DAILY_SUMMARY_TOPICS = [
    "(Summary)Nilai Tukar Rupiah",
    "(Summary)IHSG",
    "(Summary)Indonia",
    "(Summary)Idx Volatilitas",
    "(Summary)Idx Risiko Geopolitik",
]


def last_business_day(from_date: date) -> date:
    d = from_date - timedelta(days=1)
    while d.weekday() >= 5:  # Sat=5, Sun=6
        d -= timedelta(days=1)
    return d


def check(cur, table: str, date_col: str, topics: list[str], target: date) -> bool:
    cur.execute(
        f'SELECT topic, COUNT(*) FROM {table} '
        f'WHERE {date_col} = %s AND topic = ANY(%s) GROUP BY topic',
        (target, topics),
    )
    counts = dict(cur.fetchall())

    all_ok = True
    for topic in topics:
        n = counts.get(topic, 0)
        status = "OK" if n > 0 else "MISSING"
        if n == 0:
            all_ok = False
        print(f"  [{status:7s}] {table:15s} {topic:35s} rows={n}")
    return all_ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, help="Target date YYYY-MM-DD (default: last business day)")
    args = parser.parse_args()

    target = date.fromisoformat(args.date) if args.date else last_business_day(date.today())

    db_url = os.getenv("NEON_DB_URL")
    if not db_url:
        sys.exit("NEON_DB_URL not set (check .env)")

    print(f"Verifying scraping output for {target.isoformat()}\n")

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            print("news_articles (raw scraped news, all topics):")
            news_ok = check(cur, "news_articles", "date", ALL_NEWS_TOPICS, target)
            print("\nnews_sentiment (daily Gemini summary, \"Tanggal akhir\"):")
            summary_ok = check(cur, "news_sentiment", '"Tanggal akhir"', DAILY_SUMMARY_TOPICS, target)
    finally:
        conn.close()

    print()
    if news_ok and summary_ok:
        print(f"PASS: scraping + summarization both produced data for {target.isoformat()}.")
        sys.exit(0)
    else:
        print(f"FAIL: missing data for {target.isoformat()} (see MISSING rows above).")
        sys.exit(1)


if __name__ == "__main__":
    main()
