#!/usr/bin/env python3
"""
Capture CNBC scraper error logs.

This script:
1. Starts capturing logs from Azure
2. Triggers the CNBC scraper function
3. Captures the full error message and stack trace
4. Saves logs to file for analysis
"""

import sys
import time
import json
import requests
import subprocess
import threading
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from diagnostics import AzureLogAccess, LogParser

# Configuration
FUNCTION_APP_URL = "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net"
FUNCTION_KEY = "QRn4YL31yW-bZBFHDlt8znrvRmlfbvD8owXwCBegfk7TAzFuLEZIFg=="
FUNCTION_NAME = "cnbc_scraper_function"

# Output directory
OUTPUT_DIR = Path("diagnostic_logs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Global variable to store logs
captured_logs = []
log_capture_active = False


def capture_logs_background(duration_seconds=60):
    """Capture logs in the background using Azure CLI."""
    global captured_logs, log_capture_active
    
    print(f"📝 Starting log capture for {duration_seconds} seconds...")
    log_capture_active = True
    
    try:
        log_access = AzureLogAccess()
        
        # Use tail_logs to capture real-time logs
        entries = log_access.tail_logs(timeout_seconds=duration_seconds)
        captured_logs.extend(entries)
        
        print(f"✅ Captured {len(entries)} log entries")
        
    except Exception as e:
        print(f"⚠️  Error capturing logs: {e}")
    finally:
        log_capture_active = False


def trigger_cnbc_scraper():
    """Trigger the CNBC scraper function."""
    url = f"{FUNCTION_APP_URL}/api/{FUNCTION_NAME}?code={FUNCTION_KEY}"
    
    payload = {
        "keywords": ["energy", "oil", "gas"],
        "start_date": "2026-01-27",
        "end_date": "2026-01-28",
        "save_to_db": True
    }
    
    print("\n" + "=" * 70)
    print("🚀 Triggering CNBC Scraper Function")
    print("=" * 70)
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        start_time = time.time()
        print("⏳ Sending request... (may take 30-120 seconds)")
        
        response = requests.post(url, json=payload, timeout=180)
        elapsed = time.time() - start_time
        
        print(f"\n📊 Response received after {elapsed:.1f}s")
        print(f"Status Code: {response.status_code}")
        print()
        
        # Save response
        response_file = OUTPUT_DIR / f"cnbc_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        response_data = {
            "status_code": response.status_code,
            "elapsed_seconds": elapsed,
            "headers": dict(response.headers),
            "body": response.text
        }
        
        try:
            response_data["json"] = response.json()
        except:
            pass
        
        with open(response_file, 'w') as f:
            json.dump(response_data, f, indent=2)
        
        print(f"💾 Response saved to: {response_file}")
        
        # Print response details
        if response.status_code == 200:
            print("✅ SUCCESS!")
            result = response.json()
            print(f"Articles Found: {result.get('results', {}).get('articles_found', 0)}")
            print(f"Articles Saved: {result.get('results', {}).get('articles_saved', 0)}")
        else:
            print("❌ FAILED!")
            print(f"Response Body: {response.text[:500]}")
        
        return response
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out (>180s)")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def query_application_insights():
    """Query Application Insights for recent errors."""
    print("\n" + "=" * 70)
    print("🔍 Querying Application Insights for Recent Errors")
    print("=" * 70)
    
    log_access = AzureLogAccess()
    
    # Get recent errors (last 10 minutes)
    print("Fetching errors from last 10 minutes...")
    error_entries = log_access.get_recent_errors(minutes=10)
    
    if error_entries:
        print(f"✅ Found {len(error_entries)} error entries")
        return error_entries
    else:
        print("⚠️  No errors found in Application Insights")
        return []


def query_exceptions():
    """Query Application Insights for exceptions."""
    print("\n" + "=" * 70)
    print("🔍 Querying Application Insights for Exceptions")
    print("=" * 70)
    
    log_access = AzureLogAccess()
    
    print("Fetching exceptions from last 10 minutes...")
    exceptions = log_access.get_exceptions(minutes=10)
    
    if exceptions:
        print(f"✅ Found {len(exceptions)} exceptions")
        return exceptions
    else:
        print("⚠️  No exceptions found in Application Insights")
        return []


def query_failed_requests():
    """Query Application Insights for failed requests."""
    print("\n" + "=" * 70)
    print("🔍 Querying Application Insights for Failed Requests")
    print("=" * 70)
    
    log_access = AzureLogAccess()
    
    print("Fetching failed requests from last 10 minutes...")
    failed_requests = log_access.get_failed_requests(minutes=10)
    
    if failed_requests:
        print(f"✅ Found {len(failed_requests)} failed requests")
        return failed_requests
    else:
        print("⚠️  No failed requests found in Application Insights")
        return []


