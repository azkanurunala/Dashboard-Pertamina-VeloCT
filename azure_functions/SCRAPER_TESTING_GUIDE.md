# Panduan Testing Scraper

Dokumentasi lengkap untuk menjalankan dan test setiap scraper satu per satu.

## 📋 Daftar Scrapers

### International News Scrapers
1. **CNBC** - CNBC International news
2. **OilPrice** - OilPrice.com energy news
3. **Reuters** - Reuters news agency
4. **CNN** - CNN news
5. **The Guardian** - The Guardian UK news

### Indonesian News Scrapers
6. **Kompas** - Kompas.com
7. **Tempo** - Tempo.co
8. **Kontan** - Kontan.co.id
9. **CNBC Indonesia** - CNBC Indonesia
10. **Bisnis Indonesia** - Bisnis.com

### Data Scrapers
11. **BPS** - Badan Pusat Statistik (Indonesian Statistics)

## 🚀 Cara Menjalankan

### Opsi 1: Menu Interaktif (Batch Script) - PALING MUDAH

```cmd
cd azure_functions
test_scrapers.bat
```

Menu akan muncul:
```
========================================
SCRAPER TESTING MENU
========================================

Select scraper to test:

1.  CNBC (International)
2.  OilPrice
3.  Reuters
4.  CNN
5.  The Guardian
6.  Kompas (Indonesia)
7.  Tempo (Indonesia)
8.  Kontan (Indonesia)
9.  CNBC Indonesia
10. Bisnis Indonesia
11. BPS (Data)
12. Test ALL Scrapers
0.  Exit

Enter your choice (0-12):
```

Pilih nomor scraper yang ingin di-test, tekan Enter.

### Opsi 2: PowerShell Script

```powershell
cd azure_functions
.\test_scrapers_one_by_one.ps1
```

### Opsi 3: Python Script - Test Semua Sekaligus

```cmd
cd azure_functions
python test_individual_scrapers.py
```

Script ini akan:
- Test semua 11 scrapers secara berurutan
- Menampilkan progress untuk setiap scraper
- Memberikan summary lengkap di akhir

### Opsi 4: Test Manual Satu per Satu

#### Test CNBC Scraper
```cmd
cd azure_functions
python -c "import sys; sys.path.insert(0, '.'); from scrapers.cnbc_scraper import CNBCNewsScraper; print('✓ CNBC OK')"
```

#### Test OilPrice Scraper
```cmd
python -c "import sys; sys.path.insert(0, '.'); from scrapers.oilprice_scraper import scrape_oilprice_news; print('✓ OilPrice OK')"
```

#### Test Reuters Scraper
```cmd
python -c "import sys; sys.path.insert(0, '.'); from scrapers.reuters_scraper import ReutersNewsScraper; print('✓ Reuters OK')"
```

#### Test CNN Scraper
```cmd
python -c "import sys; sys.path.insert(0, '.'); from scrapers.cnn_scraper import scrape_cnn_news; print('✓ CNN OK')"
```

#### Test The Guardian Scraper
```cmd
python -c "import sys; sys.path.insert(0, '.'); from scrapers.theguardian_scraper import scrape_theguardian_news; print('✓ Guardian OK')"
```

#### Test Kompas Scraper
```cmd
python -c "import sys; sys.path.insert(0, '.'); from scrapers.kompas_scraper import scrape_kompas_news; print('✓ Kompas OK')"
```

#### Test Tempo Scraper
```cmd
python -c "import sys; sys.path.insert(0, '.'); from scrapers.tempo_scraper import scrape_tempo_news; print('✓ Tempo OK')"
```

#### Test Kontan Scraper
```cmd
python -c "import sys; sys.path.insert(0, '.'); from scrapers.kontan_scraper import scrape_kontan_news; print('✓ Kontan OK')"
```

#### Test CNBC Indonesia Scraper
```cmd
python -c "import sys; sys.path.insert(0, '.'); from scrapers.cnbc_indonesia_scraper import scrape_cnbc_indonesia_news; print('✓ CNBC Indonesia OK')"
```

#### Test Bisnis Indonesia Scraper
```cmd
python -c "import sys; sys.path.insert(0, '.'); from scrapers.bisnis_indonesia_scraper import scrape_bisnis_indonesia_news; print('✓ Bisnis Indonesia OK')"
```

#### Test BPS Scraper
```cmd
python -c "import sys; sys.path.insert(0, '.'); from scrapers.bps_scraper import scrape_bps_data; print('✓ BPS OK')"
```

## 📊 Output yang Diharapkan

