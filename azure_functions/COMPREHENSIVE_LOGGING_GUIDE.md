# Comprehensive Logging Implementation Guide

## Overview

Panduan ini menjelaskan cara mengimplementasikan comprehensive logging untuk semua Azure Functions scrapers dan schedulers. Logging yang baru memberikan visibilitas penuh terhadap eksekusi function di Azure Log Stream dan Application Insights.

## Fitur Utama

### 1. **Structured Logging**
- Format JSON yang konsisten untuk semua log entries
- Custom dimensions untuk filtering di Application Insights
- Correlation ID untuk tracking across functions

### 2. **Automatic Context Enrichment**
- Execution ID unik untuk setiap function invocation
- Timestamp otomatis dalam format ISO 8601
- Function name dan source name otomatis ditambahkan

### 3. **Security & Sanitization**
- Automatic redaction untuk passwords, tokens, API keys
- URL parameter sanitization
- Connection string sanitization

### 4. **Performance Metrics**
- Execution time tracking
- Database operation metrics
- Throughput calculations (articles per second)

## Implementasi untuk Scraper Functions

### Step 1: Import AzureLoggingManager

Tambahkan import di bagian atas file `__init__.py`:

```python
try:
    from ..shared.azure_logging import AzureLoggingManager
    logging.info("✓ Successfully imported AzureLoggingManager")
except Exception as e:
    logging.error(f"✗ IMPORT ERROR - AzureLoggingManager: {str(e)}", exc_info=True)
    raise
```

### Step 2: Initialize Logging Manager di Main Function

```python
def main(req: func.HttpRequest) -> func.HttpResponse:
    # Initialize comprehensive logging
    correlation_id = req.headers.get('x-correlation-id')
    log_manager = AzureLoggingManager(
        function_name="your_scraper_function",  # e.g., "kompas_scraper_function"
        correlation_id=correlation_id
    )
    
    try:
        # Parse parameters
        params = _parse_request_parameters(req)
        
        # Log function start
        log_manager.log_function_start(
            trigger_type="http",
            parameters={
                "keywords": params['keywords'],
                "start_date": params['start_date'].isoformat(),
                "end_date": params['end_date'].isoformat(),
                "save_to_db": params.get('save_to_db', True)
            }
        )
        
        # Execute scraping
        result = asyncio.run(_scrape_news(params, log_manager))
        
        # Log function completion
        log_manager.log_function_end(
            status="success",
            result_summary={
                "articles_found": result['results']['articles_found'],
                "articles_saved": result['results']['articles_saved'],
                "execution_time_seconds": result['execution_time_seconds']
            }
        )
        
        return func.HttpResponse(
            json.dumps(result, indent=2, default=str),
            status_code=200,
            mimetype="application/json"
        )
        
    except ValueError as e:
        # Log parameter validation error
        log_manager.log_error(
            error=e,
            context_data={
                "error_type": "parameter_validation",
                "operation": "parse_parameters"
            }
        )
        
        log_manager.log_function_end(
            status="failed",
            result_summary={"error": "Invalid parameters", "message": str(e)}
        )
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "error": "Invalid parameters",
                "message": str(e),
                "execution_id": log_manager.execution_id,
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=400,
            mimetype="application/json"
        )
        
    except Exception as e:
        # Log unexpected error
        log_manager.log_error(
            error=e,
            context_data={
                "error_type": "unexpected_error",
                "operation": "scraping",
                "parameters": params if 'params' in locals() else {}
            }
        )
        
        log_manager.log_function_end(
            status="failed",
            result_summary={"error": "Internal server error", "message": str(e)}
        )
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "error": "Internal server error",
                "message": str(e),
                "error_type": type(e).__name__,
                "execution_id": log_manager.execution_id,
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )
```

### Step 3: Update Scraping Function

Update function signature untuk menerima `log_manager`:

