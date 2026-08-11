"""backfill_news_alltopics.py -- Backfill news scraping for ALL topics, month by month.

Runs the lokal + internasional news scrapers for every topic (including the
ones commented out in the orchestrators) over historical month windows,
newest month first: 1 month back, then 2 months back, ... up to --months-back.

The production orchestrator files are NOT modified: the full keyword/sheet
maps are reconstructed here and monkeypatched onto the imported modules.

Usage:
    python scripts/backfill_news_alltopics.py                    # 8 months back
    python scripts/backfill_news_alltopics.py --months-back 3
    python scripts/backfill_news_alltopics.py --only lokal       # or: intl
    python scripts/backfill_news_alltopics.py --delay 2.0

Progress saved to scripts/backfill_alltopics_progress.json after each
(loop, date) unit; interrupt and re-run to resume.

Note: most sources only expose recent articles (live sitemaps/RSS), so old
months will mostly yield Kompas/archive hits. Combine with:
    python scripts/backfill.py --sources kompas_monthly --start ... --end ...
"""

import argparse
import json
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

PROGRESS_FILE = SCRIPT_DIR / "backfill_alltopics_progress.json"  # dioverride per rentang bulan di main()


# ── Full topic maps (reconstructed from the commented-out orchestrator config) ──

def build_lokal_maps(m):
    """m = orchestrators.main_news_scraping_lokal module."""
    sumber = {
        "indeks risiko geopolitik ": [m.main_bloomberg_technoz],
        "indeks volatilitas ": [m.main_bloomberg_technoz],
        "kurs ": [m.scrape_kontan, m.main_bisnis_indonesia, m.main_kompas, m.scrape_tempo, m.main_cnbc],
        "ihsg ": [m.scrape_kontan, m.main_bisnis_indonesia, m.main_kompas, m.scrape_tempo, m.main_cnbc],
        "inflasi ": [m.scrape_kontan, m.main_bisnis_indonesia, m.main_kompas, m.scrape_tempo, m.main_cnbc, m.main_bps],
        "bi rate ": [m.scrape_kontan, m.main_bisnis_indonesia, m.main_kompas, m.scrape_tempo, m.main_cnbc, m.main_bank_indonesia],
        "indonia ": [m.scrape_kontan, m.main_bisnis_indonesia, m.main_kompas, m.scrape_tempo, m.main_cnbc, m.main_bank_indonesia],
        "indeks sales retail ": [m.scrape_kontan, m.main_bisnis_indonesia, m.main_kompas, m.scrape_tempo, m.main_cnbc, m.main_bank_indonesia],
        "indeks kepercayaan konsumen ": [m.scrape_kontan, m.main_bisnis_indonesia, m.main_kompas, m.scrape_tempo, m.main_cnbc, m.main_bank_indonesia],
        "indeks kinerja manufaktur ": [m.scrape_kontan, m.main_bisnis_indonesia, m.main_kompas, m.scrape_tempo, m.main_cnbc],
        "indeks kinerja jasa ": [m.scrape_kontan, m.main_bisnis_indonesia, m.main_kompas, m.scrape_tempo, m.main_cnbc],
        "neraca perdagangan ": [m.scrape_kontan, m.main_bisnis_indonesia, m.main_kompas, m.scrape_tempo, m.main_cnbc, m.main_bps],
        "pertumbuhan domestik bruto ": [m.scrape_kontan, m.main_bisnis_indonesia, m.main_kompas, m.scrape_tempo, m.main_cnbc, m.main_bps],
        "harga minyak ": [m.scrape_kontan_bbm, m.main_bisnis_indonesia, m.main_bloomberg_technoz],
        "volume minyak ": [m.scrape_kontan_bbm, m.main_bisnis_indonesia, m.main_bloomberg_technoz],
        "harga produk kilang pertamina ": [m.scrape_kontan_biodiesel, m.main_bisnis_indonesia, m.main_bloomberg_technoz],
        "volume produk kilang pertamina ": [m.scrape_kontan_biodiesel, m.main_bisnis_indonesia, m.main_bloomberg_technoz],
        "RON 92 ": [m.scrape_kontan_biodiesel, m.main_bisnis_indonesia, m.main_bloomberg_technoz],
        "Petrochemical ": [m.scrape_kontan_biodiesel, m.main_bisnis_indonesia, m.main_bloomberg_technoz],
        "biodiesel ": [m.scrape_kontan_biodiesel, m.main_bisnis_indonesia, m.main_bloomberg_technoz],
        "SAF ": [m.scrape_kontan_biodiesel, m.main_bisnis_indonesia, m.main_bloomberg_technoz],
        "bioetanol ": [m.scrape_kontan_biodiesel, m.main_bisnis_indonesia, m.main_bloomberg_technoz],
        "RUPTL ": [m.scrape_kontan_biodiesel, m.main_bisnis_indonesia, m.main_bloomberg_technoz],
        "LCOE ": [m.scrape_kontan_biodiesel, m.main_bisnis_indonesia, m.main_bloomberg_technoz],
        "WTE ": [m.scrape_kontan_biodiesel, m.main_bisnis_indonesia, m.main_bloomberg_technoz],
        "Pembangkit listrik nuklir ": [m.scrape_kontan_biodiesel, m.main_bisnis_indonesia, m.main_bloomberg_technoz],
    }
    sheet_to_keyword = {
        "(News)Indeks Risiko Geopolitik": "indeks risiko geopolitik ",
        "(News)Indeks Volatilitas": "indeks volatilitas ",
        "(News)Kurs": "kurs ",
        "(News)IHSG": "ihsg ",
        "(News)Inflasi": "inflasi ",
        "(News)BI Rate": "bi rate ",
        "(News)Indonia": "indonia ",
        "(News)Indeks Penjualan Ritel": "indeks sales retail ",
        "(News)Indeks Kepercayaan Knsmn": "indeks kepercayaan konsumen ",
        "(News)Indeks Kinerja Manufaktur": "indeks kinerja manufaktur ",
        "(News)Indeks Kinerja Jasa": "indeks kinerja jasa ",
        "(News)Neraca Perdagangan": "neraca perdagangan ",
        "(News)PDB": "pertumbuhan domestik bruto ",
        "(News)Harga Minyak": "harga minyak ",
        "(News)Volume Minyak": "volume minyak ",
        "(News)Harga Produk Kilang": "harga produk kilang pertamina ",
        "(News)Volume Produk Kilang": "volume produk kilang pertamina ",
        "(News)Crackspread BBM": "RON 92 ",
        "(News)Crackspread Non-BBM": "Petrochemical ",
        "(News)Biodiesel": "biodiesel ",
        "(News)SAF": "SAF ",
        "(News)Bioetanol": "bioetanol ",
        "(News)RUPTL": "RUPTL ",
        "(News)EBT": "LCOE ",
        "(News)WTE": "WTE ",
        "(News)Nuklir": "Pembangkit listrik nuklir ",
    }
    return sumber, sheet_to_keyword


