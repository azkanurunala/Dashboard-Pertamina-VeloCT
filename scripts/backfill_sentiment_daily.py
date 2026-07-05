"""backfill_sentiment_daily.py -- Backfill DAILY Gemini summaries for all topics.

The production sentiment orchestrators only move forward from the latest
"Tanggal akhir" per topic, so historical gaps are never filled. This script
walks a historical date range and, for every (topic, day) that has articles
in news_articles but no row in news_sentiment, generates a one-day summary
and upserts it (conflict key: topic + "Tanggal awal").

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


def month_windows(start: date, end: date) -> list[tuple[str, date, date]]:
    """30-day windows, newest first, covering [start, end]."""
    windows = []
    n = 1
    win_end = end
    while win_end >= start:
        win_start = max(start, win_end - timedelta(days=29))
        windows.append((f"bulan-{n}", win_start, win_end))
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

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    topics = {k: v for k, v in TOPICS.items() if not args.topics or k in args.topics}

    print(f"Rentang: {start} -> {end} | topik: {len(topics)} | dry-run: {args.dry_run}")

    model = None if args.dry_run else setup_gemini()
    windows = month_windows(start, end)

    total_written = 0
    for topic, (news_sheets, summary_sheet) in topics.items():
        print(f"\n{'=' * 60}\n[{topic}] -> {summary_sheet}\n{'=' * 60}")

        # Artikel per hari
        frames = []
        for sheet in news_sheets:
            df = storage.read_news_sheet(sheet)
            if not df.empty and "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
                frames.append(df[["date", "content"]].dropna())
        if not frames:
            print("  (tidak ada artikel sama sekali, lewati)")
            continue
        articles = pd.concat(frames, ignore_index=True)

        # Hari yang sudah punya summary
        existing = storage.read_sentiment_sheet(summary_sheet)
        have_days: set = set()
        if not existing.empty and "Tanggal awal" in existing.columns:
            have_days = set(pd.to_datetime(existing["Tanggal awal"], errors="coerce").dt.date.dropna())

        for win_name, win_start, win_end in windows:
            day = win_end
            while day >= win_start:
                if day not in have_days:
                    day_ts = pd.Timestamp(day)
                    day_articles = articles[articles["date"] == day_ts]["content"].astype(str).tolist()
                    if day_articles:
                        print(f"  [{win_name}] {day}: {len(day_articles)} artikel -> summarize", flush=True)
                        if not args.dry_run:
                            try:
                                summary = summarize_all_news(
                                    model, day_articles, day_ts, day_ts,
                                    news_sheets, ROLE_PROMPT, SPESIFIC_PROMPT,
                                )
                                if summary:
                                    row = pd.DataFrame([{
                                        "Tanggal awal": day,
                                        "Tanggal akhir": day,
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
                day -= timedelta(days=1)

    print(f"\nSELESAI. Summary {'akan ' if args.dry_run else ''}ditulis: {total_written}")


if __name__ == "__main__":
    main()