```python
async def _scrape_news(params: Dict[str, Any], log_manager: AzureLoggingManager) -> Dict[str, Any]:
    start_time = datetime.utcnow()
    
    # Log scraping start
    log_manager.log_scraping_start(
        source="YourSource",  # e.g., "Kompas", "Kontan", etc.
        keywords=params['keywords'],
        date_range={
            'start': params['start_date'].isoformat(),
            'end': params['end_date'].isoformat()
        }
    )
    
    try:
        # Start operation tracking
        operation_id = log_manager.log_operation_start(
            operation_name="scrape_articles",
            details={
                "source": "YourSource",
                "keywords_count": len(params['keywords']),
                "date_range_days": (params['end_date'] - params['start_date']).days
            }
        )
        
        # Scrape articles
        articles = await your_scraper_function(
            keywords=params['keywords'],
            start_date=params['start_date'],
            end_date=params['end_date']
        )
        
        # Log articles found
        log_manager.log_scraping_articles_found(
            count=len(articles),
            parsing_success_rate=100.0 if articles else 0.0
        )
        
        # Save to database
        saved_count = 0
        if articles:
            try:
                db_start = datetime.utcnow()
                connection_string = get_database_connection_string()
                
                async with DatabaseHandler(connection_string) as db:
                    saved_count = await db.save_articles(articles)
                
                db_duration = (datetime.utcnow() - db_start).total_seconds() * 1000
                
                # Log database operation
                log_manager.log_database_operation(
                    operation="INSERT",
                    table="news_articles",
                    row_count=saved_count,
                    duration_ms=db_duration
                )
                
                # Log articles saved
                log_manager.log_scraping_articles_saved(
                    saved_count=saved_count,
                    duplicate_count=len(articles) - saved_count,
                    duration_ms=db_duration
                )
                
            except Exception as e:
                # Log database error
                log_manager.log_database_error(
                    error=e,
                    query_type="INSERT",
                    table="news_articles"
                )
        
        # Calculate execution time
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        execution_time_ms = execution_time * 1000
        
        # Log scraping end
        log_manager.log_scraping_end(
            articles_scraped=len(articles),
            articles_saved=saved_count,
            duration_ms=execution_time_ms
        )
        
        # Log operation end
        log_manager.log_operation_end(
            operation_id=operation_id,
            status="success",
            metrics={
                "articles_found": len(articles),
                "articles_saved": saved_count,
                "execution_time_ms": execution_time_ms
            }
        )
        
        return {
            "status": "success",
            "source": "YourSource",
            "execution_time_seconds": execution_time,
            "execution_id": log_manager.execution_id,
            "correlation_id": log_manager.correlation_id,
            "parameters": {
                "keywords": params['keywords'],
                "start_date": params['start_date'].isoformat(),
                "end_date": params['end_date'].isoformat()
            },
            "results": {
                "articles_found": len(articles),
                "articles_saved": saved_count
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log error
        log_manager.log_error(
            error=e,
            context_data={
                "operation": "scraping",
                "source": "YourSource",
                "execution_time_seconds": execution_time
            }
        )
        
        # Log operation end with failure
        if 'operation_id' in locals():
            log_manager.log_operation_end(
                operation_id=operation_id,
                status="failed",
                metrics={"execution_time_seconds": execution_time}
            )
        
        raise
```

## Implementasi untuk Scheduler Functions

### Scheduler Logging Pattern

```python
def main(timer: func.TimerRequest) -> None:
    # Initialize logging
    log_manager = AzureLoggingManager(
        function_name="daily_morning_scheduler"
    )
    
    try:
        # Log scheduler trigger
        log_manager.log_scheduler_trigger(
            schedule_name="Daily Morning Scraping",
            trigger_time=datetime.utcnow(),
            workflow_params={
                "scrapers": ["kompas", "kontan", "cnbc"],
                "parallel_execution": True
            }
        )
        
        # Define scrapers to run
        scrapers = ["kompas", "kontan", "cnbc", "bisnis_indonesia"]
        
        # Log orchestration
        log_manager.log_scheduler_orchestration(
            scrapers=scrapers,
            parallel_count=2  # Number of parallel executions
        )
        
        # Execute scrapers (simplified)
        results = await execute_scrapers(scrapers, log_manager.correlation_id)
        
        # Log aggregation
        total_articles = sum(r['articles_found'] for r in results)
        success_rate = (len([r for r in results if r['status'] == 'success']) / len(results)) * 100
        
        log_manager.log_scheduler_aggregation(
            total_articles=total_articles,
            success_rate=success_rate,
            metrics={
                "scrapers_executed": len(scrapers),
                "scrapers_succeeded": len([r for r in results if r['status'] == 'success']),
                "scrapers_failed": len([r for r in results if r['status'] == 'failed'])
            }
        )
        
        # Log completion
        log_manager.log_scheduler_complete(
            workflow_summary={
                "total_scrapers": len(scrapers),
                "total_articles": total_articles,
                "success_rate": success_rate
            },
            next_run=timer.schedule_status.next if timer.schedule_status else None
        )
        
    except Exception as e:
        log_manager.log_error(
            error=e,
            context_data={
                "operation": "scheduler_execution",
                "schedule_name": "Daily Morning Scraping"
            }
        )
        
        log_manager.log_function_end(
            status="failed",
            result_summary={"error": str(e)}
        )
        raise
```

## Log Emojis untuk Visual Clarity

Logging menggunakan emoji untuk memudahkan identifikasi di log stream:

