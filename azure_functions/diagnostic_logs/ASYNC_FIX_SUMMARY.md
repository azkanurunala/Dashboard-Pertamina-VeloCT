# Async Function Signature Fix Summary

**Date**: 2026-01-28  
**Issue**: 7 scraper functions use `async def main()` which Azure Functions doesn't support  
**Solution**: Convert to sync `def main()` with `asyncio.run()` for async operations  
**Status**: Ready to implement

---

## Problem Identified

Azure Functions HTTP triggers require a **synchronous** `def main()` function. However, 7 scraper functions are using `async def main()`, which causes immediate failure.

### Evidence

**Working Functions** (use sync `def main()` + `asyncio.run()`):
- ✅ cnbc_scraper_function
- ✅ cnn_scraper_function  
- ✅ reuters_scraper_function

**Failing Functions** (use `async def main()`):
- ❌ theguardian_scraper_function
- ❌ oilprice_scraper_function
- ❌ bisnis_indonesia_scraper_function
- ❌ cnbc_indonesia_scraper_function
- ❌ kompas_scraper_function
- ❌ kontan_scraper_function
- ❌ tempo_scraper_function

---

## Solution Pattern

### Current (WRONG):
```python
async def main(req: func.HttpRequest) -> func.HttpResponse:
    articles = await scrape_theguardian_news(...)
    # ... rest of code
```

### Fixed (CORRECT):
```python
def main(req: func.HttpRequest) -> func.HttpResponse:
    """Main Azure Function entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info('The Guardian scraper function triggered')
    
    try:
        # Parse request parameters
        params = _parse_request_parameters(req)
        logger.info(f"Scraping The Guardian with parameters: {params}")
        
        # Run the scraping operation using asyncio.run()
        result = asyncio.run(_scrape_theguardian_news(params))
        
        # Return successful response
        return func.HttpResponse(
            json.dumps(result, indent=2, default=str),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "error": "Internal server error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )

async def _scrape_theguardian_news(params: Dict[str, Any]) -> Dict[str, Any]:
    """Perform The Guardian news scraping operation."""
    # ... async scraping logic here
```

---

## Functions to Fix

### 1. theguardian_scraper_function/__init__.py
- Change: `async def main()` → `def main()`
- Add: `asyncio.run(_scrape_theguardian_news())`
- Create: `async def _scrape_theguardian_news()`

### 2. oilprice_scraper_function/__init__.py
- Change: `async def main()` → `def main()`
- Add: `asyncio.run(_scrape_oilprice_news())`
- Create: `async def _scrape_oilprice_news()`

### 3. bisnis_indonesia_scraper_function/__init__.py
- Change: `async def main()` → `def main()`
- Add: `asyncio.run(_scrape_bisnis_news())`
- Create: `async def _scrape_bisnis_news()`

### 4. cnbc_indonesia_scraper_function/__init__.py
- Change: `async def main()` → `def main()`
- Add: `asyncio.run(_scrape_cnbc_indonesia_news())`
- Create: `async def _scrape_cnbc_indonesia_news()`

### 5. kompas_scraper_function/__init__.py
- Change: `async def main()` → `def main()`
- Add: `asyncio.run(_scrape_kompas_news())`
- Create: `async def _scrape_kompas_news()`

### 6. kontan_scraper_function/__init__.py
- Change: `async def main()` → `def main()`
- Add: `asyncio.run(_scrape_kontan_news())`
- Create: `async def _scrape_kontan_news()`

### 7. tempo_scraper_function/__init__.py
- Change: `async def main()` → `def main()`
- Add: `asyncio.run(_scrape_tempo_news())`
- Create: `async def _scrape_tempo_news()`

---

## Implementation Steps

For each function:

1. **Import asyncio** (if not already imported)
2. **Change function signature**: `async def main()` → `def main()`
3. **Add parameter parsing** (if not exists)
4. **Create async helper function**: `async def _scrape_xxx_news(params)`
5. **Call with asyncio.run()**: `result = asyncio.run(_scrape_xxx_news(params))`
6. **Add error handling** with proper JSON responses
7. **Add logging** for debugging

---

## Expected Outcome

After fixing all 7 functions:
- ✅ Functions will start successfully
- ✅ HTTP 500 errors will be resolved
- ✅ Functions will return HTTP 200 with article data
- ✅ Error messages will be properly logged and returned

---

## Next Steps

1. Fix all 7 async function signatures
2. Test locally if possible
3. Redeploy to Azure with remote build
4. Test each function via HTTP request
5. Verify HTTP 200 responses

