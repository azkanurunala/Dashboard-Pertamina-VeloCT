# Azure OpenAI Migration — Session Notes

> **Auto-loaded** via reference from `CLAUDE.md`. This file captures the migration from Gemini → Azure OpenAI (`gpt-5.4-mini`) executed on **2026-04-30**, plus what's pending and how to verify it. Read this before touching the AI provider, sentiment pipeline, or anything in `shared/ai_providers.py`, `shared/config.py`, `shared/copilot_integration.py`, or scraper Vision OCR paths.

---

## Decision summary

- **Switched** the AI provider from Gemini (`gemini-2.0-flash`) to Azure OpenAI (`gpt-5.4-mini`) hosted on the `peidashboard` Cognitive Services account.
- **Rationale**: user-driven; Azure OpenAI is the customer's preferred tenant.
- The `GeminiProvider` class is **kept** in `shared/ai_providers.py` as a fallback option (still selectable via `AI_TYPE=GEMINI`). Do **not** delete it.
- All defaults across the codebase now point at `AI_TYPE=AZURE_OPENAI`.

## Azure OpenAI deployment details

| Field | Value |
|---|---|
| Endpoint | `https://peidashboard.openai.azure.com/openai/deployments/gpt-5.4-mini/chat/completions?api-version=2024-12-01-preview` |
| Deployment name | `gpt-5.4-mini` |
| Model version | `2026-03-17` |
| API key (Key Vault candidate, currently in App Settings) | `AgVJFUh1eHJj1BTpuSs8CtjuCNjMH3L6TEk3IANtHSCyQrkxE3beJQQJ99CDACYeBjFXJ3w3AAABACOG3vKy` |
| Auth type | API key via `api-key:` header (NOT `Authorization: Bearer`) |
| Token param | `max_completion_tokens` (NOT `max_tokens` — gpt-5.x rejects it) |
| Temperature | **Omit** — gpt-5.x deployments only accept the default value |
| Rate limit | 100 RPM / 100k TPM |

## Environment variables (production + local)

```
AI_TYPE=AZURE_OPENAI
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_MODEL_NAME=gpt-5.4-mini
AZURE_OPENAI_API_ENDPOINT=https://peidashboard.openai.azure.com/openai/deployments/gpt-5.4-mini/chat/completions?api-version=2024-12-01-preview
```

Pushed to: `local.settings.json`, `azure_settings.json`, `.env`, `.env.test`, `.env.template`, **and** the live Function App's App Settings.

## Code changes (committed under branch `dev-migration`)

| File | Change |
|---|---|
| `shared/ai_providers.py` | Added `AzureOpenAIProvider` class. Added `AZURE_OPENAI` to `SUPPORTED_TYPES`. Factory dispatches to it when `AI_TYPE=AZURE_OPENAI`. Default for `os.getenv("AI_TYPE", ...)` flipped to `"AZURE_OPENAI"`. |
| `shared/config.py` | `provider_defaults` map gained `AZURE_OPENAI` entry. Default `AI_TYPE` flipped. Added `python-dotenv` autoload of `.env` (override=False so Azure App Settings still win in production). |
| `shared/copilot_integration.py` | Default `AI_TYPE` flipped. `model_version` field now formatted `azure_openai-gpt-5.4-mini`. |
| `scrapers/migas_esdm_scraper.py` | Vision OCR fallback gained `AZURE_OPENAI` branch via new `_call_azure_openai_vision()`. Without this branch the OCR would have crashed under the new provider. |
| `backfill_via_google.py`, `backfill_sentiment.py` | Hardcoded `os.environ['AI_TYPE'] = 'OPENAI'` → `'AZURE_OPENAI'`. |
| `azure_settings.json` | Added `AZURE_OPENAI_*` entries; `AI_TYPE` flipped. |
| `.env`, `.env.test`, `.env.template` | Same. |
| `scripts/sync-env-to-azure.ps1` | Refactored to send settings via temp JSON file (`--settings @file.json`) instead of `KEY=VALUE` args. **Reason: passwords containing `&` (e.g. `SP_PASSWORD=Pertamina.Setup1S&P`) broke the previous form because CMD's batch wrapper around `az.cmd` re-parses `&` as a command separator before `az` ever sees it.** |
| `scripts/verify-azure-openai-migration.cmd` | New verification script (queries App Insights + SQL). |

## Production state as of 2026-05-01

- Function App: `pei-dashboard` in resource group `PeiDashboard`, subscription `5e4ecee4-ce42-47f4-b953-7f29ad625c53`.
- Default domain: `pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net`
- Code deployed via `func azure functionapp publish pei-dashboard --build remote` — succeeded.
- App Settings pushed via `az functionapp config appsettings set` — succeeded.
- Health check (`/api/health`) — 19/19 imports pass, 0 failures.
- **Local end-to-end** — `CopilotIntegration.analyze_sentiment()` returns `model_version=azure_openai-gpt-5.4-mini`. Confirmed working.
- **Production end-to-end** — NOT yet observed. Reason: most scrapers stopped saving data after 2026-02-12 (pre-existing issue documented in `CLAUDE.md`), so no upstream articles → no sentiment runs → no proof in `sentiment_analyses` table.
- HTTP-trigger scraper functions only **scrape** — they do **not** run sentiment. Sentiment only fires through the orchestrator (timer-driven path in `orchestration/scheduler_function.py` → `daily_morning_routine` etc.).
- The S&P News scraper, when invoked manually with a wider date range, did save 42 articles successfully on 2026-05-01 — proving scrape-and-save still works for that source.

