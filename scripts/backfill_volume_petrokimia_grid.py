"""backfill_volume_petrokimia_grid.py -- One-off catch-up for (Summary)Volume Petrokimia,
realigned to the same Tue-Mon weekly grid every other weekly topic already uses.

Volume Petrokimia's last real row ended 2026-05-07 (Thu). Continuing naturally
(start = last_end + 1, the normal production behavior) would anchor its
weekly grid to Friday -- permanently offset ~4 days from every other topic's
Tue-Mon grid (e.g. "21-27 Jul, 28 Jul-3 Aug"). Instead of drifting forward
from May 7, this hardcodes the same Tue-Mon windows the rest of the pipeline
already settled on and fills them directly. Once these rows exist, future
production runs (which just do last_end+1 from here on) naturally stay on
that same grid -- no ongoing special-casing needed.

Source news: (News)Crackspread Non-BBM (shared with Crackspread_Non_BBM --
see TOPICS["Volume_Petrokimia"] in main_sentiment_news_mingguan.py). Uses that
same volume-focused prompt so the text doesn't duplicate Crackspread_Non_BBM's
(the original "2 summary rows per date" complaint, QA Revisi II).

Usage:
    python scripts/backfill_volume_petrokimia_grid.py             # dry run: windows + article counts only
    python scripts/backfill_volume_petrokimia_grid.py --execute    # call Gemini + write rows
    python scripts/backfill_volume_petrokimia_grid.py --selftest
"""

import argparse
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

from dotenv import load_dotenv

load_dotenv(SCRIPT_DIR.parent / ".env")
os.environ["STORAGE_BACKEND"] = "neon"

import pandas as pd  # noqa: E402

TOPIC = "(Summary)Volume Petrokimia"
NEWS_SHEET = "(News)Crackspread Non-BBM"
MAX_NEWS_PER_TOPIC = 200  # mirror main_sentiment_news_mingguan.py

# Same Tue-Mon grid every other weekly topic already ends on (verified against
# (Summary)BI-Rate / Biodiesel / etc post-dedupe: latest row = 2026-07-28 -> 2026-08-03).
GRID_ANCHOR_START = date(2026, 7, 28)  # start of the newest window in that shared grid
LAST_REAL_END = date(2026, 4, 20)      # 2nd run: old Fri-Thu rows (17 Apr-7 May) deleted,
                                        # regenerate on the Tue-Mon grid from 21 Apr onward
                                        # so it connects with zero gap into 12 May.


def grid_windows(anchor_start: date, stop_after: date) -> list[tuple[date, date]]:
    """Tue-Mon windows walking backward from anchor_start, down to (not including) stop_after."""
    windows = []
    start = anchor_start
    while start > stop_after:
        windows.append((start, start + timedelta(days=6)))
        start -= timedelta(days=7)
    windows.reverse()
    return windows


def _selftest() -> None:
    """python scripts/backfill_volume_petrokimia_grid.py --selftest"""
    windows = grid_windows(date(2026, 7, 28), date(2026, 5, 7))
    assert windows[0] == (date(2026, 5, 12), date(2026, 5, 18)), windows[0]
    assert windows[-1] == (date(2026, 7, 28), date(2026, 8, 3)), windows[-1]
    assert len(windows) == 12, len(windows)
    # Contiguous, no overlap: each window starts exactly 7 days after the previous.
    for (s1, e1), (s2, e2) in zip(windows, windows[1:]):
        assert (s2 - s1).days == 7, (s1, s2)
        assert e1 < s2, (e1, s2)
    print("_selftest OK")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--execute", action="store_true", help="call Gemini and write rows (default: dry run / article counts only)")
    ap.add_argument("--delay", type=float, default=4.0, help="seconds between Gemini calls")
    args = ap.parse_args()

    from helpers import neon_helper

    windows = grid_windows(GRID_ANCHOR_START, LAST_REAL_END)
    print(f"Grid: {len(windows)} window(s), {windows[0][0]} -> {windows[-1][1]}")

    existing = neon_helper.read_table("news_sentiment", topic=TOPIC)
    have_starts = set(pd.to_datetime(existing["Tanggal awal"]).dt.date) if not existing.empty else set()

    articles_df = neon_helper.read_table("news_articles", topic=NEWS_SHEET)
    articles_df["date"] = pd.to_datetime(articles_df["date"], errors="coerce")

    plan: list[tuple[date, date, list[str]]] = []
    for start, end in windows:
        if start in have_starts:
            print(f"  {start} -> {end}: sudah ada row -> SKIP")
            continue
        mask = (articles_df["date"] >= pd.Timestamp(start)) & (articles_df["date"] <= pd.Timestamp(end))
        window_articles = articles_df.loc[mask, "content"].dropna().astype(str).tolist()
        note = " -> SKIP (kosong)" if not window_articles else ""
        print(f"  {start} -> {end}: {len(window_articles)} artikel{note}")
        if window_articles:
            plan.append((start, end, window_articles[:MAX_NEWS_PER_TOPIC]))

    if not args.execute:
        print(f"\nDRY RUN -- {len(plan)} row akan digenerate. Re-run dengan --execute buat beneran jalanin.")
        return

    from helpers.storage_backend import storage
    from helpers.summary_helper import setup_gemini, summarize_all_news
    from orchestrators.main_sentiment_news_mingguan import TOPICS

    cfg = TOPICS["Volume_Petrokimia"]
    model = setup_gemini()

    written = 0
    for start, end, window_articles in plan:
        print(f"\n[{start} -> {end}] {len(window_articles)} artikel -> summarize...", flush=True)
        try:
            summary = summarize_all_news(
                model, window_articles, pd.Timestamp(start), pd.Timestamp(end),
                cfg["target_sheets"], cfg["role_prompt"], cfg["spesific_prompt"],
            )
            if summary:
                row = pd.DataFrame([{
                    "Tanggal awal": start,
                    "Tanggal akhir": end,
                    "Summary": summary,
                    "Summary Data": None,
                }])
                storage.write_sentiment_file({TOPIC: row})
                written += 1
        except Exception as exc:
            print(f"  ERROR: {exc}")
        time.sleep(args.delay)

    print(f"\nSELESAI. {written}/{len(plan)} row ditulis ke {TOPIC}.")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
