"""backfill_sentiment_daily.py -- Backfill Gemini summaries for all topics.

The production sentiment orchestrators only move forward from the latest
"Tanggal akhir" per topic, so historical gaps are never filled. This script
walks a historical date range and, for every (topic, period) that has articles
in news_articles but no row in news_sentiment, generates a summary and upserts
it (conflict key: topic + "Tanggal awal"). Period length matches each topic's
production cadence: 1-day windows for DAILY_TOPICS, 7-day windows for
everything else (mirroring main_sentiment_news_mingguan.py).

Usage:
    python scripts/backfill_sentiment_daily.py                          # 8 bulan ke belakang
    python scripts/backfill_sentiment_daily.py --start 2025-11-05 --end 2026-07-04
    python scripts/backfill_sentiment_daily.py --topics "IHSG" "Inflasi"
    python scripts/backfill_sentiment_daily.py --delay 5 --dry-run

Newest month is processed first (bulan-1, lalu bulan-2, dst.), same as the
news backfill. Safe to interrupt and re-run: existing summary days are
skipped by checking news_sentiment first.
"""

import argparse
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

from dotenv import load_dotenv

load_dotenv(SCRIPT_DIR.parent / ".env")
os.environ["STORAGE_BACKEND"] = "neon"  # backfill selalu ke Neon, override .env

import pandas as pd  # noqa: E402

ROLE_PROMPT = "Ekonom"
SPESIFIC_PROMPT = (
    "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. "
    "Fokus pada waktu, aktor utama, dan dampaknya secara global atau regional "
    "dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
    "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan "
    "em dash/semicolon), dan exclude kasus-kasus hukum!"
)

# topic -> (target news sheets, output summary sheet)
# Reconstructed from the (mostly commented) TOPICS configs across the three
# sentiment orchestrators. Sheet names must match news_articles/news_sentiment
# topic values exactly.
TOPICS: dict[str, tuple[list[str], str]] = {
    "Indeks Risiko Geopolitik":   (["(News)Indeks Risiko Geopolitik"], "(Summary)Idx Risiko Geopolitik"),
    "Indeks Volatilitas":         (["(News)Indeks Volatilitas"], "(Summary)Idx Volatilitas"),
    "Nilai Tukar Rupiah":         (["(News)Kurs"], "(Summary)Nilai Tukar Rupiah"),
    "IHSG":                       (["(News)IHSG"], "(Summary)IHSG"),
    "Inflasi":                    (["(News)Inflasi"], "(Summary)Inflasi"),
    "BI Rate":                    (["(News)BI Rate"], "(Summary)BI-Rate"),
    "Indonia":                    (["(News)Indonia"], "(Summary)Indonia"),
    "Indeks Penjualan Ritel":     (["(News)Indeks Penjualan Ritel"], "(Summary)Idx Penjualan Ritel"),
    "Indeks Kepercayaan Konsumen": (["(News)Indeks Kepercayaan Knsmn"], "(Summary)Idx Kepercayaan Konsum"),
    "Indeks PMI":                 (["(News)Indeks Kinerja Manufaktur", "(News)Indeks Kinerja Jasa"], "(Summary)Idx PMI"),
    "Neraca Perdagangan":         (["(News)Neraca Perdagangan"], "(Summary)Neraca Perdagangan"),
    "PDB":                        (["(News)PDB"], "(Summary)PDB"),
    "Harga Minyak":               (["(News)Harga Minyak"], "(Summary)Harga Minyak"),
    "Volume Minyak":              (["(News)Volume Minyak"], "(Summary)Volume Minyak"),
    "Harga Produk Kilang":        (["(News)Harga Produk Kilang"], "(Summary)Harga Produk Kilang"),
    "Volume Produk Kilang":       (["(News)Volume Produk Kilang"], "(Summary)Volume Produk Kilang"),
    "Crackspread BBM":            (["(News)Crackspread BBM"], "(Summary)Crackspread BBM"),
    "Crackspread Non-BBM":        (["(News)Crackspread Non-BBM"], "(Summary)Crackspread Non-BBM"),
    "Biodiesel":                  (["(News)Biodiesel"], "(Summary)Biodiesel"),
    "SAF":                        (["(News)SAF"], "(Summary)SAF"),
    "Bioetanol":                  (["(News)Bioetanol"], "(Summary)Bioetanol"),
    "RUPTL":                      (["(News)RUPTL"], "(Summary)RUPTL"),
    "Harga EBT":                  (["(News)EBT"], "(Summary)Harga EBT"),
    "Kapasitas EBT":              (["(News)EBT"], "(Summary)Kapasitas EBT"),
    "WTE":                        (["(News)WTE"], "(Summary)WTE"),
    "Nuklir":                     (["(News)Nuklir"], "(Summary)Nuklir"),
}


