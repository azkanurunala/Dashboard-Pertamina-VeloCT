"""repair_summary_data.py -- Fill NULL "Summary Data" in news_sentiment for Biodiesel/Bioetanol/SAF.

Those weekly rows had no "Summary Data" (CPO/Biodiesel/Bioetanol/SAF vs. prior
period comparison) because they were created by backfill_sentiment_daily.py,
which only fills the gap-filling "Summary" text and always hardcodes
"Summary Data": None -- it never runs the comparison logic that
main_sentiment_news_mingguan.py's production run has. This script reuses that
exact production logic (_get_comparison / _get_comparison_bioetanol /
_get_comparison_saf) and walks each topic chronologically, filling NULL rows
in order so a same-month "copy previous period" correctly sees the
just-repaired previous value instead of the stale None (see the
_get_prev_period / _latest_row fix in that module for the matching
forward-looking bug).

Usage:
    python scripts/repair_summary_data.py                # dry run, report only
    python scripts/repair_summary_data.py --execute       # backup + write UPDATEs
    python scripts/repair_summary_data.py --selftest
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

from dotenv import load_dotenv

load_dotenv(SCRIPT_DIR.parent / ".env")
os.environ["STORAGE_BACKEND"] = "neon"

import pandas as pd  # noqa: E402

BACKUP_DIR = SCRIPT_DIR / "backups"

TOPIC_SHEET = {
    "Biodiesel": "(Summary)Biodiesel",
    "Bioetanol": "(Summary)Bioetanol",
    "SAF": "(Summary)SAF",
}


def _fmt_pct(value: float | None) -> str:
    return f"{abs(value):.2f}%" if value is not None else "N/A"


def _trend(value: float | None) -> str:
    if value is None:
        return "tidak tersedia"
    return "kenaikan" if value >= 0 else "penurunan"


def compute_biodiesel(start, end, start_prev, end_prev, prev_summary_data):
    from orchestrators.main_sentiment_news_mingguan import _get_comparison

    comparison = _get_comparison(start, end, start_prev, end_prev)
    if comparison["same_month"]:
        return prev_summary_data
    if comparison["cpo"] is None or comparison["bio"] is None:
        return None
    cpo_trend = "kenaikan" if comparison["cpo_change"] >= 0 else "penurunan"
    bio_trend = "kenaikan" if comparison["bio_change"] >= 0 else "penurunan"
    return (
        f"Pada periode {start.month}/{start.day}/{start.year} sampai "
        f"{end.month}/{end.day}/{end.year}, "
        f"rata-rata CPO {comparison['cpo']:.2f} dan rata-rata Biodiesel {comparison['bio']:.2f}. "
        f"Periode ini mengalami {cpo_trend} {abs(comparison['cpo_change']):.2f}% nilai CPO "
        f"dan {bio_trend} {abs(comparison['bio_change']):.2f}% biodiesel dibanding bulan sebelumnya."
    )


def compute_bioetanol(start, end, start_prev, end_prev, prev_summary_data):
    from orchestrators.main_sentiment_news_mingguan import _get_comparison_bioetanol

    comparison = _get_comparison_bioetanol(start, end, start_prev, end_prev)
    if comparison["same_month"]:
        return prev_summary_data
    if comparison["bioetanol"] is None or comparison["tetes_tebu"] is None:
        return None
    bioetanol_trend = "kenaikan" if comparison["bioetanol_change"] >= 0 else "penurunan"
    tetes_trend = "kenaikan" if comparison["tetes_change"] >= 0 else "penurunan"
    return (
        f"Pada bulan {end.strftime('%B %Y')}, "
        f"rata-rata Bioetanol {comparison['bioetanol']:.2f} dan rata-rata Tetes Tebu {comparison['tetes_tebu']:.2f}. "
        f"Periode ini mengalami {bioetanol_trend} {abs(comparison['bioetanol_change']):.2f}% nilai Bioetanol "
        f"dan {tetes_trend} {abs(comparison['tetes_change']):.2f}% Tetes Tebu dibanding bulan sebelumnya."
    )


def compute_saf(start, end, start_prev, end_prev, prev_summary_data):
    from orchestrators.main_sentiment_news_mingguan import _get_comparison_saf

    comparison = _get_comparison_saf(start, end, start_prev, end_prev)
    if comparison["saf"] is None or comparison["uco"] is None:
        return None
    return (
        f"Pada periode {start.month}/{start.day}/{start.year} sampai "
        f"{end.month}/{end.day}/{end.year}, "
        f"rata-rata SAF tercatat {comparison['saf']:.2f} dan rata-rata UCO {comparison['uco']:.2f}. "
        f"Secara periodik, SAF mengalami {_trend(comparison['saf_change'])} {_fmt_pct(comparison['saf_change'])} "
        f"dan UCO mengalami {_trend(comparison['uco_change'])} {_fmt_pct(comparison['uco_change'])} dibanding periode sebelumnya."
    )


COMPUTE = {"Biodiesel": compute_biodiesel, "Bioetanol": compute_bioetanol, "SAF": compute_saf}


def repair_topic(topic: str, df_topic: pd.DataFrame) -> list[tuple[int, str]]:
    """Walk rows chronologically, filling NULL "Summary Data". Returns [(id, new_value), ...]."""
    df_topic = df_topic.sort_values("Tanggal awal").reset_index(drop=True)
    fn = COMPUTE[topic]

    updates: list[tuple[int, str]] = []
    prev_start = prev_end = prev_summary = None
    for _, row in df_topic.iterrows():
        start = pd.Timestamp(row["Tanggal awal"])
        end = pd.Timestamp(row["Tanggal akhir"])
        current_summary = row["Summary Data"] if pd.notna(row["Summary Data"]) else None

        if current_summary is None and prev_start is not None:
            new_val = fn(start, end, prev_start, prev_end, prev_summary)
            if new_val is not None:
                updates.append((int(row["id"]), new_val))
                current_summary = new_val

        prev_start, prev_end, prev_summary = start, end, current_summary

    return updates


def _selftest() -> None:
    """python scripts/repair_summary_data.py --selftest"""
    calls = []

    def fake_fn(start, end, start_prev, end_prev, prev_summary):
        calls.append((start, end, start_prev, end_prev, prev_summary))
        return f"computed-{end.date()}"

    COMPUTE["_fake"] = fake_fn
    df = pd.DataFrame([
        {"id": 1, "Tanggal awal": pd.Timestamp("2026-01-01"), "Tanggal akhir": pd.Timestamp("2026-01-07"), "Summary Data": "existing"},
        {"id": 2, "Tanggal awal": pd.Timestamp("2026-01-08"), "Tanggal akhir": pd.Timestamp("2026-01-14"), "Summary Data": None},
        {"id": 3, "Tanggal awal": pd.Timestamp("2026-01-15"), "Tanggal akhir": pd.Timestamp("2026-01-21"), "Summary Data": None},
    ])
    updates = repair_topic("_fake", df)
    del COMPUTE["_fake"]

    # Row 1 already has data -> skipped, no call made for it.
    assert [u[0] for u in updates] == [2, 3], updates
    assert updates[0][1] == "computed-2026-01-14", updates
    # Row 3's call must see row 2's freshly computed value, not the stale None
    # that was in the DB before this run -- that's the forward-cascade fix.
    assert calls[1][4] == "computed-2026-01-14", calls

    # No previous period at all (first row NULL, nothing before it) -> left alone.
    df2 = pd.DataFrame([
        {"id": 9, "Tanggal awal": pd.Timestamp("2026-01-01"), "Tanggal akhir": pd.Timestamp("2026-01-07"), "Summary Data": None},
    ])
    COMPUTE["_fake"] = fake_fn
    assert repair_topic("_fake", df2) == []
    del COMPUTE["_fake"]

    print("_selftest OK")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--execute", action="store_true", help="actually UPDATE the DB (default: dry run / report only)")
    args = ap.parse_args()

    from helpers import neon_helper

    df = neon_helper.read_table("news_sentiment")

    all_updates: list[tuple[int, str]] = []
    for topic, sheet in TOPIC_SHEET.items():
        sub = df[df["topic"] == sheet]
        updates = repair_topic(topic, sub)
        if not updates:
            continue
        print(f"\n=== {sheet} === ({len(updates)} row(s) to fill)")
        for id_, val in updates:
            preview = val if len(val) <= 90 else val[:87] + "..."
            print(f"  id={id_}: {preview}")
        all_updates.extend(updates)

    print(f"\n{'=' * 60}")
    print(f"TOTAL rows to update: {len(all_updates)}")

    if not all_updates:
        print("Nothing to do.")
        return

    if not args.execute:
        print("DRY RUN -- nothing written. Re-run with --execute to apply.")
        return

    BACKUP_DIR.mkdir(exist_ok=True)
    ids = [i for i, _ in all_updates]
    backup_path = BACKUP_DIR / f"news_sentiment_summary_data_repair_{datetime.now():%Y%m%d_%H%M%S}.csv"
    df[df["id"].isin(ids)].to_csv(backup_path, index=False)
    print(f"Backup (pre-repair state) written: {backup_path}")

    import psycopg2

    with psycopg2.connect(os.environ["NEON_DB_URL"]) as conn:
        with conn.cursor() as cur:
            for id_, val in all_updates:
                cur.execute('UPDATE news_sentiment SET "Summary Data" = %s WHERE id = %s', (val, id_))
        conn.commit()
    print(f"Updated {len(all_updates)} row(s).")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
