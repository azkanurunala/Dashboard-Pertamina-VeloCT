# Quick Test Commands - Cheat Sheet

## 🚀 Cara Tercepat

```cmd
cd azure_functions
test_scrapers.bat
```

## 📋 Test Individual Scrapers

### International News
```cmd
# CNBC
python -c "from scrapers.cnbc_scraper import CNBCNewsScraper; print('✓ CNBC OK')"

# OilPrice
python -c "from scrapers.oilprice_scraper import scrape_oilprice_news; print('✓ OilPrice OK')"

# Reuters
python -c "from scrapers.reuters_scraper import ReutersNewsScraper; print('✓ Reuters OK')"

# CNN
python -c "from scrapers.cnn_scraper import scrape_cnn_news; print('✓ CNN OK')"

# The Guardian
python -c "from scrapers.theguardian_scraper import scrape_theguardian_news; print('✓ Guardian OK')"
```

### Indonesian News
```cmd
# Kompas
python -c "from scrapers.kompas_scraper import scrape_kompas_news; print('✓ Kompas OK')"

# Tempo
python -c "from scrapers.tempo_scraper import scrape_tempo_news; print('✓ Tempo OK')"

# Kontan
python -c "from scrapers.kontan_scraper import scrape_kontan_news; print('✓ Kontan OK')"

# CNBC Indonesia
python -c "from scrapers.cnbc_indonesia_scraper import scrape_cnbc_indonesia_news; print('✓ CNBC ID OK')"

# Bisnis Indonesia
python -c "from scrapers.bisnis_indonesia_scraper import scrape_bisnis_indonesia_news; print('✓ Bisnis OK')"
```

### Data Scrapers
```cmd
# BPS
python -c "from scrapers.bps_scraper import scrape_bps_data; print('✓ BPS OK')"
```

## 🔄 Test All Scrapers
```cmd
python test_individual_scrapers.py
```

## ✅ Expected Output
```
✓ [Scraper Name] OK
```

## ❌ If Error
```cmd
# Reinstall dependencies
pip install -r requirements.txt

# Check Python version (should be 3.11)
python --version
```

---
**Copy-paste commands di atas untuk quick testing!**
