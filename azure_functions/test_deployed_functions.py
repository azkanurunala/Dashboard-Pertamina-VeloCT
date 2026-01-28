"""
Script untuk test Azure Functions yang sudah di-deploy via HTTP requests.
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import time

# ========================================
# KONFIGURASI - AZURE FUNCTION APP
# ========================================
FUNCTION_APP_NAME = "pei-dashboard-f5eebmdhe2a9dfgs"
AZURE_REGION = "canadacentral-01"
BASE_URL = f"https://{FUNCTION_APP_NAME}.{AZURE_REGION}.azurewebsites.net/api"

# FUNCTION KEY - SUDAH DIKONFIGURASI!
FUNCTION_KEY = "QRn4YL31yW-bZBFHDlt8znrvRmlfbvD8owXwCBegfk7TAzFuLEZIFg=="

# Jika URL berubah, edit line di atas atau uncomment dan edit line di bawah:
# BASE_URL = "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api"


class AzureFunctionTester:
    """Test deployed Azure Functions via HTTP"""
    
    def __init__(self, base_url: str, function_key: str = None):
        self.base_url = base_url
        self.function_key = function_key
        self.results = []
        
        # Default parameters
        self.start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        self.end_date = datetime.now().strftime('%Y-%m-%d')
        self.keywords_en = "energy,oil,gas"
        self.keywords_id = "energi,minyak,gas"
    
    def test_function(self, function_name: str, params: Dict[str, str]) -> Dict[str, Any]:
        """Test a single Azure Function"""
        url = f"{self.base_url}/{function_name}"
        
        # Add function key to params if provided
        if self.function_key and self.function_key != "YOUR_FUNCTION_KEY_HERE":
            params['code'] = self.function_key
        
        print(f"\n{'='*70}")
        print(f"Testing: {function_name}")
        print(f"{'='*70}")
        print(f"URL: {url}")
        print(f"Params: {params}")
        
        try:
            start_time = time.time()
            response = requests.get(url, params=params, timeout=300)  # 5 min timeout
            duration = time.time() - start_time
            
            print(f"Status Code: {response.status_code}")
            print(f"Duration: {duration:.2f}s")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✓ Success!")
                    
                    # Try to extract article count
                    articles_count = 0
                    if 'results' in data and 'articles_found' in data['results']:
                        articles_count = data['results']['articles_found']
                    elif 'articles_found' in data:
                        articles_count = data['articles_found']
                    
                    print(f"Articles Found: {articles_count}")
                    
                    return {
                        "function": function_name,
                        "status": "success",
                        "status_code": response.status_code,
                        "duration": duration,
                        "articles_count": articles_count,
                        "error": None
                    }
                except json.JSONDecodeError:
                    print(f"✓ Success (non-JSON response)")
                    return {
                        "function": function_name,
                        "status": "success",
                        "status_code": response.status_code,
                        "duration": duration,
                        "articles_count": 0,
                        "error": None
                    }
            else:
                print(f"✗ Failed with status {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return {
                    "function": function_name,
                    "status": "failed",
                    "status_code": response.status_code,
                    "duration": duration,
                    "articles_count": 0,
                    "error": f"HTTP {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            print(f"✗ Timeout after 5 minutes")
            return {
                "function": function_name,
                "status": "timeout",
                "status_code": 0,
                "duration": 300,
                "articles_count": 0,
                "error": "Timeout"
            }
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return {
                "function": function_name,
                "status": "error",
                "status_code": 0,
                "duration": 0,
                "articles_count": 0,
                "error": str(e)
            }
    
    def test_all_functions(self):
        """Test all deployed Azure Functions"""
        print("\n" + "="*70)
        print("AZURE FUNCTIONS TESTING SUITE")
        print("="*70)
        print(f"Base URL: {self.base_url}")
        print(f"Date Range: {self.start_date} to {self.end_date}")
        print(f"Keywords (EN): {self.keywords_en}")
        print(f"Keywords (ID): {self.keywords_id}")
        
        # Define all functions to test
        functions = [
            {
                "name": "cnbc_scraper_function",
                "params": {
                    "keywords": self.keywords_en,
                    "start_date": self.start_date,
                    "end_date": self.end_date,
                    "save_to_db": "false"
                }
            },
            {
                "name": "oilprice_scraper_function",
                "params": {
                    "keywords": self.keywords_en,
                    "start_date": self.start_date,
                    "end_date": self.end_date,
                    "max_articles": "10"
                }
            },
            {
                "name": "reuters_scraper_function",
                "params": {
                    "keywords": self.keywords_en,
                    "start_date": self.start_date,
                    "end_date": self.end_date,
                    "save_to_db": "false"
                }
            },
            {
                "name": "cnn_scraper_function",
                "params": {
                    "keywords": self.keywords_en,
                    "start_date": self.start_date,
                    "end_date": self.end_date,
                    "max_articles": "10"
                }
            },
            {
                "name": "theguardian_scraper_function",
                "params": {
                    "keywords": self.keywords_en,
                    "start_date": self.start_date,
                    "end_date": self.end_date,
                    "max_articles": "10"
                }
            },
            {
                "name": "kompas_scraper_function",
                "params": {
                    "keywords": self.keywords_id,
                    "start_date": self.start_date,
                    "end_date": self.end_date,
                    "max_articles": "10"
                }
            },
            {
                "name": "tempo_scraper_function",
                "params": {
                    "keywords": self.keywords_id,
                    "start_date": self.start_date,
                    "end_date": self.end_date,
                    "max_articles": "10"
                }
            },
            {
                "name": "kontan_scraper_function",
                "params": {
                    "keywords": self.keywords_id,
                    "start_date": self.start_date,
                    "end_date": self.end_date,
                    "max_articles": "10"
                }
            },
            {
                "name": "cnbc_indonesia_scraper_function",
                "params": {
                    "keywords": self.keywords_id,
                    "start_date": self.start_date,
                    "end_date": self.end_date,
                    "max_articles": "10"
                }
            },
            {
                "name": "bisnis_indonesia_scraper_function",
                "params": {
                    "keywords": self.keywords_id,
                    "start_date": self.start_date,
                    "end_date": self.end_date,
                    "max_articles": "10"
                }
            },
            {
                "name": "bps_scraper_function",
                "params": {
                    "indicators": "inflation,gdp",
                    "start_date": self.start_date,
                    "end_date": self.end_date
                }
            },
        ]
        
        # Test each function
        for func in functions:
            result = self.test_function(func["name"], func["params"])
            self.results.append(result)
            time.sleep(2)  # Small delay between tests
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        success_count = sum(1 for r in self.results if r['status'] == 'success')
        failed_count = sum(1 for r in self.results if r['status'] in ['failed', 'error', 'timeout'])
        total_articles = sum(r['articles_count'] for r in self.results)
        avg_duration = sum(r['duration'] for r in self.results) / len(self.results) if self.results else 0
        
        print(f"\nTotal Functions Tested: {len(self.results)}")
        print(f"✓ Successful: {success_count}")
        print(f"✗ Failed: {failed_count}")
        print(f"📰 Total Articles: {total_articles}")
        print(f"⏱ Average Duration: {avg_duration:.2f}s")
        
        print("\nDetailed Results:")
        print("-" * 70)
        print(f"{'Function':<35} {'Status':<10} {'Code':<6} {'Time':<8} {'Articles'}")
        print("-" * 70)
        
        for result in self.results:
            status_icon = "✓" if result['status'] == 'success' else "✗"
            print(f"{status_icon} {result['function']:<33} "
                  f"{result['status']:<10} "
                  f"{result['status_code']:<6} "
                  f"{result['duration']:.2f}s   "
                  f"{result['articles_count']}")
            
            if result['error']:
                print(f"  Error: {result['error']}")
        
        print("\n" + "="*70)
        
        if failed_count == 0:
            print("✓ ALL FUNCTIONS WORKING CORRECTLY!")
        else:
            print(f"⚠ {failed_count} function(s) need attention")
        
        print("="*70)


def main():
    """Main function"""
    print("\n" + "="*70)
    print("AZURE FUNCTIONS DEPLOYMENT TESTER")
    print("="*70)
    
    # Check if BASE_URL is configured
    if "your-function-app-name" in BASE_URL:
        print("\n⚠ WARNING: Please configure FUNCTION_APP_NAME first!")
        print(f"Current BASE_URL: {BASE_URL}")
        print("\nEdit line 13 in this file:")
        print('FUNCTION_APP_NAME = "your-actual-function-app-name"')
        print("\nOr set BASE_URL directly on line 17:")
        print('BASE_URL = "https://your-actual-function-app.azurewebsites.net/api"')
        
        # Ask user if they want to continue anyway
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Exiting...")
            return
    
    # Check if FUNCTION_KEY is configured
    if FUNCTION_KEY == "YOUR_FUNCTION_KEY_HERE":
        print("\n⚠ WARNING: Function Key not configured!")
        print("Functions memerlukan authentication key.")
        print("\nLihat GET_FUNCTION_KEY_GUIDE.md untuk cara mendapatkan key.")
        print("\nQuick steps:")
        print("1. Azure Portal → PeiDashboard Function App")
        print("2. App Keys → Host keys → default → Copy")
        print("3. Edit line 16 in this file:")
        print('FUNCTION_KEY = "your_actual_function_key_here"')
        
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Exiting...")
            return
    
    # Create tester and run tests
    tester = AzureFunctionTester(BASE_URL, FUNCTION_KEY)
    tester.test_all_functions()


if __name__ == '__main__':
    main()