## How to prove the migration is live in production

1. Manually fire the orchestrator timer via the Functions admin API:
   ```cmd
   az functionapp keys list --name pei-dashboard --resource-group PeiDashboard --query "masterKey" -o tsv
   ```
   Then with `<MASTER>`:
   ```cmd
   curl -X POST "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/admin/functions/daily_morning_timer" -H "x-functions-key: <MASTER>" -H "Content-Type: application/json" -d "{\"input\":\"manual\"}"
   ```
2. Wait ~5 min for the orchestrator to finish.
3. Run `scripts\verify-azure-openai-migration.cmd`. Expect:
   - Section [3] (`model_version LIKE 'azure_openai-%'`): rows > 0
   - Section [4] (`model_version LIKE 'gemini-%'`): no rows
   - Section [5] last 10 rows: top entries should be `azure_openai-gpt-5.4-mini` with today's timestamp.
   - Section [1] / [2] App Insights queries: positive markers > 0, Gemini markers = 0.

## Incidents during migration

**2026-05-02 — `sync-env-to-azure.ps1` clobbered production App Insights.** Running the bulk env-sync script pushed the test/mock values `APPINSIGHTS_INSTRUMENTATIONKEY=test-instrumentation-key` and `APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=test-key;...test.in.applicationinsights.azure.com/` from `.env` straight into the live Function App, breaking telemetry — the orchestrator and scrapers ran fine but their logs were shipped to a fake endpoint, so App Insights queries returned empty for ~hours until the bug was spotted. Fixed by manually re-pushing the real `pei-dashboard2026012369` instrumentation key + connection string, then adding `APPINSIGHTS_INSTRUMENTATIONKEY` and `APPLICATIONINSIGHTS_CONNECTION_STRING` to the `$Skip` list in `scripts/sync-env-to-azure.ps1` so future runs leave them alone. **Lesson: never let a generic `.env`-to-AppSettings sync script touch telemetry / connection-string settings — those must be sourced from `azure_settings.json` or the portal only.**

## Known infrastructure gotchas

- **Two App Insights components** in `PeiDashboard` RG: `pei-dashboard2026012369` (active, AppId `9db8826b-a342-44c5-973d-a045bac44ee2`) and `pei-dashboard` (stale). Always query the first.
- **SQL firewall** blocks new IPs by default. Add via `az sql server firewall-rule create --resource-group PeiDashboard --server pei-dashboard --name "<rule-name>" --start-ip-address <IP> --end-ip-address <IP>`.
- **`az.cmd` on Windows** — invoking from CMD with values containing `&`, `^`, `>`, `|`, `(`, `)` will fail unless the value is inside `"..."` AND any wrapping shell doesn't pre-parse it. Prefer JSON-file form (`--settings @file.json`) for bulk pushes.
- **Inside CMD `-Q "..."` strings, do NOT escape `>` as `^>`.** The `^` survives into the SQL query as literal `^>` which is a syntax error. The double quotes already protect `>` from CMD redirection.
- **HTTP scraper functions accept `start_date` and `end_date` as `YYYY-MM-DD`**, not ISO8601 with time. Wider window (e.g. 6 days) is more likely to find articles than today-only.
- **Stray file `$null`** got deployed into `/home/site/wwwroot` after a misformatted PowerShell `> $null` redirect. 0 bytes, harmless, but ugly. Sweep on next deploy.

## Pending follow-ups

- **Move `AZURE_OPENAI_API_KEY` into Key Vault** and reference it from App Settings via `@Microsoft.KeyVault(SecretUri=...)`, matching how `DatabaseConnectionString` and `StorageConnectionString` are configured. Right now the key is in plaintext in `azure_settings.json` and App Settings.
- **Investigate why most scrapers haven't saved data since 2026-02-12.** Separate from this migration. `CLAUDE.md` lists known-broken scrapers (`bank_indonesia_scraper.py`, `bps_scraper.py`) that depend on a missing `shared/selenium_helper.py`.
- **Confirm production sentiment row** with `model_version=azure_openai-gpt-5.4-mini` after firing the manual timer trigger above. Once that row exists, the migration is fully proven.
- **Delete stale `$null` file** in `/home/site/wwwroot` on next deploy.

## What NOT to do

- Don't add `temperature` to Azure OpenAI requests — gpt-5.x deployments reject anything other than the default.
- Don't use `max_tokens` — must be `max_completion_tokens`.
- Don't use `Authorization: Bearer <key>` — Azure OpenAI uses `api-key: <key>`.
- Don't delete `GeminiProvider`, `_call_gemini_vision()`, or `GEMINI_API_KEY` from settings — they're intentional fallbacks.
- Don't run `func azure functionapp publish` from a venv where Python ≠ 3.11 without verifying remote build picked up the right interpreter — the deploy log will warn.
- Don't pass `KEY=VALUE` args containing `&` to `az.cmd` from CMD/PowerShell — use a JSON file.