- 🚀 `FUNCTION_START` - Function dimulai
- ✅ `FUNCTION_END` - Function selesai sukses
- ❌ `ERROR` - Error terjadi
- 🔍 `SCRAPING_START` - Scraping dimulai
- 📄 `PAGE_FETCH` - Page fetch individual
- 📰 `ARTICLES_FOUND` - Articles ditemukan
- 📝 `ARTICLES_PARSED` - Articles di-parse
- 💾 `ARTICLES_SAVED` - Articles disimpan ke database
- 🔌 `DB_CONNECTION` - Database connection
- 💽 `DB_OPERATION` - Database operation
- 🔄 `DB_TRANSACTION` - Database transaction
- ⏰ `SCHEDULER_TRIGGER` - Scheduler triggered
- 🎭 `SCHEDULER_ORCHESTRATION` - Scheduler orchestration
- ⏳ `SCHEDULER_WAIT` - Scheduler waiting
- 📊 `SCHEDULER_AGGREGATION` - Scheduler aggregation
- ▶️ `OPERATION_START` - Operation dimulai
- ⏹️ `OPERATION_END` - Operation selesai

## Querying Logs di Application Insights

### Query untuk melihat semua executions

```kusto
traces
| where customDimensions.function_name == "cnbc_scraper_function"
| where message contains "FUNCTION_START" or message contains "FUNCTION_END"
| project timestamp, message, customDimensions.execution_id, customDimensions.correlation_id
| order by timestamp desc
```

### Query untuk melihat errors

```kusto
traces
| where customDimensions.function_name == "cnbc_scraper_function"
| where message contains "ERROR"
| project timestamp, message, customDimensions.execution_id, customDimensions.exception
| order by timestamp desc
```

### Query untuk performance metrics

```kusto
traces
| where customDimensions.function_name == "cnbc_scraper_function"
| where message contains "SCRAPING_END"
| extend articles_scraped = toint(customDimensions.data.articles_scraped)
| extend duration_ms = todouble(customDimensions.data.duration_ms)
| extend throughput = todouble(customDimensions.data.throughput_articles_per_second)
| project timestamp, articles_scraped, duration_ms, throughput
| order by timestamp desc
```

### Query untuk correlation tracking

```kusto
traces
| where customDimensions.correlation_id == "your-correlation-id"
| project timestamp, customDimensions.function_name, message
| order by timestamp asc
```

## Testing Logging

### Local Testing

```python
# test_logging.py
import asyncio
from azure_functions.shared.azure_logging import AzureLoggingManager

async def test_logging():
    log_manager = AzureLoggingManager(
        function_name="test_function"
    )
    
    log_manager.log_function_start(
        trigger_type="manual",
        parameters={"test": "value"}
    )
    
    log_manager.log_scraping_start(
        source="TestSource",
        keywords=["test"],
        date_range={"start": "2024-01-01", "end": "2024-01-31"}
    )
    
    log_manager.log_scraping_articles_found(
        count=10,
        parsing_success_rate=95.0
    )
    
    log_manager.log_function_end(
        status="success",
        result_summary={"articles": 10}
    )

if __name__ == "__main__":
    asyncio.run(test_logging())
```

### Azure Testing

1. Deploy function ke Azure
2. Trigger function via HTTP atau Timer
3. Buka Azure Portal → Function App → Log Stream
4. Atau buka Application Insights → Logs → Run queries

## Checklist untuk Setiap Scraper

- [ ] Import AzureLoggingManager
- [ ] Initialize log_manager di main()
- [ ] Log function_start dengan parameters
- [ ] Pass log_manager ke scraping function
- [ ] Log scraping_start
- [ ] Log operation_start
- [ ] Log articles_found
- [ ] Log database_operation
- [ ] Log articles_saved
- [ ] Log scraping_end
- [ ] Log operation_end
- [ ] Log function_end
- [ ] Handle errors dengan log_error
- [ ] Test di Azure Log Stream

## Scrapers yang Perlu Diupdate

1. ✅ CNBC Scraper - COMPLETED
2. ⏳ Kompas Scraper - PENDING
3. ⏳ Kontan Scraper - PENDING
4. ⏳ BPS Scraper - PENDING
5. ⏳ Bisnis Indonesia Scraper - PENDING
6. ⏳ CNBC Indonesia Scraper - PENDING
7. ⏳ Oilprice Scraper - PENDING
8. ⏳ The Guardian Scraper - PENDING
9. ⏳ Reuters Scraper - PENDING
10. ⏳ Tempo Scraper - PENDING
11. ⏳ CNN Scraper - PENDING

## Schedulers yang Perlu Diupdate

1. ⏳ Daily Morning Scheduler - PENDING
2. ⏳ Daily Afternoon Scheduler - PENDING
3. ⏳ Weekly Summary Scheduler - PENDING
4. ⏳ Monthly Aggregation Scheduler - PENDING

## Next Steps

1. Update semua scraper functions dengan pattern di atas
2. Update semua scheduler functions
3. Deploy ke Azure
4. Test logging di Azure Log Stream
5. Create Application Insights dashboard
6. Setup alerts untuk critical errors