def build_intl_maps(m):
    """m = orchestrators.main_news_scraping_internasional module."""
    sumber = {
        "geopolitical risk ": [m.main_google_news_cnn, m.main_google_news_cnbc, m.main_scmp, m.scrape_theguardian],
        "volatility index ": [m.main_google_news_cnn, m.main_google_news_cnbc, m.main_scmp, m.scrape_theguardian],
        "dxy ": [m.main_google_news_cnn, m.main_google_news_cnbc],
        "purchasing manufaktur index ": [m.scrape_news_sap],
        "purchasing services index ": [m.scrape_news_sap],
        "oil price ": [m.scrape_oilprice],
        "oil volume ": [m.scrape_oilprice],
        "pertamina oil price ": [m.scrape_oilprice],
        "pertamina oil volume ": [m.scrape_oilprice],
        "RON 92 ": [m.scrape_news_sap, m.main_google_news_cnbc, m.main_google_news_cnn,
                    m.scrape_energiesmedia, m.scrape_bioenergytimes, m.scrape_theguardian],
        "Petrochemical ": [m.scrape_news_sap, m.main_google_news_cnbc, m.main_google_news_cnn,
                           m.scrape_energiesmedia, m.scrape_bioenergytimes],
        "SAF ": [m.scrape_news_sap, m.main_google_news_cnbc, m.main_google_news_cnn],
    }
    sheet_to_keyword = {
        "(News)Indeks Risiko Geopolitik": "geopolitical risk ",
        "(News)Indeks Volatilitas": "volatility index ",
        "(News)Kurs": "dxy ",
        "(News)Indeks Kinerja Manufaktur": "purchasing manufaktur index ",
        "(News)Indeks Kinerja Jasa": "purchasing services index ",
        "(News)Harga Minyak": "oil price ",
        "(News)Volume Minyak": "oil volume ",
        "(News)Harga Produk Kilang": "pertamina oil price ",
        "(News)Volume Produk Kilang": "pertamina oil volume ",
        "(News)Crackspread BBM": "RON 92 ",
        "(News)Crackspread Non-BBM": "Petrochemical ",
        "(News)SAF": "SAF ",
    }
    return sumber, sheet_to_keyword


# ── Progress ──────────────────────────────────────────────────────────────────

_progress_file = PROGRESS_FILE


def load_progress() -> dict:
    if _progress_file.exists():
        return json.loads(_progress_file.read_text())
    return {"started_at": datetime.now().isoformat(), "done": {}}


def save_progress(progress: dict) -> None:
    tmp = _progress_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(progress, indent=2))
    tmp.replace(_progress_file)


# ── Core loop ─────────────────────────────────────────────────────────────────

