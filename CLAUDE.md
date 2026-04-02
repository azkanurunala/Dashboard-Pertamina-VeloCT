# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **Azure Functions-based automated news scraping and data aggregation system** for Pertamina's energy sector dashboard. It scrapes news from 18+ sources and structured data (oil prices, biofuels, nuclear) from government/market APIs, classifies articles by energy topic via keyword matching, runs AI sentiment analysis via Gemini, and stores everything in Azure SQL Server for Power BI consumption.

All active code lives in `azure_functions/`. The `src/` directory is legacy.

## Commands

All commands run from `azure_functions/` unless noted.

```bash
# Activate virtual environment
source .venv/Scripts/activate         # bash on Windows
.venv\Scripts\Activate.ps1            # PowerShell

# Run tests
pytest tests/                          # All tests
pytest tests/ -m unit                  # Unit tests only
pytest tests/ -m integration           # Integration tests only
pytest tests/test_models.py -v         # Single file

# Local Azure Functions runtime
func start                             # Requires Azure Functions Core Tools

# Database checks (connect via local.settings.json)
python check_category.py               # Check category counts in DB
python check_recent_data.py            # Check recent article counts per table
python verify_schema_alignment.py      # Verify DB schema matches migration SQL

# Data backfill / seeding
python backfill_bi.py                  # Backfill Bank Indonesia news (last 30 days)
python seed_data.py --dry-run          # Validate CSV seeding without inserting
python seed_data.py --batch-size 50    # Import CSV data

# Deployment
./scripts/deploy-functions.ps1         # Deploy to Azure
```

## Architecture

### Flow

```
Timer triggers (daily/weekly/monthly)
    → SchedulerFunction (orchestration/scheduler_function.py)
        → OrchestratorFunction (orchestration/orchestrator_function.py)
            → SCRAPER_REGISTRY[source]()   ← one scraper per source
            → _classify_article_categories()  ← keyword → category mapping
            → DatabaseHandler.save_articles()
            → CopilotIntegration (AI sentiment)
                → ai_providers.py (Gemini/Claude/OpenAI)
```

### Key Files

| File | Role |
|------|------|
| `orchestration/orchestrator_function.py` | Central orchestrator; holds `SCRAPER_REGISTRY`, `DATA_SOURCES`, `CATEGORY_KEYWORDS`, and `_classify_article_categories()` |
| `orchestration/scheduler_function.py` | Timer-triggered routines: `daily_morning_routine()`, `daily_afternoon_routine()`, weekly, monthly |
| `shared/models.py` | Core dataclasses: `NewsArticle`, `SentimentAnalysis`, `ExecutionResult`, enums |
| `shared/database_handler.py` | All DB operations (pyodbc/pymssql, connection pool, retry, dedup by URL+category) |
| `shared/interfaces.py` | Abstract base contracts for all major components |
| `shared/config.py` | `EnvironmentConfigurationManager`; reads env vars, falls back to Azure Key Vault |
| `shared/ai_providers.py` | Pluggable AI backends (Gemini, Claude, OpenAI) for sentiment analysis |
| `scrapers/base_scraper.py` | `BaseNewsScraper` with rate limiting, retry, aiohttp, optional Selenium fallback |
| `UNIFIED_MIGRATION.sql` | **Source of truth for the full DB schema** (30 tables) |

### Scrapers

Two scraper types exist, distinguished in `DATA_SOURCES` set:

- **News scrapers** → return `List[NewsArticle]` → classified into categories → saved to `news_articles` table
- **Data scrapers** → return `List[dict]` → saved to type-specific tables (e.g., `data_biodiesel_hip`, `data_oil_prices`)

Scrapers that need Selenium import from `shared/selenium_helper.py` (currently **missing** — `bank_indonesia_scraper.py` and others will fail silently if this file doesn't exist; `SELENIUM_AVAILABLE` will be `False`).

### Category Classification

`_classify_article_categories(title, content)` in `orchestrator_function.py` does **substring matching** (not word boundary) of `CATEGORY_KEYWORDS` dict against `title + content`. Returns the matched category names, or falls back to `['Harga Minyak']`. Power BI queries filter by these exact category strings (e.g., `category = 'indeks kepercayaan knsmn'`).

**Important**: The keywords use BI terminology like `'indeks keyakinan konsumen'` (not `'kepercayaan'`). Short abbreviations like `'ikk'`, `'ike'`, `'iek'` must **not** be added as keywords — they cause false positives (e.g., `'ikk'` matches `'naikkan'`).

### Database

- Connection string: `SQL_SERVER_CONNECTION_STRING` env var (or `DatabaseConnectionString` in Azure App Settings)
- Source name matching in `news_sources` is **exact, case-sensitive**. The scraper's `SOURCE_NAME` constant must match the `name` column in `news_sources` exactly (e.g., `"Bank Indonesia"` vs `"BANK_INDONESIA"` are different rows).
- Deduplication is based on `(url, category)` pairs.

### Scheduling

Timer schedules are set via environment variables in CRON format:
- `MORNING_TIMER_SCHEDULE` — international sources (CNBC, Reuters, Bloomberg, etc.)
- `AFTERNOON_TIMER_SCHEDULE` — Indonesian/local sources (Bank Indonesia, ESDM, BPS, etc.)

## Known Issues

- `shared/selenium_helper.py` does not exist → `bank_indonesia_scraper.py`, `bps_scraper.py`, and other Selenium-dependent scrapers silently fail in Azure (0 articles saved).
- `news_sources.base_url` for `BANK_INDONESIA` is incorrectly set to `https://www.bank_indonesia.com` (should be `https://www.bi.go.id`).
- Most scrapers stopped saving data after 2026-02-12; only `S&P Global News`, `EnergiesMedia`, `SCMP` are active as of 2026-03-13.
