# Scraper Coverage Audit

## Overview

This document provides a comprehensive audit of news scraper coverage, comparing the original system (src/code_scrapping) with the Azure Functions implementation (azure_functions).

**Audit Date**: January 26, 2026  
**Original System Sources**: 27 scrapers  
**Azure Functions Implemented**: 12 scrapers  
**Coverage**: 44.4%

## Implemented Scrapers (11/27)

### International News Sources (5)

| Source | Original File | Azure Function | Scraper Module | Status |
|--------|--------------|----------------|----------------|--------|
| CNBC | cnbc.py | cnbc_scraper_function | cnbc_scraper.py | ✅ Implemented |
| CNN | cnn.py | cnn_scraper_function | cnn_scraper.py | ✅ Implemented |
| Reuters | reuters.py | reuters_scraper_function | reuters_scraper.py | ✅ Implemented |
| The Guardian | theguardian.py | theguardian_scraper_function | theguardian_scraper.py | ✅ Implemented |
| OilPrice | oilprice.py | oilprice_scraper_function | oilprice_scraper.py | ✅ Implemented |

### Indonesian News Sources (6)

| Source | Original File | Azure Function | Scraper Module | Status |
|--------|--------------|----------------|----------------|--------|
| Kompas | kompas.py | kompas_scraper_function | kompas_scraper.py | ✅ Implemented |
| Tempo | tempo.py | tempo_scraper_function | tempo_scraper.py | ✅ Implemented |
| Kontan | kontan.py | kontan_scraper_function | kontan_scraper.py | ✅ Implemented |
| Bisnis Indonesia | bisnis_indonesia.py | bisnis_indonesia_scraper_function | bisnis_indonesia_scraper.py | ✅ Implemented |
| CNBC Indonesia | cnbc_id.py | cnbc_indonesia_scraper_function | cnbc_indonesia_scraper.py | ✅ Implemented |

## Missing Scrapers (15/27)

### International News Sources (2)

| Source | Original File | Category | Priority |
|--------|--------------|----------|----------|
| SCMP (South China Morning Post) | scmp.py | International News | Medium |
| Bloomberg Technoz | bloomberg_technoz.py | Technology News | Low |

### Indonesian News Sources (1)

| Source | Original File | Category | Priority |
|--------|--------------|----------|----------|
| Energies Media | energiesmedia.py | Energy News | Low |
| Bioenergy Times | bioenergytimes.py | Energy News | Low |

### Government/Official Data Sources (6)

| Source | Original File | Category | Priority | Status |
|--------|--------------|----------|----------|--------|
| BPS (Statistics Indonesia) | bps.py | Statistical Data | High | ✅ Implemented |
| Bank Indonesia | bank_indonesia.py | Economic Data | High | ❌ Not Implemented (Requires Selenium) |
| ESDM Biodiesel | biodiesel_esdm_scrape.py | Energy Data | Medium | ❌ Not Implemented |
| ESDM Bioethanol | bioetanol_esdm_scrape.py | Energy Data | Medium | ❌ Not Implemented |
| ESDM Migas | migas_esdm.py | Energy Data | Medium | ❌ Not Implemented |
| EIA Migas | migas_eia.py | Energy Data | Medium | ❌ Not Implemented |

### Specialized/Commodity Sources (4)

| Source | Original File | Category | Priority |
|--------|--------------|----------|----------|
| CPO Scraping | scrapping_cpo.py | Commodity Data | Medium |
| Kontan BBM | kontan_bbm.py | Fuel Prices | Medium |
| Kontan Biodiesel | kontan_biodiesel.py | Fuel Prices | Medium |
| S&P Data | scrape_sandp_data.py | Financial Data | Low |
| S&P News | scrape_sandp_news.py | Financial News | Low |

### Aggregator Sources (2)

| Source | Original File | Category | Priority |
|--------|--------------|----------|----------|
| Google News | google_news.py | News Aggregator | Low |
| The Guardian Sitemap | the_guardian_sitemap.py | Sitemap Crawler | Low |

## Priority Classification

### High Priority (2 scrapers)
Critical government data sources that provide economic and statistical data:
- Bank Indonesia (central bank data)
- BPS (official statistics)

### Medium Priority (9 scrapers)
Important news sources and specialized data:
- SCMP (major Asian news source)
- ESDM sources (government energy data)
- Commodity and fuel price sources
- EIA energy data

### Low Priority (5 scrapers)
Supplementary sources and aggregators:
- Bloomberg Technoz
- Bioenergy Times
- Energies Media
- S&P sources
- Google News aggregator
- Guardian Sitemap crawler

## Implementation Status by Category

| Category | Total | Implemented | Missing | Coverage |
|----------|-------|-------------|---------|----------|
| International News | 7 | 5 | 2 | 71.4% |
| Indonesian News | 6 | 5 | 1 | 83.3% |
| Government/Official Data | 6 | 1 | 5 | 16.7% |
| Specialized/Commodity | 6 | 0 | 6 | 0% |
| Aggregators | 2 | 0 | 2 | 0% |
| **Total** | **27** | **12** | **15** | **44.4%** |