def month_windows(months_back: int) -> list[tuple[str, date, date]]:
    """Windows newest-first: 1 back = (today-30 .. today-1), etc. 30-day blocks."""
    today = date.today()
    windows = []
    for n in range(1, months_back + 1):
        end = today - timedelta(days=30 * (n - 1) + 1)
        start = today - timedelta(days=30 * n)
        windows.append((f"bulan-{n}", start, end))
    return windows


def run_window(label: str, mod, sheet_to_keyword, win_name, start, end, args, progress):
    from helpers.storage_backend import storage

    done: dict = progress["done"]
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    print(f"\n{'=' * 60}\n[{label}] window {win_name}: {start} -> {end} ({len(dates)} hari)\n{'=' * 60}")

    for tanggal in dates:
        key = f"{label}:{tanggal.isoformat()}"
        if done.get(key):
            continue

        print(f"\n[{label}] {win_name} {tanggal}")
        for sheet_name, keyword in sheet_to_keyword.items():
            try:
                hasil = mod.scrape_keyword(keyword, tanggal.isoformat())
                if hasil is not None and not getattr(hasil, "empty", True):
                    storage.write_news_file({sheet_name: hasil})
                    print(f"  [{sheet_name}] +{len(hasil)} artikel")
            except Exception as exc:
                print(f"  [{sheet_name}] ERROR: {exc}")
            time.sleep(args.delay)

        done[key] = True
        save_progress(progress)


def run_kompas_all_topics(args) -> None:
    """Kompas historical monthly sitemaps for ALL lokal topics (archives reach
    old months, unlike live sitemaps). Reuses backfill.py's run_kompas_monthly
    with the full sheet map patched in."""
    import importlib.util

    import orchestrators.main_news_scraping_lokal as L
    sumber, s2k = build_lokal_maps(L)
    L.SUMBER_DICT = sumber
    L.SHEET_TO_KEYWORD = s2k
    L.ACTIVE_SHEETS = list(s2k.keys())

    spec = importlib.util.spec_from_file_location("backfill_base", SCRIPT_DIR / "backfill.py")
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)

    today = date.today()
    ns = argparse.Namespace(
        start=(today - timedelta(days=30 * args.months_back)).isoformat(),
        end=(today - timedelta(days=1)).isoformat(),
        delay=args.delay,
    )
    progress = base.load_progress()
    base.run_kompas_monthly(ns, progress)


def main() -> None:
    try:
        _main_impl()
    finally:
        # scrape_keyword (lokal orchestrator) reuses one Selenium driver per
        # source across the whole run instead of relaunching per keyword --
        # close here so no Chrome process lingers after the script exits.
        # close_driver() is a no-op if that source was never used.
        from news.bank_indonesia import close_driver as close_bank_indonesia_driver
        from news.cnbc_id import close_driver as close_cnbc_driver
        close_cnbc_driver()
        close_bank_indonesia_driver()


def _main_impl() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--months-back", type=int, default=8)
    ap.add_argument("--from-month", type=int, default=1, help="window bulan awal (1 = bulan terakhir)")
    ap.add_argument("--to-month", type=int, default=None, help="window bulan akhir (default: months-back)")
    ap.add_argument("--only", choices=["lokal", "intl"], default=None)
    ap.add_argument("--kompas", action="store_true",
                    help="mode arsip: sitemap bulanan Kompas untuk semua topik lokal")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between scraper calls")
    args = ap.parse_args()

    if args.kompas:
        run_kompas_all_topics(args)
        return

    to_month = args.to_month or args.months_back
    global _progress_file
    _progress_file = SCRIPT_DIR / f"backfill_alltopics_progress_m{args.from_month}-{to_month}.json"

    progress = load_progress()
    windows = [w for w in month_windows(args.months_back)
               if args.from_month <= int(w[0].split("-")[1]) <= to_month]
    print(f"Backfill semua topik, window bulan {args.from_month}..{to_month} (terbaru dulu):")
    for w, s, e in windows:
        print(f"  {w}: {s} -> {e}")

    jobs = []
    if args.only in (None, "lokal"):
        import orchestrators.main_news_scraping_lokal as L
        sumber, s2k = build_lokal_maps(L)
        L.SUMBER_DICT = sumber
        L.SHEET_TO_KEYWORD = s2k
        L.ACTIVE_SHEETS = list(s2k.keys())
        jobs.append(("lokal", L, s2k))
    if args.only in (None, "intl"):
        import orchestrators.main_news_scraping_internasional as I
        sumber, s2k = build_intl_maps(I)
        I.SUMBER_DICT = sumber
        I.SHEET_TO_KEYWORD = s2k
        I.ACTIVE_SHEETS = list(s2k.keys())
        jobs.append(("intl", I, s2k))

    # Urutan sesuai permintaan: selesaikan bulan-1 (lokal+intl) dulu, lalu bulan-2, dst.
    for win_name, start, end in windows:
        for label, mod, s2k in jobs:
            run_window(label, mod, s2k, win_name, start, end, args, progress)

    print("\nSELESAI.")


if __name__ == "__main__":
    main()
