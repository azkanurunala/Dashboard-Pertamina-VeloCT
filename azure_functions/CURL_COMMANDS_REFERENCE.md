# Quick curl Commands Reference

**EDIT DULU**: Ganti `YOUR-APP-NAME` dengan nama Function App Anda!

```bash
# Set your Function App name
export APP_NAME="YOUR-APP-NAME"
export BASE_URL="https://${APP_NAME}.azurewebsites.net/api"
```

Atau untuk Windows CMD:
```cmd
set APP_NAME=YOUR-APP-NAME
set BASE_URL=https://%APP_NAME%.azurewebsites.net/api
```

---

## International News Scrapers

### CNBC
```bash
curl -X GET "${BASE_URL}/cnbc_scraper_function?keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&save_to_db=false"
```

### OilPrice
```bash
curl -X GET "${BASE_URL}/oilprice_scraper_function?keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&max_articles=10"
```

### Reuters
```bash
curl -X GET "${BASE_URL}/reuters_scraper_function?keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&save_to_db=false"
```

### CNN
```bash
curl -X GET "${BASE_URL}/cnn_scraper_function?keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&max_articles=10"
```

### The Guardian
```bash
curl -X GET "${BASE_URL}/theguardian_scraper_function?keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&max_articles=10"
```

---

## Indonesian News Scrapers

### Kompas
```bash
curl -X GET "${BASE_URL}/kompas_scraper_function?keywords=energi,minyak&start_date=2025-01-21&end_date=2026-01-28&max_articles=10"
```

### Tempo
```bash
curl -X GET "${BASE_URL}/tempo_scraper_function?keywords=energi,minyak&start_date=2025-01-21&end_date=2026-01-28&max_articles=10"
```

### Kontan
```bash
curl -X GET "${BASE_URL}/kontan_scraper_function?keywords=energi,minyak&start_date=2025-01-21&end_date=2026-01-28&max_articles=10"
```

### CNBC Indonesia
```bash
curl -X GET "${BASE_URL}/cnbc_indonesia_scraper_function?keywords=energi,minyak&start_date=2025-01-21&end_date=2026-01-28&max_articles=10"
```

### Bisnis Indonesia
```bash
curl -X GET "${BASE_URL}/bisnis_indonesia_scraper_function?keywords=energi,minyak&start_date=2025-01-21&end_date=2026-01-28&max_articles=10"
```

---

## Data Scrapers

### BPS
```bash
curl -X GET "${BASE_URL}/bps_scraper_function?indicators=inflation,gdp&start_date=2025-01-21&end_date=2026-01-28"
```

---

## With Function Key (if required)

```bash
# Add function key to URL
curl -X GET "${BASE_URL}/cnbc_scraper_function?code=YOUR_FUNCTION_KEY&keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28"

# Or use header
curl -H "x-functions-key: YOUR_FUNCTION_KEY" -X GET "${BASE_URL}/cnbc_scraper_function?keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28"
```

---

## Pretty Print JSON Response

```bash
curl -X GET "${BASE_URL}/cnbc_scraper_function?keywords=energy&start_date=2025-01-21&end_date=2026-01-28" | python -m json.tool
```

---

## Save Response to File

```bash
curl -X GET "${BASE_URL}/cnbc_scraper_function?keywords=energy&start_date=2025-01-21&end_date=2026-01-28" -o response.json
```

---

## Show Response Time

```bash
curl -w "\nTime: %{time_total}s\n" -X GET "${BASE_URL}/cnbc_scraper_function?keywords=energy&start_date=2025-01-21&end_date=2026-01-28"
```

---

**Copy-paste commands di atas untuk quick testing!**
