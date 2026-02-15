# Database Schema Documentation

**Source:** C:\RunningProjects\Dashboard-Pertamina-VeloCT\pei-dashboard.bacpac
**Extracted:** 2026-02-16 02:51:22
**Version:** 1.0
**Total Tables:** 26

## Tables

- [configuration](#configuration)
- [data_biodiesel_hip](#data-biodiesel-hip)
- [data_bioetanol_hip](#data-bioetanol-hip)
- [data_cpo_prices](#data-cpo-prices)
- [data_ebt_capacity](#data-ebt-capacity)
- [data_ebt_prices](#data-ebt-prices)
- [data_eia_market](#data-eia-market)
- [data_fossil](#data-fossil)
- [data_fossil_prediction](#data-fossil-prediction)
- [data_geopolitical_risk_index](#data-geopolitical-risk-index)
- [data_iaea_electrical](#data-iaea-electrical)
- [data_iaea_nuclear_capacity](#data-iaea-nuclear-capacity)
- [data_market_indicators](#data-market-indicators)
- [data_oil_crackspreads](#data-oil-crackspreads)
- [data_oil_prices](#data-oil-prices)
- [data_petrochemical_prices](#data-petrochemical-prices)
- [data_renewable_energy](#data-renewable-energy)
- [data_ruptl_projects](#data-ruptl-projects)
- [data_saf_uco_prices](#data-saf-uco-prices)
- [data_volatility_index](#data-volatility-index)
- [data_wte_komposisi](#data-wte-komposisi)
- [data_wte_sumber](#data-wte-sumber)
- [data_wte_timbulan](#data-wte-timbulan)
- [execution_logs](#execution-logs)
- [sentiment_analyses](#sentiment-analyses)
- [sentiment_analysis_articles](#sentiment-analysis-articles)

## configuration

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| config_key | nvarchar(100) | No |  |  |
| config_value | ntext | No |  |  |
| config_type | varchar(20) | No |  |  |
| description | nvarchar(500) | Yes |  |  |
| is_sensitive | bit | No |  |  |
| created_at | datetime2 | No |  |  |
| updated_at | datetime2 | No |  |  |

---

## data_biodiesel_hip

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| published_date | datetime2 | Yes |  |  |
| hip_month | nvarchar(50) | Yes |  |  |
| price_idr_liter | float(53) | Yes |  |  |
| scraped_at | datetime2 | Yes |  |  |

---

## data_bioetanol_hip

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| date | date | Yes |  |  |
| bulan_hip | nvarchar(50) | Yes |  |  |
| hip_bioetanol_idr_l | float(53) | Yes |  |  |
| harga_tetes_tebu | float(53) | Yes |  |  |
| created_at | datetime2 | Yes |  |  |

---

## data_cpo_prices

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| upload_date | date | Yes |  |  |
| price_date | date | Yes |  |  |
| px_last | float(53) | Yes |  |  |
| scraped_at | datetime2 | Yes |  |  |

---

## data_ebt_capacity

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| tahun | int | Yes |  |  |
| bulan | int | Yes |  |  |
| plta | float(53) | Yes |  |  |
| pltm | float(53) | Yes |  |  |
| pltmh | float(53) | Yes |  |  |
| pltp | float(53) | Yes |  |  |
| plts | float(53) | Yes |  |  |
| plts_atap | float(53) | Yes |  |  |
| pltb | float(53) | Yes |  |  |
| pltbm | float(53) | Yes |  |  |
| pltbg | float(53) | Yes |  |  |
| pltsa | float(53) | Yes |  |  |
| pltbn | float(53) | Yes |  |  |
| plt_hybrid | float(53) | Yes |  |  |
| total | float(53) | Yes |  |  |
| created_at | datetime2 | Yes |  |  |

---

## data_ebt_prices

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| no | int | Yes |  |  |
| lokasi | nvarchar(255) | Yes |  |  |
| provinsi | nvarchar(255) | Yes |  |  |
| jenis_ebt | nvarchar(255) | Yes |  |  |
| faktor_lokasi | float(53) | Yes |  |  |
| kelompok_hpt | nvarchar(255) | Yes |  |  |
| stage | int | Yes |  |  |
| cent_usd_kwh | float(53) | Yes |  |  |
| lcoe_cent_usd_kwh | float(53) | Yes |  |  |
| battery | float(53) | Yes |  |  |
| created_at | datetime2 | Yes |  |  |

---

## data_eia_market

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| bulan | nvarchar(50) | Yes |  |  |
| tahun | int | Yes |  |  |
| world_total_production | float(53) | Yes |  |  |
| opec | float(53) | Yes |  |  |
| non_opec | float(53) | Yes |  |  |
| crude_oil | float(53) | Yes |  |  |
| other_liquids | float(53) | Yes |  |  |
| world_total_consumption | float(53) | Yes |  |  |
| oecd | float(53) | Yes |  |  |
| non_oecd | float(53) | Yes |  |  |
| next_release_date | datetime2 | Yes |  |  |
| scraped_at | datetime2 | Yes |  |  |

---

## data_fossil

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| time | datetime2 | Yes |  |  |
| brent | float(53) | Yes |  |  |
| gasoline | float(53) | Yes |  |  |
| diesel | float(53) | Yes |  |  |
| avtur | float(53) | Yes |  |  |
| created_at | datetime2 | Yes |  |  |

---

## data_fossil_prediction

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| prediction_year | int | Yes |  |  |
| brent | float(53) | Yes |  |  |
| gasoline | float(53) | Yes |  |  |
| diesel | float(53) | Yes |  |  |
| avtur | float(53) | Yes |  |  |
| fo05_price | float(53) | Yes |  |  |
| go2500_price | float(53) | Yes |  |  |
| go50_price | float(53) | Yes |  |  |
| jetkero_price | float(53) | Yes |  |  |
| ron92_price | float(53) | Yes |  |  |
| ron95_price | float(53) | Yes |  |  |
| ron97_price | float(53) | Yes |  |  |
| fo05_cs | float(53) | Yes |  |  |
| go2500_cs | float(53) | Yes |  |  |
| go50_cs | float(53) | Yes |  |  |
| jetkero_cs | float(53) | Yes |  |  |
| ron92_cs | float(53) | Yes |  |  |
| ron95_cs | float(53) | Yes |  |  |
| ron97_cs | float(53) | Yes |  |  |
| scraped_at | datetime2 | Yes |  |  |

---

## data_geopolitical_risk_index

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| index_date | date | Yes |  |  |
| region | nvarchar(50) | Yes |  |  |
| gpr_value | float(53) | Yes |  |  |
| scraped_at | datetime2 | Yes |  |  |

---

## data_iaea_electrical

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| year | int | Yes |  |  |
| net_electrical_capacity_gwe | float(53) | Yes |  |  |
| num_operated_reactors_with_data | int | Yes |  |  |
| electricity_supplied_twh | float(53) | Yes |  |  |
| created_at | datetime2 | Yes |  |  |

---

## data_iaea_nuclear_capacity

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| year | int | Yes |  |  |
| total_net_electrical_capacity_gw | float(53) | Yes |  |  |
| num_operated_reactors | int | Yes |  |  |
| year_end_total_net_electrical_capacity_gw | float(53) | Yes |  |  |
| year_end_operational_reactors | int | Yes |  |  |
| created_at | datetime2 | Yes |  |  |

---

## data_market_indicators

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| indicator_date | date | Yes |  |  |
| category | nvarchar(50) | Yes |  |  |
| indicator_name | nvarchar(100) | Yes |  |  |
| value | float(53) | Yes |  |  |
| scraped_at | datetime2 | Yes |  |  |

---

## data_oil_crackspreads

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| assess_date | date | Yes |  |  |
| val_ron92 | float(53) | Yes |  |  |
| val_ron95 | float(53) | Yes |  |  |
| val_ron97 | float(53) | Yes |  |  |
| val_fo05 | float(53) | Yes |  |  |
| val_jetkero | float(53) | Yes |  |  |
| val_go50 | float(53) | Yes |  |  |
| val_go2500 | float(53) | Yes |  |  |
| val_brent | float(53) | Yes |  |  |
| val_ron92_mt | float(53) | Yes |  |  |
| val_ron95_mt | float(53) | Yes |  |  |
| cs_ron92 | float(53) | Yes |  |  |
| cs_ron95 | float(53) | Yes |  |  |
| cs_ron97 | float(53) | Yes |  |  |
| scraped_at | datetime2 | Yes |  |  |

---

## data_oil_prices

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| year | int | Yes |  |  |
| month | nvarchar(50) | Yes |  |  |
| price | float(53) | Yes |  |  |
| date_raw | nvarchar(100) | Yes |  |  |
| brent_price | float(53) | Yes |  |  |
| created_at | datetime2 | Yes |  |  |

---

## data_petrochemical_prices

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| year | int | Yes |  |  |
| month | int | Yes |  |  |
| price_paraxylene | float(53) | Yes |  |  |
| price_propylene | float(53) | Yes |  |  |
| price_benzene | float(53) | Yes |  |  |
| price_butane | float(53) | Yes |  |  |
| price_propane | float(53) | Yes |  |  |
| price_lpg | float(53) | Yes |  |  |
| price_brent | float(53) | Yes |  |  |
| cs_paraxylene | float(53) | Yes |  |  |
| cs_propylene | float(53) | Yes |  |  |
| cs_benzene | float(53) | Yes |  |  |
| cs_lpg | float(53) | Yes |  |  |
| scraped_at | datetime2 | Yes |  |  |

---

## data_renewable_energy

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| indicator_date | date | Yes |  |  |
| energy_type | nvarchar(50) | Yes |  |  |
| metric_name | nvarchar(50) | Yes |  |  |
| region | nvarchar(100) | Yes |  |  |
| value | float(53) | Yes |  |  |
| uom | nvarchar(20) | Yes |  |  |
| scraped_at | datetime2 | Yes |  |  |

---

## data_ruptl_projects

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| number | int | Yes |  |  |
| province | nvarchar(100) | Yes |  |  |
| electric_system | nvarchar(255) | Yes |  |  |
| power_plant_type | nvarchar(255) | Yes |  |  |
| project_name | nvarchar(255) | Yes |  |  |
| capacity_mw | float(53) | Yes |  |  |
| target_cod_re_base | nvarchar(50) | Yes |  |  |
| target_cod_ared | nvarchar(50) | Yes |  |  |
| status | nvarchar(100) | Yes |  |  |
| developer | nvarchar(255) | Yes |  |  |
| notes | nvarchar | Yes |  |  |
| created_at | datetime2 | Yes |  |  |

---

## data_saf_uco_prices

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| assess_date | date | Yes |  |  |
| value_uco | float(53) | Yes |  |  |
| value_saf | float(53) | Yes |  |  |
| mod_date_uco | datetime2 | Yes |  |  |
| mod_date_saf | datetime2 | Yes |  |  |
| scraped_at | datetime2 | Yes |  |  |

---

## data_volatility_index

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| indicator_date | date | Yes |  |  |
| index_name | nvarchar(50) | Yes |  |  |
| index_value | float(53) | Yes |  |  |
| scraped_at | datetime2 | Yes |  |  |

---

## data_wte_komposisi

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| year | int | Yes |  |  |
| province | nvarchar(255) | Yes |  |  |
| city_regency | nvarchar(255) | Yes |  |  |
| sisa_makanan | float(53) | Yes |  |  |
| kayu_ranting | float(53) | Yes |  |  |
| kertas_karton | float(53) | Yes |  |  |
| plastik | float(53) | Yes |  |  |
| logam | float(53) | Yes |  |  |
| kain | float(53) | Yes |  |  |
| karet_kulit | float(53) | Yes |  |  |
| kaca | float(53) | Yes |  |  |
| lain_lain | float(53) | Yes |  |  |
| created_at | datetime2 | Yes |  |  |

---

## data_wte_sumber

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| year | int | Yes |  |  |
| province | nvarchar(255) | Yes |  |  |
| city_regency | nvarchar(255) | Yes |  |  |
| ss_rumah_tangga | float(53) | Yes |  |  |
| ss_perkantoran | float(53) | Yes |  |  |
| ss_pasar | float(53) | Yes |  |  |
| ss_perniagaan | float(53) | Yes |  |  |
| ss_fasilitas_publik | float(53) | Yes |  |  |
| ss_kawasan | float(53) | Yes |  |  |
| ss_lain_lain | float(53) | Yes |  |  |
| created_at | datetime2 | Yes |  |  |

---

## data_wte_timbulan

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | int | No |  | IDENTITY |
| year | int | Yes |  |  |
| province | nvarchar(255) | Yes |  |  |
| city_regency | nvarchar(255) | Yes |  |  |
| timbulan_harian | float(53) | Yes |  |  |
| timbulan_tahunan | float(53) | Yes |  |  |
| created_at | datetime2 | Yes |  |  |

---

## execution_logs

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | uniqueidentifier | No |  |  |
| function_name | nvarchar(100) | No |  |  |
| execution_id | nvarchar(100) | No |  |  |
| start_time | datetime2 | No |  |  |
| end_time | datetime2 | Yes |  |  |
| status | varchar(20) | No |  |  |
| error_message | ntext | Yes |  |  |
| input_parameters | ntext | Yes |  |  |
| output_summary | ntext | Yes |  |  |
| duration_ms | int | Yes |  |  |
| created_at | datetime2 | No |  |  |

---

## sentiment_analyses

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | uniqueidentifier | No |  |  |
| analysis_date | datetime2 | No |  |  |
| date_range_start | datetime2 | No |  |  |
| date_range_end | datetime2 | No |  |  |
| sentiment_score | float(53) | No |  |  |
| sentiment_label | varchar(20) | No |  |  |
| confidence | float(53) | No |  |  |
| summary | ntext | No |  |  |
| model_version | varchar(50) | No |  |  |
| role_context | nvarchar(200) | Yes |  |  |
| article_count | int | No |  |  |
| created_at | datetime2 | No |  |  |
| updated_at | datetime2 | No |  |  |
| reference_topic | nvarchar(100) | Yes |  |  |

---

## sentiment_analysis_articles

### Columns

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| sentiment_analysis_id | uniqueidentifier | No |  |  |
| article_id | uniqueidentifier | No |  |  |
| created_at | datetime2 | No |  |  |

---
