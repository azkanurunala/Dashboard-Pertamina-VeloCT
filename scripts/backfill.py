"""
backfill.py -- Close data gap Oct 2025 -> Jun 2026.

Run locally with STORAGE_BACKEND=neon and a full .env file.
Progress is saved to scripts/backfill_progress.json after each unit of work,
so the script can be interrupted and resumed.

Usage examples:
    # Full backfill (all sources, Oct 2025 -> Jun 2026)
    python scripts/backfill.py

    # Specific sources only
    python scripts/backfill.py --sources eia spglobal_saf news_lokal

    # Custom date range
    python scripts/backfill.py --start 2025-10-01 --end 2025-12-31

    # Resume news loop from a specific date (overrides progress file)
    python scripts/backfill.py --sources news_lokal --resume-from 2026-01-15

    # Slower request rate to reduce ban risk
    python scripts/backfill.py --delay 5.0

Available --sources values:
    Tier 1 (self-healing, run once):
        eia, biodiesel_esdm, bioetanol_esdm, migas_esdm, iaea, wte, cpo, kapasitas_ebt
    Tier 2 (S&P Global with explicit date range):
        spglobal_saf,
        spglobal_petrochemical, spglobal_forecast_bbm_short, spglobal_forecast_bbm_long
    Tier 3 (news, daily loop):
        news_lokal, news_intl
    Tier 4 (Kompas historical sitemaps, month loop):
        kompas_monthly
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

os.environ["STORAGE_BACKEND"] = "neon"  # backfill selalu ke Neon, override .env
load_dotenv()

SCRIPT_DIR = Path(__file__).parent
SRC_DIR    = SCRIPT_DIR.parent / "src"
sys.path.insert(0, str(SRC_DIR))

PROGRESS_FILE = SCRIPT_DIR / "backfill_progress.json"

TIER1_SOURCES = {
    "eia",
    "biodiesel_esdm",
    "bioetanol_esdm",
    "migas_esdm",
    "iaea",
    "wte",
    "cpo",
    "kapasitas_ebt",
}

TIER2_SOURCES = {
    "spglobal_saf",
    "spglobal_petrochemical",
    "spglobal_forecast_bbm_short",
    "spglobal_forecast_bbm_long",
}

ALL_SOURCES = TIER1_SOURCES | TIER2_SOURCES | {
    "news_lokal", "news_intl", "kompas_monthly"
}


# ── Progress ──────────────────────────────────────────────────────────────────

def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text())
        except Exception:
            pass
    return {
        "started_at":                  None,
        "completed_sources":           [],
        "last_completed_date_lokal":   None,
        "last_completed_date_intl":    None,
        "completed_kompas_months":     [],
    }


def save_progress(progress: dict) -> None:
    """Merge with on-disk state before writing.

    Multiple backfill.py invocations (different --sources/date ranges) can
    run concurrently and share this one progress file. A blind overwrite
    lets whichever process saves last clobber further-along progress from
    another process. Union-merging keeps progress moving forward only,
    regardless of write order or how many instances run at once.
    """
    disk = {}
    if PROGRESS_FILE.exists():
        try:
            disk = json.loads(PROGRESS_FILE.read_text())
        except Exception:
            pass

    # Mutate in place -- callers hold references to these lists (e.g.
    # `completed = progress["completed_sources"]`) and keep appending to them.
    progress["completed_sources"][:] = sorted(
        set(progress.get("completed_sources", [])) | set(disk.get("completed_sources", []))
    )
    progress["completed_kompas_months"][:] = sorted(
        set(progress.get("completed_kompas_months", [])) | set(disk.get("completed_kompas_months", []))
    )
    for key in ("last_completed_date_lokal", "last_completed_date_intl"):
        candidates = [v for v in (progress.get(key), disk.get(key)) if v]
        progress[key] = max(candidates) if candidates else None
    if disk.get("started_at") and (not progress.get("started_at") or disk["started_at"] < progress["started_at"]):
        progress["started_at"] = disk["started_at"]

    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


# ── Date utilities ────────────────────────────────────────────────────────────

def date_range(start: str, end: str) -> list[str]:
    d = datetime.strptime(start, "%Y-%m-%d").date()
    e = datetime.strptime(end,   "%Y-%m-%d").date()
    out = []
    while d <= e:
        out.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    return out


def month_range(start: str, end: str) -> list[tuple[int, int]]:
    d = datetime.strptime(start, "%Y-%m-%d").date().replace(day=1)
    e = datetime.strptime(end,   "%Y-%m-%d").date().replace(day=1)
    out = []
    while d <= e:
        out.append((d.year, d.month))
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return out


def should_run(name: str, selected: list[str] | None) -> bool:
    if not selected:
        return True
    return name in selected or "all" in selected


# ── Tier 1: Self-healing structured data (run once) ──────────────────────────

TIER1_IMPORTS = {
    "eia":            ("structured_data.migas_eia",        "main_eia"),
    "biodiesel_esdm": ("structured_data.biodiesel_esdm",   "main_biodiesel_esdm"),
    "bioetanol_esdm": ("structured_data.bioetanol_esdm",   "main_bioetanol_esdm"),
    "migas_esdm":     ("structured_data.migas_esdm",       "main_price_esdm"),
    "iaea":           ("structured_data.nuclear_iaea_pris", "main_iaea_scraper"),
    "wte":            ("structured_data.wte_sipsn",        "main_sipsn_scraper"),
    "cpo":            ("structured_data.cpo_gapki",        "main_scraper_cpo"),
    # NOTE: EBTKE API only exposes the current latest month, no historical
    # range -- this only captures whatever is "latest" right now, it cannot
    # backfill past missing months.
    "kapasitas_ebt":  ("structured_data.kapasitas_esdm",   "main_ebtke_scraper"),
}


def run_tier1(args, progress: dict) -> None:
    import importlib

    completed = progress["completed_sources"]

    for name, (module_path, func_name) in TIER1_IMPORTS.items():
        if not should_run(name, args.sources):
            continue
        if name in completed:
            print(f"[Tier1] {name}: already completed, skipping")
            continue

        print(f"\n{'='*60}")
        print(f"[Tier1] {name}")
        print(f"{'='*60}")
        try:
            mod  = importlib.import_module(module_path)
            func = getattr(mod, func_name)
            func()
            completed.append(name)
            save_progress(progress)
            print(f"[Tier1] {name}: done")
        except Exception as exc:
            print(f"[Tier1] {name}: ERROR -- {exc}")


# ── Tier 2: S&P Global with explicit date range ───────────────────────────────

def run_tier2(args, progress: dict) -> None:
    from structured_data.spglobal_data import (
        main_saf_weekly,
        main_petrochemical_short_term,
        main_price_forecast_short_term_bbm,
        main_price_forecast_long_term_bbm,
    )

    months = month_range(args.start, args.end)
    (start_year, start_month), (end_year, end_month) = months[0], months[-1]

    tier2_funcs = {
        "spglobal_saf":              lambda: main_saf_weekly(args.start, args.end),
        "spglobal_petrochemical":    lambda: main_petrochemical_short_term(start_year, start_month, end_year, end_month),
        "spglobal_forecast_bbm_short": lambda: main_price_forecast_short_term_bbm(start_year, start_month, end_year, end_month),
        "spglobal_forecast_bbm_long": lambda: main_price_forecast_long_term_bbm(start_year, end_year),
    }

    completed = progress["completed_sources"]

    for name, func in tier2_funcs.items():
        if not should_run(name, args.sources):
            continue
        if name in completed:
            print(f"[Tier2] {name}: already completed, skipping")
            continue

        print(f"\n{'='*60}")
        print(f"[Tier2] {name} ({args.start} -> {args.end})")
        print(f"{'='*60}")
        try:
            func()
            completed.append(name)
            save_progress(progress)
            print(f"[Tier2] {name}: done")
        except Exception as exc:
            print(f"[Tier2] {name}: ERROR -- {exc}")


# ── Tier 3: News daily loop ───────────────────────────────────────────────────

def _run_news_loop(
    label: str,
    orchestrator_module: str,
    progress_key: str,
    args,
    progress: dict,
) -> None:
    """Generic news backfill loop. Imports ACTIVE_SHEETS/scrape_keyword from
    the given orchestrator module and iterates date_range(args.start, args.end).
    Saves each scraped DataFrame directly to Neon after every keyword."""
    import importlib
    import pandas as pd

    mod = importlib.import_module(orchestrator_module)
    ACTIVE_SHEETS   = mod.ACTIVE_SHEETS
    SHEET_TO_KEYWORD = mod.SHEET_TO_KEYWORD
    scrape_keyword  = mod.scrape_keyword

    from helpers.storage_backend import storage
    # scrape_keyword (lokal orchestrator) reuses one Selenium driver per
    # source across the whole loop instead of relaunching per keyword --
    # close_driver() is a no-op if that source was never used, so calling
    # both unconditionally is safe for the internasional orchestrator too.
    from news.bank_indonesia import close_driver as close_bank_indonesia_driver
    from news.cnbc_id import close_driver as close_cnbc_driver

    dates       = date_range(args.start, args.end)
    last_done   = args.resume_from or progress.get(progress_key)

    print(f"\n{'='*60}")
    print(f"[{label}] {len(dates)} dates: {dates[0]} -> {dates[-1]}")
    if last_done:
        print(f"[{label}] Resuming from after: {last_done}")
    print(f"{'='*60}")

    try:
        for date_idx, tanggal in enumerate(dates, 1):
            if last_done and tanggal <= last_done:
                continue

            print(f"\n{'='*60}")
            print(f"[{label}] {date_idx}/{len(dates)}: {tanggal}")
            print(f"{'='*60}")

            for sheet_name in ACTIVE_SHEETS:
                keyword = SHEET_TO_KEYWORD.get(sheet_name)
                if not keyword:
                    continue

                print(f"  [{sheet_name}] keyword={keyword}")
                try:
                    hasil = scrape_keyword(keyword, tanggal)
                    if hasil is not None and not getattr(hasil, "empty", True):
                        storage.write_news_file({sheet_name: hasil})
                        print(f"  -> saved {len(hasil)} rows")
                except Exception as exc:
                    print(f"  -> ERROR: {exc}")

                time.sleep(args.delay)

            progress[progress_key] = tanggal
            save_progress(progress)
            print(f"[{label}] saved progress: {tanggal}")
            time.sleep(args.delay)
    finally:
        close_cnbc_driver()
        close_bank_indonesia_driver()


def run_news_lokal(args, progress: dict) -> None:
    _run_news_loop(
        label="News Lokal",
        orchestrator_module="orchestrators.main_news_scraping_lokal",
        progress_key="last_completed_date_lokal",
        args=args,
        progress=progress,
    )


def run_news_intl(args, progress: dict) -> None:
    _run_news_loop(
        label="News Intl",
        orchestrator_module="orchestrators.main_news_scraping_internasional",
        progress_key="last_completed_date_intl",
        args=args,
        progress=progress,
    )


# ── Tier 4: Kompas historical monthly sitemaps ────────────────────────────────

def run_kompas_monthly(args, progress: dict) -> None:
    """Backfill Kompas articles using historical monthly sitemaps.

    Regular scraping only sees the live sitemap (current week). This function
    fetches the /sitemap-news-{section}-{YYYY}-{MM}.xml URLs that Kompas keeps
    for past months, so we can recover articles from the gap period.
    """
    import pandas as pd

    from helpers.storage_backend import storage
    from helpers.scraping_utils import rename_to_standard_columns
    from news.kompas import (
        find_articles_in_monthly_sitemap,
        fetch_article_content,
        CONTENT_FETCH_DELAY,
    )
    from orchestrators.main_news_scraping_lokal import ACTIVE_SHEETS, SHEET_TO_KEYWORD

    completed_months: set[str] = set(progress.get("completed_kompas_months", []))
    months = month_range(args.start, args.end)

    print(f"\n{'='*60}")
    print(f"[Kompas Monthly] {len(months)} months: {months[0]} -> {months[-1]}")
    print(f"{'='*60}")

    for year, month in months:
        month_key = f"{year}-{month:02d}"
        if month_key in completed_months:
            print(f"[Kompas Monthly] {month_key}: already done, skipping")
            continue

        print(f"\n[Kompas Monthly] Processing {month_key}")

        for sheet_name in ACTIVE_SHEETS:
            keyword = SHEET_TO_KEYWORD.get(sheet_name)
            if not keyword:
                continue

            print(f"  [{sheet_name}] keyword={keyword}")
            try:
                articles = find_articles_in_monthly_sitemap(keyword, year, month)
                if not articles:
                    print(f"  -> 0 articles found")
                    continue

                for i, article in enumerate(articles, 1):
                    print(f"  ({i}/{len(articles)}) fetching content: {article['Link']}")
                    article["Konten"] = fetch_article_content(article["Link"])
                    time.sleep(CONTENT_FETCH_DELAY)

                df = rename_to_standard_columns(pd.DataFrame(articles))
                if not df.empty:
                    storage.write_news_file({sheet_name: df})
                    print(f"  -> saved {len(df)} rows")
            except Exception as exc:
                print(f"  -> ERROR: {exc}")

            time.sleep(args.delay)

        completed_months.add(month_key)
        progress["completed_kompas_months"] = sorted(completed_months)
        save_progress(progress)
        print(f"[Kompas Monthly] {month_key}: done")


# ── CLI + main ────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill data gap -- requires STORAGE_BACKEND=neon and .env credentials",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--start",  default="2025-10-01",
                        help="Backfill start date YYYY-MM-DD (default: 2025-10-01)")
    parser.add_argument("--end",    default="2026-06-30",
                        help="Backfill end date YYYY-MM-DD (default: 2026-06-30)")
    parser.add_argument("--sources", nargs="+", metavar="SOURCE",
                        help="Sources to run. Omit to run all. "
                             f"Choices: {sorted(ALL_SOURCES)}")
    parser.add_argument("--resume-from", dest="resume_from", default=None,
                        help="Override progress file: resume news loop from AFTER this date")
    parser.add_argument("--delay",  type=float, default=2.5,
                        help="Seconds between requests (default: 2.5)")
    return parser.parse_args()


def main() -> None:
    args     = parse_args()
    progress = load_progress()

    if not progress["started_at"]:
        progress["started_at"] = datetime.now().isoformat()
        save_progress(progress)

    print(f"\n{'='*60}")
    print(f"BACKFILL: {args.start} -> {args.end}")
    print(f"Sources : {args.sources or 'all'}")
    print(f"Delay   : {args.delay}s")
    print(f"Progress: {PROGRESS_FILE}")
    print(f"{'='*60}\n")

    # Tier 1 -- self-healing structured data
    if any(should_run(n, args.sources) for n in TIER1_SOURCES):
        run_tier1(args, progress)

    # Tier 2 -- S&P Global with date range
    if any(should_run(n, args.sources) for n in TIER2_SOURCES):
        run_tier2(args, progress)

    # Tier 3 -- news daily loop
    if should_run("news_lokal", args.sources):
        run_news_lokal(args, progress)

    if should_run("news_intl", args.sources):
        run_news_intl(args, progress)

    # Tier 4 -- Kompas historical monthly sitemaps
    if should_run("kompas_monthly", args.sources):
        run_kompas_monthly(args, progress)

    print(f"\n{'='*60}")
    print("BACKFILL COMPLETE")
    print(f"Progress file: {PROGRESS_FILE}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
