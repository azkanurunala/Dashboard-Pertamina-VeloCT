"""
Script untuk menjalankan dan test setiap scraper satu per satu.
Memverifikasi bahwa semua imports berhasil dan scraper bisa dijalankan.
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add parent directory to path
parent_dir = os.path.abspath(os.path.dirname(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


class ScraperTester:
    """Test individual scrapers"""
    
    def __init__(self):
        self.results = []
        self.start_date = datetime.now() - timedelta(days=7)
        self.end_date = datetime.now()
        self.keywords = ["energy", "oil", "gas"]
    
    async def test_cnbc_scraper(self) -> Dict[str, Any]:
        """Test CNBC scraper"""
        print("\n" + "="*70)
        print("Testing CNBC Scraper")
        print("="*70)
        
        try:
            from scrapers.cnbc_scraper import CNBCNewsScraper
            print("✓ Import successful")
            
            async with CNBCNewsScraper() as scraper:
                print(f"✓ Scraper initialized")
                articles = await scraper.scrape_news(
                    keywords=self.keywords,
                    start_date=self.start_date,
                    end_date=self.end_date
                )
                print(f"✓ Scraping completed: {len(articles)} articles found")
                
                return {
                    "scraper": "CNBC",
                    "status": "success",
                    "articles_count": len(articles),
                    "error": None
                }
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return {
                "scraper": "CNBC",
                "status": "failed",
                "articles_count": 0,
                "error": str(e)
            }
    
    async def test_oilprice_scraper(self) -> Dict[str, Any]:
        """Test OilPrice scraper"""
        print("\n" + "="*70)
        print("Testing OilPrice Scraper")
        print("="*70)
        
        try:
            from scrapers.oilprice_scraper import scrape_oilprice_news
            print("✓ Import successful")
            
            articles = await scrape_oilprice_news(
                keywords=self.keywords,
                start_date=self.start_date,
                end_date=self.end_date,
                max_articles=10
            )
            print(f"✓ Scraping completed: {len(articles)} articles found")
            
            return {
                "scraper": "OilPrice",
                "status": "success",
                "articles_count": len(articles),
                "error": None
            }
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return {
                "scraper": "OilPrice",
                "status": "failed",
                "articles_count": 0,
                "error": str(e)
            }
    
    async def test_reuters_scraper(self) -> Dict[str, Any]:
        """Test Reuters scraper"""
        print("\n" + "="*70)
        print("Testing Reuters Scraper")
        print("="*70)
        
        try:
            from scrapers.reuters_scraper import ReutersNewsScraper
            print("✓ Import successful")
            
            async with ReutersNewsScraper() as scraper:
                print(f"✓ Scraper initialized")
                articles = await scraper.scrape_news(
                    keywords=self.keywords,
                    start_date=self.start_date,
                    end_date=self.end_date
                )
                print(f"✓ Scraping completed: {len(articles)} articles found")
                
                return {
                    "scraper": "Reuters",
                    "status": "success",
                    "articles_count": len(articles),
                    "error": None
                }
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return {
                "scraper": "Reuters",
                "status": "failed",
                "articles_count": 0,
                "error": str(e)
            }
    
    async def test_cnn_scraper(self) -> Dict[str, Any]:
        """Test CNN scraper"""
        print("\n" + "="*70)
        print("Testing CNN Scraper")
        print("="*70)
        
        try:
            from scrapers.cnn_scraper import scrape_cnn_news
            print("✓ Import successful")
            
            articles = await scrape_cnn_news(
                keywords=self.keywords,
                start_date=self.start_date,
                end_date=self.end_date,
                max_articles=10
            )
            print(f"✓ Scraping completed: {len(articles)} articles found")
            
            return {
                "scraper": "CNN",
                "status": "success",
                "articles_count": len(articles),
                "error": None
            }
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return {
                "scraper": "CNN",
                "status": "failed",
                "articles_count": 0,
                "error": str(e)
            }
    
    async def test_theguardian_scraper(self) -> Dict[str, Any]:
        """Test The Guardian scraper"""
        print("\n" + "="*70)
        print("Testing The Guardian Scraper")
        print("="*70)
        
        try:
            from scrapers.theguardian_scraper import scrape_theguardian_news
            print("✓ Import successful")
            
            articles = await scrape_theguardian_news(
                keywords=self.keywords,
                start_date=self.start_date,
                end_date=self.end_date,
                max_articles=10
            )
            print(f"✓ Scraping completed: {len(articles)} articles found")
            
            return {
                "scraper": "The Guardian",
                "status": "success",
                "articles_count": len(articles),
                "error": None
            }
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return {
                "scraper": "The Guardian",
                "status": "failed",
                "articles_count": 0,
                "error": str(e)
            }
    
    async def test_kompas_scraper(self) -> Dict[str, Any]:
        """Test Kompas scraper"""
        print("\n" + "="*70)
        print("Testing Kompas Scraper")
        print("="*70)
        
        try:
            from scrapers.kompas_scraper import scrape_kompas_news
            print("✓ Import successful")
            
            articles = await scrape_kompas_news(
                keywords=["energi", "minyak"],  # Indonesian keywords
                start_date=self.start_date,
                end_date=self.end_date,
                max_articles=10
            )
            print(f"✓ Scraping completed: {len(articles)} articles found")
            
            return {
                "scraper": "Kompas",
                "status": "success",
                "articles_count": len(articles),
                "error": None
            }
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return {
                "scraper": "Kompas",
                "status": "failed",
                "articles_count": 0,
                "error": str(e)
            }
    
    async def test_tempo_scraper(self) -> Dict[str, Any]:
        """Test Tempo scraper"""
        print("\n" + "="*70)
        print("Testing Tempo Scraper")
        print("="*70)
        
        try:
            from scrapers.tempo_scraper import scrape_tempo_news
            print("✓ Import successful")
            
            articles = await scrape_tempo_news(
                keywords=["energi", "minyak"],  # Indonesian keywords
                start_date=self.start_date,
                end_date=self.end_date,
                max_articles=10
            )
            print(f"✓ Scraping completed: {len(articles)} articles found")
            
            return {
                "scraper": "Tempo",
                "status": "success",
                "articles_count": len(articles),
                "error": None
            }
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return {
                "scraper": "Tempo",
                "status": "failed",
                "articles_count": 0,
                "error": str(e)
            }
    
    async def test_kontan_scraper(self) -> Dict[str, Any]:
        """Test Kontan scraper"""
        print("\n" + "="*70)
        print("Testing Kontan Scraper")
        print("="*70)
        
        try:
            from scrapers.kontan_scraper import scrape_kontan_news
            print("✓ Import successful")
            
            articles = await scrape_kontan_news(
                keywords=["energi", "minyak"],  # Indonesian keywords
                start_date=self.start_date,
                end_date=self.end_date,
                max_articles=10
            )
            print(f"✓ Scraping completed: {len(articles)} articles found")
            
            return {
                "scraper": "Kontan",
                "status": "success",
                "articles_count": len(articles),
                "error": None
            }
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return {
                "scraper": "Kontan",
                "status": "failed",
                "articles_count": 0,
                "error": str(e)
            }
    
    async def test_cnbc_indonesia_scraper(self) -> Dict[str, Any]:
        """Test CNBC Indonesia scraper"""
        print("\n" + "="*70)
        print("Testing CNBC Indonesia Scraper")
        print("="*70)
        
        try:
            from scrapers.cnbc_indonesia_scraper import scrape_cnbc_indonesia_news
            print("✓ Import successful")
            
            articles = await scrape_cnbc_indonesia_news(
                keywords=["energi", "minyak"],  # Indonesian keywords
                start_date=self.start_date,
                end_date=self.end_date,
                max_articles=10
            )
            print(f"✓ Scraping completed: {len(articles)} articles found")
            
            return {
                "scraper": "CNBC Indonesia",
                "status": "success",
                "articles_count": len(articles),
                "error": None
            }
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return {
                "scraper": "CNBC Indonesia",
                "status": "failed",
                "articles_count": 0,
                "error": str(e)
            }
    
    async def test_bisnis_indonesia_scraper(self) -> Dict[str, Any]:
        """Test Bisnis Indonesia scraper"""
        print("\n" + "="*70)
        print("Testing Bisnis Indonesia Scraper")
        print("="*70)
        
        try:
            from scrapers.bisnis_indonesia_scraper import scrape_bisnis_indonesia_news
            print("✓ Import successful")
            
            articles = await scrape_bisnis_indonesia_news(
                keywords=["energi", "minyak"],  # Indonesian keywords
                start_date=self.start_date,
                end_date=self.end_date,
                max_articles=10
            )
            print(f"✓ Scraping completed: {len(articles)} articles found")
            
            return {
                "scraper": "Bisnis Indonesia",
                "status": "success",
                "articles_count": len(articles),
                "error": None
            }
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return {
                "scraper": "Bisnis Indonesia",
                "status": "failed",
                "articles_count": 0,
                "error": str(e)
            }
    
    async def test_bps_scraper(self) -> Dict[str, Any]:
        """Test BPS scraper"""
        print("\n" + "="*70)
        print("Testing BPS Scraper")
        print("="*70)
        
        try:
            from scrapers.bps_scraper import scrape_bps_data
            print("✓ Import successful")
            
            data = await scrape_bps_data(
                indicators=["inflation", "gdp"],
                start_date=self.start_date,
                end_date=self.end_date
            )
            print(f"✓ Scraping completed: {len(data)} data points found")
            
            return {
                "scraper": "BPS",
                "status": "success",
                "articles_count": len(data),
                "error": None
            }
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return {
                "scraper": "BPS",
                "status": "failed",
                "articles_count": 0,
                "error": str(e)
            }
    
    async def run_all_tests(self):
        """Run all scraper tests"""
        print("\n" + "="*70)
        print("SCRAPER TESTING SUITE")
        print("="*70)
        print(f"Date Range: {self.start_date.date()} to {self.end_date.date()}")
        print(f"Keywords: {', '.join(self.keywords)}")
        
        # List of all test methods
        tests = [
            self.test_cnbc_scraper,
            self.test_oilprice_scraper,
            self.test_reuters_scraper,
            self.test_cnn_scraper,
            self.test_theguardian_scraper,
            self.test_kompas_scraper,
            self.test_tempo_scraper,
            self.test_kontan_scraper,
            self.test_cnbc_indonesia_scraper,
            self.test_bisnis_indonesia_scraper,
            self.test_bps_scraper,
        ]
        
        # Run each test
        for test in tests:
            result = await test()
            self.results.append(result)
            await asyncio.sleep(1)  # Small delay between tests
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        success_count = sum(1 for r in self.results if r['status'] == 'success')
        failed_count = sum(1 for r in self.results if r['status'] == 'failed')
        total_articles = sum(r['articles_count'] for r in self.results)
        
        print(f"\nTotal Scrapers Tested: {len(self.results)}")
        print(f"✓ Successful: {success_count}")
        print(f"✗ Failed: {failed_count}")
        print(f"📰 Total Articles/Data: {total_articles}")
        
        print("\nDetailed Results:")
        print("-" * 70)
        
        for result in self.results:
            status_icon = "✓" if result['status'] == 'success' else "✗"
            print(f"{status_icon} {result['scraper']:<20} | "
                  f"Status: {result['status']:<10} | "
                  f"Articles: {result['articles_count']}")
            
            if result['error']:
                print(f"  Error: {result['error'][:100]}...")
        
        print("\n" + "="*70)
        
        if failed_count == 0:
            print("✓ ALL SCRAPERS WORKING CORRECTLY!")
        else:
            print(f"⚠ {failed_count} scraper(s) need attention")
        
        print("="*70)


async def main():
    """Main function"""
    tester = ScraperTester()
    await tester.run_all_tests()


if __name__ == '__main__':
    asyncio.run(main())