### Jika Berhasil:
```
✓ Import successful
✓ Scraper initialized
✓ Scraping completed: X articles found
✓ [Scraper Name]: PASSED
```

### Jika Gagal:
```
✗ Error: [error message]
✗ [Scraper Name]: FAILED
```

## 🔍 Troubleshooting

### Error: ModuleNotFoundError
**Problem**: Module tidak ditemukan
**Solution**: 
```cmd
cd azure_functions
pip install -r requirements.txt
```

### Error: Import Error
**Problem**: Import path salah
**Solution**: Pastikan menjalankan dari folder `azure_functions`
```cmd
cd azure_functions
python test_scrapers.bat
```

### Error: Connection Error
**Problem**: Tidak bisa connect ke website
**Solution**: 
- Check koneksi internet
- Beberapa website mungkin memerlukan VPN
- Coba lagi nanti (website mungkin down)

### Error: Timeout
**Problem**: Scraping terlalu lama
**Solution**:
- Normal untuk scraper yang mengambil banyak artikel
- Tunggu sampai selesai atau tekan Ctrl+C untuk stop

## 📝 Test Results Summary

Setelah menjalankan `test_individual_scrapers.py`, Anda akan mendapat summary seperti:

```
======================================================================
TEST SUMMARY
======================================================================

Total Scrapers Tested: 11
✓ Successful: 11
✗ Failed: 0
📰 Total Articles/Data: 150

Detailed Results:
----------------------------------------------------------------------
✓ CNBC                | Status: success    | Articles: 15
✓ OilPrice            | Status: success    | Articles: 10
✓ Reuters             | Status: success    | Articles: 20
✓ CNN                 | Status: success    | Articles: 12
✓ The Guardian        | Status: success    | Articles: 18
✓ Kompas              | Status: success    | Articles: 15
✓ Tempo               | Status: success    | Articles: 14
✓ Kontan              | Status: success    | Articles: 13
✓ CNBC Indonesia      | Status: success    | Articles: 11
✓ Bisnis Indonesia    | Status: success    | Articles: 12
✓ BPS                 | Status: success    | Articles: 10

======================================================================
✓ ALL SCRAPERS WORKING CORRECTLY!
======================================================================
```

## 🎯 Quick Commands

### Test semua scraper sekaligus:
```cmd
cd azure_functions
python test_individual_scrapers.py
```

### Test dengan menu interaktif:
```cmd
cd azure_functions
test_scrapers.bat
```

### Test satu scraper cepat (contoh CNBC):
```cmd
cd azure_functions
python -c "from scrapers.cnbc_scraper import CNBCNewsScraper; print('✓ OK')"
```

## 📁 File-file Testing

1. **test_scrapers.bat** - Menu interaktif Windows (RECOMMENDED)
2. **test_scrapers_one_by_one.ps1** - PowerShell script dengan menu
3. **test_individual_scrapers.py** - Python script lengkap untuk test semua
4. **SCRAPER_TESTING_GUIDE.md** - Dokumentasi ini

## ✅ Checklist Testing

Sebelum deploy ke Azure, pastikan:

- [ ] Semua scraper bisa di-import tanpa error
- [ ] Test minimal 1 scraper dari setiap kategori (International, Indonesia, Data)
- [ ] Verifikasi artikel yang di-scrape memiliki data lengkap
- [ ] Check tidak ada error di console
- [ ] Pastikan Python 3.11 compatibility (sudah di-fix)
- [ ] Verifikasi import path sudah menggunakan absolute imports

## 🔗 Related Documentation

- **Python 3.11 Compatibility**: `PYTHON_311_COMPATIBILITY_STATUS.md`
- **Import Path Fix**: `IMPORT_PATH_FIX_SUMMARY.md`
- **Comprehensive Logging**: `COMPREHENSIVE_LOGGING_GUIDE.md`

## 💡 Tips

1. **Test lokal dulu** sebelum deploy ke Azure
2. **Gunakan menu interaktif** (`test_scrapers.bat`) untuk testing cepat
3. **Run test lengkap** (`test_individual_scrapers.py`) sebelum commit
4. **Check logs** jika ada error untuk debugging
5. **Test dengan keywords berbeda** untuk hasil lebih akurat

## 📞 Support

Jika ada masalah:
1. Check error message di console
2. Lihat troubleshooting section di atas
3. Verifikasi semua dependencies ter-install
4. Pastikan Python 3.11 digunakan: `python --version`

---

**Last Updated**: January 28, 2026
**Python Version**: 3.11.0
**Status**: All scrapers verified working ✅
