# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **🔥 Required reading before any AI-provider / sentiment / scraper-OCR work:** [AZURE_OPENAI_MIGRATION.md](AZURE_OPENAI_MIGRATION.md). The system was migrated from Gemini to Azure OpenAI (`gpt-5.4-mini`) on 2026-04-30; that file captures decisions, env vars, gotchas, pending follow-ups, and how to verify the migration is live.

@AZURE_OPENAI_MIGRATION.md

## Project Overview

This is an **Azure Functions-based automated news scraping and data aggregation system** for Pertamina's energy sector dashboard. It scrapes news from 18+ sources and structured data (oil prices, biofuels, nuclear) from government/market APIs, classifies articles by energy topic via keyword matching, runs AI sentiment analysis via **Azure OpenAI (gpt-5.4-mini)** (was Gemini before 2026-04-30), and stores everything in Azure SQL Server for Power BI consumption.

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
scripts\sync-env-to-azure.cmd          # Sync .env -> Azure App Settings (CMD)
scripts\sync-env-to-azure.cmd -DryRun  # Preview which keys would be pushed
.\scripts\sync-env-to-azure.ps1        # Same, from PowerShell
func azure functionapp publish pei-dashboard --build remote   # Deploy code
./scripts/deploy-functions.ps1         # Deploy script wrapper (legacy)
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
| `shared/config.py` | `EnvironmentConfigurationManager`; auto-loads `.env` on import (via `python-dotenv`, `override=False` so Azure App Settings win in cloud), reads env vars, falls back to Azure Key Vault |
| `scripts/sync-env-to-azure.ps1` / `.cmd` | Reads `.env` and pushes every key to Azure Function App App Settings via `az functionapp config appsettings set` |
| `shared/ai_providers.py` | Pluggable AI backends (Gemini, Claude, OpenAI) for sentiment analysis |
| `scrapers/base_scraper.py` | `BaseNewsScraper` with rate limiting, retry, aiohttp, optional Selenium fallback |
| `UNIFIED_MIGRATION.sql` | **Source of truth for the full DB schema** (30 tables) |

### Scrapers

Two scraper types exist, distinguished in `DATA_SOURCES` set:

- **News scrapers** → return `List[NewsArticle]` → classified into categories → saved to `news_articles` table
- **Data scrapers** → return `List[dict]` → saved to type-specific tables (e.g., `data_biodiesel_hip`, `data_oil_prices`)

Scrapers that need Selenium import from `shared/selenium_helper.py` (this file **exists** as of 2026-04-30; `SELENIUM_AVAILABLE` is `True` when the chromedriver is reachable).

### Category Classification

`_classify_article_categories(title, content)` in `orchestrator_function.py` does **substring matching** (not word boundary) of `CATEGORY_KEYWORDS` dict against `title + content`. Returns the matched category names, or falls back to `['Harga Minyak']`. Power BI queries filter by these exact category strings (e.g., `category = 'indeks kepercayaan knsmn'`).

**Important**: The keywords use BI terminology like `'indeks keyakinan konsumen'` (not `'kepercayaan'`). Short abbreviations like `'ikk'`, `'ike'`, `'iek'` must **not** be added as keywords — they cause false positives (e.g., `'ikk'` matches `'naikkan'`).

### Configuration & Secrets

`.env` (in `azure_functions/.env`) is the **single source of truth** for all secrets and configuration. The flow is:

- **Local runs** (`func start`, pytest, ad-hoc scripts): `shared/config.py` calls `load_dotenv()` on import, which populates `os.environ` from `.env`.
- **Azure cloud**: Function App **App Settings** are already in `os.environ` before `shared/config.py` runs. `load_dotenv(override=False)` will not override them, so production values always win.
- **`.env` is gitignored** — never commit it. Use `scripts\sync-env-to-azure.cmd` to push it to Azure App Settings instead of duplicating values into `azure_settings.json` by hand.
- `local.settings.json` is the legacy per-key store used by Azure Functions Core Tools when running `func start`. Keep it in sync with `.env` (or remove it once the team confirms `.env` covers everything).

Required keys (all in `.env`):
- DB: `SQL_SERVER_CONNECTION_STRING` (or `DatabaseConnectionString` for Key Vault refs in Azure)
- AI: `AI_TYPE`, `AZURE_OPENAI_API_KEY` + endpoint, `GEMINI_API_KEY`
- Scrapers: `SP_USERNAME`, `SP_PASSWORD` (S&P Global), `BPS_API_KEY`, `EIA_API_KEY`, `THEGUARDIAN_API_KEY`
- Schedules: `MORNING_TIMER_SCHEDULE`, `AFTERNOON_TIMER_SCHEDULE`, `WEEKLY_TIMER_SCHEDULE`, `MONTHLY_TIMER_SCHEDULE` (NCRONTAB)

### Database

- Connection string: `SQL_SERVER_CONNECTION_STRING` env var (or `DatabaseConnectionString` in Azure App Settings)
- Source name matching in `news_sources` is **exact, case-sensitive**. The scraper's `SOURCE_NAME` constant must match the `name` column in `news_sources` exactly (e.g., `"Bank Indonesia"` vs `"BANK_INDONESIA"` are different rows).
- Deduplication is based on `(url, category)` pairs.

### Scheduling

Timer schedules are set via environment variables in CRON format:
- `MORNING_TIMER_SCHEDULE` — international sources (CNBC, Reuters, Bloomberg, etc.)
- `AFTERNOON_TIMER_SCHEDULE` — Indonesian/local sources (Bank Indonesia, ESDM, BPS, etc.)

## Deploy Procedure

From `azure_functions/` in cmd or PowerShell (after `az login`):

```
scripts\sync-env-to-azure.cmd -DryRun     # preview
scripts\sync-env-to-azure.cmd             # push .env -> Azure App Settings
func azure functionapp publish pei-dashboard --build remote
```

Verify after deploy:
```
curl https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/health_check_function
```

The Function App is `pei-dashboard` in resource group `PeiDashboard` (Canada Central).

## Known Issues

- `news_sources.base_url` for `BANK_INDONESIA` is incorrectly set to `https://www.bank_indonesia.com` (should be `https://www.bi.go.id`).
- The Guardian, IAEA PRIS, and migas.esdm.go.id may fail from some local networks due to TLS/firewall — they work fine from inside Azure.
- S&P Global login (used by `sandp_news` and `sandp_data`) requires valid `SP_USERNAME`/`SP_PASSWORD`; if S&P changes its login flow the scraper needs updating.

## Recent fixes (2026-04-30)

- Implemented missing `_extract_article_content_json_ld` method in `scrapers/oilprice_scraper.py` (was referenced but undefined).
- Added missing `SentimentLabel` import in `orchestration/orchestrator_function.py`.
- Replaced hardcoded API keys in `theguardian_scraper.py` and `migas_eia_scraper.py` with `os.getenv(...)` — they now require `THEGUARDIAN_API_KEY` and `EIA_API_KEY` env vars.
- Added `load_dotenv()` in `shared/config.py` so `.env` is automatically loaded for local runs.