# Topics processed daily by the production "harian" orchestrators
# (main_sentiment_news_lokal_harian.py / main_sentiment_news_internasional_harian.py).
# Everything else in TOPICS is processed weekly by main_sentiment_news_mingguan.py
# (SUMMARY_WINDOW_DAYS=6, i.e. 7-day windows) — the backfill must match that
# cadence or Power BI ends up with daily rows where weekly ones are expected.
DAILY_TOPICS = {"Nilai Tukar Rupiah", "IHSG", "Indonia", "Indeks Volatilitas"}


def topic_windows(topic: str, start: date, end: date) -> list[tuple[str, date, date]]:
    """Newest-first windows sized to match the topic's production cadence.

    Daily topics get 1-day windows; everything else gets 7-day windows
    (mirroring SUMMARY_WINDOW_DAYS in main_sentiment_news_mingguan.py).
    """
    length_days = 0 if topic in DAILY_TOPICS else 6
    windows = []
    n = 1
    win_end = end
    while win_end >= start:
        win_start = max(start, win_end - timedelta(days=length_days))
        windows.append((f"periode-{n}", win_start, win_end))
        win_end = win_start - timedelta(days=1)
        n += 1
    return windows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    today = date.today()
    ap.add_argument("--start", default=(today - timedelta(days=240)).isoformat())
    ap.add_argument("--end", default=(today - timedelta(days=1)).isoformat())
    ap.add_argument("--topics", nargs="+", help="subset of topic names (default: all)")
    ap.add_argument("--delay", type=float, default=4.0, help="seconds between Gemini calls")
    ap.add_argument("--dry-run", action="store_true", help="hitung saja, tanpa panggil Gemini/tulis DB")
    args = ap.parse_args()

    from helpers.storage_backend import storage
    from helpers.summary_helper import setup_gemini, summarize_all_news
    import psycopg2

    def _query(sql, params, retries=3):
        """Koneksi segar per query + retry — tahan drop koneksi Neon."""
        last = None
        for _ in range(retries):
            try:
                with psycopg2.connect(os.environ["NEON_DB_URL"]) as conn:
                    with conn.cursor() as cur:
                        cur.execute(sql, params)
                        return cur.fetchall()
            except psycopg2.Error as exc:
                last = exc
                time.sleep(3)
        raise last

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    topics = {k: v for k, v in TOPICS.items() if not args.topics or k in args.topics}

    print(f"Rentang: {start} -> {end} | topik: {len(topics)} | dry-run: {args.dry_run}")

    model = None if args.dry_run else setup_gemini()

    total_written = 0
    for topic, (news_sheets, summary_sheet) in topics.items():
        print(f"\n{'=' * 60}\n[{topic}] -> {summary_sheet}\n{'=' * 60}")

        # Artikel per hari — query ringan (hanya date+content dalam rentang),
        # bukan SELECT * seluruh topik (39 MB+ memutus koneksi Neon free tier)
        rows = []
        for sheet in news_sheets:
            rows += _query(
                """SELECT date::date, content FROM news_articles
                   WHERE topic = %s AND content IS NOT NULL
                     AND date::date BETWEEN %s AND %s""",
                (sheet, start, end),
            )
        if not rows:
            print("  (tidak ada artikel dalam rentang, lewati)")
            continue
        articles = pd.DataFrame(rows, columns=["date", "content"])
        articles["date"] = pd.to_datetime(articles["date"])

        # Periode (hari atau minggu, tergantung cadence topik) yang sudah punya summary
        have_starts = {r[0] for r in _query(
            'SELECT "Tanggal awal" FROM news_sentiment WHERE topic = %s',
            (summary_sheet,),
        )}

        for win_name, win_start, win_end in topic_windows(topic, start, end):
            if win_start in have_starts:
                continue
            mask = (articles["date"] >= pd.Timestamp(win_start)) & (articles["date"] <= pd.Timestamp(win_end))
            window_articles = articles.loc[mask, "content"].astype(str).tolist()
            if not window_articles:
                continue
            print(f"  [{win_name}] {win_start} -> {win_end}: {len(window_articles)} artikel -> summarize", flush=True)
            if not args.dry_run:
                try:
                    summary = summarize_all_news(
                        model, window_articles, pd.Timestamp(win_start), pd.Timestamp(win_end),
                        news_sheets, ROLE_PROMPT, SPESIFIC_PROMPT,
                    )
                    if summary:
                        row = pd.DataFrame([{
                            "Tanggal awal": win_start,
                            "Tanggal akhir": win_end,
                            "Summary": summary,
                            "Summary Data": None,
                        }])
                        storage.write_sentiment_file({summary_sheet: row})
                        total_written += 1
                except Exception as exc:
                    print(f"    ERROR: {exc}")
                time.sleep(args.delay)
            else:
                total_written += 1

    print(f"\nSELESAI. Summary {'akan ' if args.dry_run else ''}ditulis: {total_written}")


if __name__ == "__main__":
    main()
