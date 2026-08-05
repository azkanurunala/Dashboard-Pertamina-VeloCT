"""dedupe_weekly_summary_overlaps.py -- Remove overlapping date ranges from news_sentiment (weekly topics only).

Root cause: news_sentiment's upsert conflict key is (topic, "Tanggal awal") only
(see storage_backend.py _NeonBackend.write_sentiment_file). Multiple pipeline/
backfill reruns over time computed different "Tanggal awal" anchors for the same
topic, so rows never collided on conflict -- they piled up as overlapping windows
instead of one clean weekly sequence (e.g. 21-27 Jul should be followed by
28 Jul-3 Aug, not by a handful of other runs' 23-29 Jul / 25-31 Jul variants).

Algorithm per topic (classic interval-scheduling maximization, anchored on the
newest row so the current/latest period is never dropped):
  1. Anchor = row with the latest "Tanggal akhir" (ties -> highest id).
  2. Walk backward: from all rows ending strictly before the current row's
     start, keep the one with the LATEST end date (tightest, non-overlapping
     fit). This is exactly the contiguous predecessor when one exists.
  3. Repeat until no non-overlapping predecessor remains.
  4. Any row never picked is an overlap duplicate -> delete candidate.

This only removes overlaps. Genuine gaps (a topic has no article-derived
summary for some week) are left alone -- the walk simply jumps back over them
without deleting anything, since a gap has no overlapping row to begin with.

Usage:
    python scripts/dedupe_weekly_summary_overlaps.py                  # dry run, all weekly topics
    python scripts/dedupe_weekly_summary_overlaps.py --topics "(Summary)BI-Rate"
    python scripts/dedupe_weekly_summary_overlaps.py --execute         # actually DELETE
    python scripts/dedupe_weekly_summary_overlaps.py --selftest
"""

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

from dotenv import load_dotenv

load_dotenv(SCRIPT_DIR.parent / ".env")
os.environ["STORAGE_BACKEND"] = "neon"

# Daily-cadence topics (1-day windows) -- never overlap by construction, skip them.
# Mirrors DAILY_TOPICS' summary sheets in backfill_sentiment_daily.py.
DAILY_SHEETS = {"(Summary)Nilai Tukar Rupiah", "(Summary)IHSG", "(Summary)Indonia", "(Summary)Idx Volatilitas"}

BACKUP_DIR = SCRIPT_DIR / "backups"


@dataclass(frozen=True)
class Row:
    id: int
    start: date
    end: date


def resolve_overlaps(rows: list[Row]) -> tuple[list[Row], list[Row]]:
    """Return (keep, delete), both sorted by start ascending."""
    if not rows:
        return [], []

    by_id = {r.id: r for r in rows}
    anchor = max(rows, key=lambda r: (r.end, r.id))

    keep = [anchor]
    current = anchor
    while True:
        candidates = [r for r in rows if r.end < current.start]
        if not candidates:
            break
        nxt = max(candidates, key=lambda r: (r.end, r.id))
        keep.append(nxt)
        current = nxt

    keep_ids = {r.id for r in keep}
    delete = [r for r in rows if r.id not in keep_ids]
    keep.sort(key=lambda r: r.start)
    delete.sort(key=lambda r: r.start)
    return keep, delete


def _selftest() -> None:
    """python scripts/dedupe_weekly_summary_overlaps.py --selftest"""
    # Mirrors the real BI-Rate overlap pattern: a clean weekly chain plus stray
    # rows from other runs that overlap it.
    rows = [
        Row(1, date(2026, 7, 7), date(2026, 7, 13)),
        Row(2, date(2026, 7, 10), date(2026, 7, 16)),   # overlaps 1 and 3 -> delete
        Row(3, date(2026, 7, 14), date(2026, 7, 20)),
        Row(4, date(2026, 7, 21), date(2026, 7, 27)),
        Row(5, date(2026, 7, 28), date(2026, 8, 3)),    # anchor (latest end)
    ]
    keep, delete = resolve_overlaps(rows)
    assert [r.id for r in keep] == [1, 3, 4, 5], keep
    assert [r.id for r in delete] == [2], delete

    # Genuine gap (no row at all for 11-21..11-27): both sides kept, nothing deleted.
    gap_rows = [
        Row(10, date(2025, 11, 14), date(2025, 11, 20)),
        Row(11, date(2025, 11, 28), date(2025, 12, 4)),
    ]
    keep, delete = resolve_overlaps(gap_rows)
    assert [r.id for r in keep] == [10, 11], keep
    assert delete == [], delete

    # Tie on end date among non-overlapping candidates -> higher id wins, only one kept.
    tie_rows = [
        Row(20, date(2026, 1, 1), date(2026, 1, 7)),
        Row(21, date(2025, 12, 20), date(2025, 12, 31)),  # same end as 22, lower id -> dropped
        Row(22, date(2025, 12, 15), date(2025, 12, 31)),
    ]
    keep, delete = resolve_overlaps(tie_rows)
    assert [r.id for r in keep] == [22, 20], keep
    assert [r.id for r in delete] == [21], delete

    print("_selftest OK")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topics", nargs="+", help="subset of topic (summary sheet) names, e.g. \"(Summary)BI-Rate\"")
    ap.add_argument("--execute", action="store_true", help="actually DELETE the overlap rows (default: dry run / report only)")
    args = ap.parse_args()

    from helpers import neon_helper

    df = neon_helper.read_table("news_sentiment")
    df = df[~df["topic"].isin(DAILY_SHEETS)]
    if args.topics:
        df = df[df["topic"].isin(args.topics)]

    all_delete_ids: list[int] = []
    for topic, sub in df.groupby("topic"):
        rows = [
            Row(int(r["id"]), r["Tanggal awal"], r["Tanggal akhir"])
            for _, r in sub.iterrows()
        ]
        keep, delete = resolve_overlaps(rows)
        if not delete:
            continue

        print(f"\n=== {topic} === ({len(rows)} rows -> keep {len(keep)}, delete {len(delete)})")
        for r in delete:
            print(f"  DELETE id={r.id:<5} {r.start} -> {r.end}")
        all_delete_ids.extend(r.id for r in delete)

    print(f"\n{'=' * 60}")
    print(f"TOTAL rows to delete: {len(all_delete_ids)}")

    if not all_delete_ids:
        print("Nothing to do.")
        return

    if not args.execute:
        print("DRY RUN -- nothing deleted. Re-run with --execute to apply.")
        return

    BACKUP_DIR.mkdir(exist_ok=True)
    backup_path = BACKUP_DIR / f"news_sentiment_overlap_deletes_{datetime.now():%Y%m%d_%H%M%S}.csv"
    df[df["id"].isin(all_delete_ids)].to_csv(backup_path, index=False)
    print(f"Backup written: {backup_path} ({len(all_delete_ids)} row(s))")

    import psycopg2

    with psycopg2.connect(os.environ["NEON_DB_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM news_sentiment WHERE id = ANY(%s)', (all_delete_ids,))
            print(f"Deleted {cur.rowcount} row(s).")
        conn.commit()


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
