# Database Architecture Overview
## pei-dashboard.bacpac Schema Structure

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    pei-dashboard.bacpac                         │
│                  (Single Source of Truth)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ├─────────────────────────────────┐
                              │                                 │
                    ┌─────────▼─────────┐          ┌───────────▼──────────┐
                    │  News & Sentiment │          │    Data Tables       │
                    │    (6 tables)     │          │    (22 tables)       │
                    └─────────┬─────────┘          └───────────┬──────────┘
                              │                                 │
        ┌─────────────────────┼─────────────────┐              │
        │                     │                 │              │
┌───────▼────────┐  ┌────────▼────────┐  ┌────▼─────┐  ┌─────▼──────┐
│ news_articles  │  │ sentiment_      │  │ keywords │  │ data_*     │
│ news_sources   │  │   analyses      │  │ article_ │  │ (22 tables)│
│                │  │ sentiment_      │  │ keywords │  │            │
│                │  │   analysis_     │  │          │  │            │
│                │  │   articles      │  │          │  │            │
└────────────────┘  └─────────────────┘  └──────────┘  └────────────┘
        ▲                    ▲                 ▲              ▲
        │                    │                 │              │
┌───────┴────────────────────┴─────────────────┴──────────────┴───────┐
│                     Azure Functions Layer                            │
├──────────────────────────────────────────────────────────────────────┤
│  News Scrapers (19)  │  Data Scrapers (9)  │  Processing (3)        │
│  ✓ CNBC, CNN, etc    │  ✓ ESDM, EIA, etc   │  ✓ Aggregator          │
│  ✓ Reuters, Kompas   │  ✓ BPS, IAEA, etc   │  ✓ Deduplication       │
│  ✓ Tempo, Kontan     │  ✓ SIPSN, GAPKI     │  ✓ Cache               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Table Categories

### 1️⃣ News & Sentiment Layer (6 tables)

```
┌─────────────────────────────────────────────────────────┐
│                   News & Sentiment                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  news_articles ◄──────┬──────► article_keywords        │
│       │               │              │                  │
│       │               │              ▼                  │
│       │               │          keywords               │
│       │               │                                 │
│       │               └──────► news_sources             │
│       │                                                 │
│       └──────────────────────► sentiment_analysis_      │
│                                    articles             │
│                                       │                 │
│                                       ▼                 │
│                               sentiment_analyses        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Relationships:**
- `news_articles` ↔ `news_sources` (many-to-one)
- `news_articles` ↔ `keywords` (many-to-many via `article_keywords`)
- `news_articles` ↔ `sentiment_analyses` (many-to-many via `sentiment_analysis_articles`)

---

### 2️⃣ System Layer (2 tables)

```
┌─────────────────────────────────────────────────────────┐
│                      System Tables                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  execution_logs          configuration                  │
│  ├─ function_name        ├─ config_key                  │
│  ├─ status               ├─ config_value                │
│  ├─ start_time           ├─ category                    │
│  ├─ end_time             └─ is_active                   │
│  └─ error_message                                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### 3️⃣ Data Layer (22 tables)

#### 🌱 Biofuel & Renewable (7 tables)

```
┌─────────────────────────────────────────────────────────┐
│              Biofuel & Renewable Energy                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Biofuel:                                               │
│  ├─ data_biodiesel_hip      (HIP Biodiesel)            │
│  ├─ data_bioetanol_hip      (HIP Bioetanol)            │
│  ├─ data_cpo_prices         (CPO Prices)               │
│  └─ data_saf_uco_prices     (SAF/UCO Prices)           │
│                                                         │
│  Renewable:                                             │
│  ├─ data_ebt_capacity       (EBT Capacity)             │
│  ├─ data_ebt_prices         (EBT Prices)               │
│  └─ data_renewable_energy   (Renewable Data)           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 🛢️ Fossil Fuel & Oil (5 tables)

```
┌─────────────────────────────────────────────────────────┐
│                 Fossil Fuel & Oil                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ├─ data_fossil                (Input Fosil)           │
│  ├─ data_fossil_prediction     (Prediksi Fosil)        │
│  ├─ data_oil_prices            (Harga Minyak)          │
│  ├─ data_oil_crackspreads      (Crackspread)           │
│  └─ data_petrochemical_prices  (Harga Petrokimia)      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### ⚡ Nuclear & Power (3 tables)