def save_logs_to_file():
    """Save captured logs to file."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save raw log entries
    log_file = OUTPUT_DIR / f"cnbc_logs_{timestamp}.txt"
    
    with open(log_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("CNBC Scraper Error Logs\n")
        f.write(f"Captured at: {datetime.now().isoformat()}\n")
        f.write("=" * 70 + "\n\n")
        
        if captured_logs:
            f.write(f"Total log entries: {len(captured_logs)}\n\n")
            
            for i, entry in enumerate(captured_logs, 1):
                f.write(f"--- Entry {i} ---\n")
                f.write(f"Timestamp: {entry.timestamp}\n")
                f.write(f"Level: {entry.level}\n")
                f.write(f"Function: {entry.function_name or 'N/A'}\n")
                f.write(f"Message: {entry.message}\n")
                
                if entry.exception:
                    f.write(f"Exception:\n{entry.exception}\n")
                
                f.write("\n")
        else:
            f.write("No log entries captured from log stream.\n")
    
    print(f"\n💾 Logs saved to: {log_file}")
    return log_file


def save_appinsights_data(errors, exceptions, failed_requests):
    """Save Application Insights data to file."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    appinsights_file = OUTPUT_DIR / f"cnbc_appinsights_{timestamp}.json"
    
    data = {
        "captured_at": datetime.now().isoformat(),
        "errors": [
            {
                "timestamp": str(e.timestamp),
                "level": e.level,
                "function_name": e.function_name,
                "message": e.message,
                "exception": e.exception
            }
            for e in errors
        ],
        "exceptions": exceptions,
        "failed_requests": failed_requests
    }
    
    with open(appinsights_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"💾 Application Insights data saved to: {appinsights_file}")
    return appinsights_file


def main():
    """Main execution."""
    print("\n" + "=" * 70)
    print("🔧 CNBC Scraper Error Capture Tool")
    print("=" * 70)
    print()
    
    # Check Azure CLI access
    log_access = AzureLogAccess()
    if not log_access.check_azure_cli_installed():
        print("⚠️  Azure CLI not installed. Will skip real-time log capture.")
        print("   Will use Application Insights queries instead.")
        use_cli = False
    elif not log_access.check_logged_in():
        print("⚠️  Not logged in to Azure CLI. Will skip real-time log capture.")
        print("   Will use Application Insights queries instead.")
        use_cli = False
    else:
        print("✅ Azure CLI is ready")
        use_cli = True
    
    print()
    
    # Start log capture in background if CLI is available
    if use_cli:
        log_thread = threading.Thread(target=capture_logs_background, args=(60,))
        log_thread.start()
        
        # Give log capture a moment to start
        time.sleep(2)
    
    # Trigger the scraper
    response = trigger_cnbc_scraper()
    
    # Wait for log capture to complete
    if use_cli:
        print("\n⏳ Waiting for log capture to complete...")
        log_thread.join()
    
    # Query Application Insights for additional data
    time.sleep(5)  # Give Azure time to process logs
    
    errors = query_application_insights()
    exceptions = query_exceptions()
    failed_requests = query_failed_requests()
    
    # Save all captured data
    print("\n" + "=" * 70)
    print("💾 Saving Captured Data")
    print("=" * 70)
    
    if use_cli:
        log_file = save_logs_to_file()
    
    appinsights_file = save_appinsights_data(errors, exceptions, failed_requests)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Summary")
    print("=" * 70)
    
    if response:
        print(f"HTTP Status: {response.status_code}")
    else:
        print("HTTP Status: Timeout/Error")
    
    if use_cli:
        print(f"Log Entries Captured: {len(captured_logs)}")
    
    print(f"Errors from AppInsights: {len(errors)}")
    print(f"Exceptions from AppInsights: {len(exceptions)}")
    print(f"Failed Requests: {len(failed_requests)}")
    
    print("\n✅ Error capture complete!")
    print(f"\n📁 All files saved to: {OUTPUT_DIR.absolute()}")
    
    # Print next steps
    print("\n" + "=" * 70)
    print("📋 Next Steps")
    print("=" * 70)
    print("1. Review captured logs in the diagnostic_logs/ directory")
    print("2. Classify errors using: python diagnostic_tool.py classify-error <log_file>")
    print("3. Analyze specific errors and identify root causes")
    print("4. Apply fixes based on error classification")
    print()


if __name__ == '__main__':
    main()