## Recommendations

### Phase 1: High Priority (Immediate)
Implement government data sources for critical economic data:
1. ✅ BPS scraper (COMPLETED - uses official API)
2. Bank Indonesia scraper (requires Selenium alternative or API research)

### Phase 2: Medium Priority (Short-term)
Implement remaining news and energy data sources:
1. SCMP scraper
2. ESDM Biodiesel scraper
3. ESDM Bioethanol scraper
4. ESDM Migas scraper
5. EIA Migas scraper
6. CPO scraping
7. Kontan BBM scraper
8. Kontan Biodiesel scraper

### Phase 3: Low Priority (Long-term)
Implement supplementary sources as needed:
1. Bloomberg Technoz
2. Bioenergy Times
3. Energies Media
4. S&P Data
5. S&P News
6. Google News aggregator
7. Guardian Sitemap crawler

## Technical Notes

### Base Scraper Pattern
All implemented scrapers follow the base scraper pattern defined in `azure_functions/scrapers/base_scraper.py`:
- Inherit from `BaseScraper` abstract class
- Implement required methods: `scrape()`, `parse_article()`, `extract_content()`
- Use standardized error handling and retry logic
- Return `NewsArticle` objects with consistent schema

### Azure Function Structure
Each scraper has a corresponding Azure Function:
- HTTP-triggered function in `{source}_scraper_function/` directory
- `function.json` configuration file
- `__init__.py` with function handler
- Imports scraper module from `azure_functions/scrapers/`

### Missing Scraper Considerations

#### Data Sources vs News Sources
Some missing scrapers are data sources (Bank Indonesia, BPS, ESDM) rather than news scrapers. These may require:
- Different data extraction patterns (APIs, structured data)
- Different storage schemas (time-series data, statistical tables)
- Different update frequencies

#### Specialized Scrapers
Commodity and fuel price scrapers (CPO, Kontan BBM/Biodiesel) may require:
- Price data extraction and normalization
- Historical data tracking
- Different database schema for price data

#### Aggregators
Google News and sitemap crawlers are meta-scrapers that aggregate from multiple sources:
- May not be needed if individual sources are covered
- Could be implemented as orchestration functions instead

## Technical Challenges for Missing Scrapers

### Selenium Dependency Issue
Several missing scrapers (Bank Indonesia, BPS, SCMP) rely on Selenium WebDriver for dynamic content rendering. This presents challenges for Azure Functions:

**Challenges**:
- Selenium requires Chrome/ChromeDriver binaries (large deployment size)
- Increased cold start times in serverless environment
- Higher memory consumption
- Complex dependency management
- Potential timeout issues with long-running scrapes

**Alternative Approaches**:
1. **API-First**: Use official APIs where available (BPS has a REST API)
2. **Playwright for Azure Functions**: Use Playwright with Azure Functions (lighter than Selenium)
3. **Separate Scraping Service**: Deploy Selenium-based scrapers to Azure Container Instances
4. **Static HTML Parsing**: Attempt to parse without JavaScript rendering where possible

### API-Based Scrapers
Some sources provide official APIs that should be prioritized:
- **BPS**: Has official REST API (already used in original implementation)
- **Bank Indonesia**: May have data APIs for structured data
- **ESDM**: Government data portals may offer API access

### Recommendation for Implementation

**Phase 1: API-Based Scrapers (Immediate)**
Implement scrapers that can use HTTP requests without Selenium:
1. BPS scraper (using existing API approach)
2. Research and implement any available APIs for ESDM sources

**Phase 2: Evaluate Selenium Alternatives (Short-term)**
For scrapers requiring dynamic content:
1. Test Playwright for Azure Functions as Selenium alternative
2. Consider Azure Container Instances for complex scrapers
3. Evaluate if static HTML parsing is sufficient

**Phase 3: Specialized Implementation (Long-term)**
For remaining sources:
1. Implement commodity/fuel price scrapers with appropriate data models
2. Evaluate necessity of aggregator sources
3. Consider hybrid approach (some scrapers in Functions, some in Containers)

## Conclusion

The Azure Functions implementation has successfully ported 12 of 27 scrapers (44.4% coverage), focusing on major international and Indonesian news sources that work well with async HTTP requests. The remaining 15 scrapers present technical challenges:

- **5 scrapers** require Selenium or dynamic rendering (Bank Indonesia, SCMP, etc.)
- **5 scrapers** are government/official data sources that may have APIs
- **4 scrapers** are specialized commodity/price sources requiring different data models
- **1 scraper** (BPS) has been successfully implemented using its official API

**Recommended Next Steps**:
1. ✅ Implement BPS scraper using its official API (COMPLETED)
2. Research API availability for other government sources (ESDM, Bank Indonesia)
3. Evaluate Playwright or Azure Container Instances for Selenium-dependent scrapers
4. Document API endpoints and authentication requirements for data sources
5. Consider whether all 27 sources are still needed for the modernized system