```
┌─────────────────────────────────────────────────────────┐
│                  Nuclear & Power                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ├─ data_iaea_electrical         (IAEA Electrical)     │
│  ├─ data_iaea_nuclear_capacity   (Nuclear Capacity)    │
│  └─ data_ruptl_projects          (RUPTL Projects)      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 📈 Market & Economics (4 tables)

```
┌─────────────────────────────────────────────────────────┐
│               Market & Economics                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ├─ data_eia_market                (EIA Market)        │
│  ├─ data_market_indicators         (Kurs, Inflasi)     │
│  ├─ data_volatility_index          (Volatilitas)       │
│  └─ data_geopolitical_risk_index   (Risiko Geopolitik) │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### ♻️ Waste to Energy (3 tables)

```
┌─────────────────────────────────────────────────────────┐
│                 Waste to Energy                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ├─ data_wte_komposisi    (Komposisi Sampah)           │
│  ├─ data_wte_sumber       (Sumber Sampah)              │
│  └─ data_wte_timbulan     (Timbulan Sampah)            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow

### News Scraping Flow

```
┌──────────────┐
│ News Sources │ (Web)
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Scraper Function │ (Azure Function)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ news_articles    │ (Database)
│ news_sources     │
│ keywords         │
│ article_keywords │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Deduplication    │ (Processing)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Sentiment        │ (AI Analysis)
│ Analysis         │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ sentiment_       │ (Database)
│   analyses       │
└──────────────────┘
```

### Data Scraping Flow

```
┌──────────────┐
│ Data Sources │ (ESDM, EIA, BPS, etc)
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Data Scraper     │ (Azure Function)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ data_* tables    │ (Database)
│ (22 tables)      │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Data Cache       │ (Processing)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Dashboard/API    │ (Consumption)
└──────────────────┘
```

---

## 🎯 Key Design Principles

### 1. Single Source of Truth
- ✅ `pei-dashboard.bacpac` is the authoritative schema
- ✅ All code references must match bacpac schema
- ✅ No ad-hoc table creation in code

### 2. Separation of Concerns
- ✅ News data separate from structured data
- ✅ System tables separate from business data
- ✅ Clear table naming convention (`data_*` prefix)

### 3. Normalization
- ✅ Junction tables for many-to-many relationships
- ✅ Foreign key constraints enforced
- ✅ No data duplication

### 4. Scalability
- ✅ Indexed columns for performance
- ✅ Partitioning strategy for large tables
- ✅ Maintenance procedures in place

---

## 📊 Table Size Estimates

| Category | Tables | Est. Rows | Growth Rate |
|----------|--------|-----------|-------------|
| News | 4 | 100K+ | High (daily) |
| Sentiment | 2 | 10K+ | Medium (weekly) |
| System | 2 | 1K+ | Low (as needed) |
| Data | 22 | 50K+ | Medium (varies) |

---

## 🔐 Security & Access

### Access Patterns
```
┌─────────────────────────────────────────────────────────┐
│                   Access Control                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Azure Functions ──► Read/Write ──► All Tables          │
│                                                         │
│  Dashboard API   ──► Read Only  ──► All Tables          │
│                                                         │
│  Admin Tools     ──► Full Access ──► All Tables         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Verification Status

| Component | Status | Last Verified |
|-----------|--------|---------------|
| Schema Definition | ✅ Verified | 2026-02-16 |
| Table Structure | ✅ Verified | 2026-02-16 |
| Relationships | ✅ Verified | 2026-02-16 |
| Indexes | ✅ Verified | 2026-02-16 |
| Constraints | ✅ Verified | 2026-02-16 |
| Code Alignment | ✅ Verified | 2026-02-16 |

---

## 📚 Related Documentation

- **VERIFICATION_SUMMARY_ID.md** - Ringkasan verifikasi
- **TABLE_MAPPING.md** - Mapping scraper ke tabel
- **SCHEMA_VERIFICATION_REPORT.md** - Laporan lengkap
- **VERIFICATION_CHECKLIST.md** - Checklist detail

---

**Architecture Version:** 1.0  
**Last Updated:** 2026-02-16  
**Maintained By:** Development Team  
**Status:** ✅ Production Ready
