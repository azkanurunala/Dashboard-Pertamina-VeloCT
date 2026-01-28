"""
Test all scrapers locally to verify they work before deploying to Azure.
"""
import asyncio
import sys
from datetime import datetime, timedelta

# Test each scraper individually
async def test_cnbc_scraper():
    """Test CNBC scraper"""
    print("\n" + "="*70)
    print("Testing CNBC Scraper")
    print("="*70)
    try:
        from scrapers.cnbc_scraper import CNBCNewsScraper
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        async with CNBCNewsScraper() as scraper:
            articles = await scraper.scrape_news(
                keywords=['oil'],
                start_date=start_date,
                end_date=end_date
            )
            print(f"✓ CNBC: Found {len(articles)} articles")
            if articles:
                print(f"  Sample: {articles[0].title[:60]}...")
            return True
    except Exception as e:
        print(f"✗ CNBC FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cnn_scraper():
    """Test CNN scraper"""
    print("\n" + "="*70)
    print("Testing CNN Scraper")
    print("="*70)
    try:
        from scrapers.cnn_scraper import CNNNewsScraper
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        async with CNNNewsScraper() as scraper:
            articles = await scraper.scrape_news(
                keywords=['oil'],
                start_date=start_date,
                end_date=end_date
            )
            print(f"✓ CNN: Found {len(articles)} articles")
            if articles:
                print(f"  Sample: {articles[0].title[:60]}...")
            return True
    except Exception as e:
        print(f"✗ CNN FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_reuters_scraper():
    """Test Reuters scraper"""
    print("\n" + "="*70)
    print("Testing Reuters Scraper")
    print("="*70)
    try:
        from scrapers.reuters_scraper import ReutersNewsScraper
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        async with ReutersNewsScraper() as scraper:
            articles = await scraper.scrape_news(
                keywords=['oil'],
                start_date=start_date,
                end_date=end_date
            )
            print(f"✓ Reuters: Found {len(articles)} articles")
            if articles:
                print(f"  Sample: {articles[0].title[:60]}...")
            return True
    except Exception as e:
        print(f"✗ Reuters FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_theguardian_scraper():
    """Test The Guardian scraper"""
    print("\n" + "="*70)
    print("Testing The Guardian Scraper")
    print("="*70)
    try:
        from scrapers.theguardian_scraper import scrape_theguardian_news
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        articles = await scrape_theguardian_news(
            keywords=['oil'],
            start_date=start_date,
            end_date=end_date,
            max_articles=20
        )
        print(f"✓ The Guardian: Found {len(articles)} articles")
        if articles:
            print(f"  Sample: {articles[0].title[:60]}...")
        return True
    except Exception as e:
        print(f"✗ The Guardian FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_oilprice_scraper():
    """Test OilPrice scraper"""
    print("\n" + "="*70)
    print("Testing OilPrice Scraper")
    print("="*70)
    try:
        from scrapers.oilprice_scraper import scrape_oilprice_news
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        articles = await scrape_oilprice_news(
            keywords=['oil'],
            start_date=start_date,
            end_date=end_date,
            max_articles=20
        )
        print(f"✓ OilPrice: Found {len(articles)} articles")
        if articles:
            print(f"  Sample: {articles[0].title[:60]}...")
        return True
    except Exception as e:
        print(f"✗ OilPrice FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_bisnis_indonesia_scraper():
    """Test Bisnis Indonesia scraper"""
    print("\n" + "="*70)
    print("Testing Bisnis Indonesia Scraper")
    print("="*70)
    try:
        from scrapers.bisnis_indonesia_scraper import scrape_bisnis_indonesia_news
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        articles = await scrape_bisnis_indonesia_news(
            keywords=['energi'],
            start_date=start_date,
            end_date=end_date,
            max_articles=30
        )
        print(f"✓ Bisnis Indonesia: Found {len(articles)} articles")
        if articles:
            print(f"  Sample: {articles[0].title[:60]}...")
        return True
    except Exception as e:
        print(f"✗ Bisnis Indonesia FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cnbc_indonesia_scraper():
    """Test CNBC Indonesia scraper"""
    print("\n" + "="*70)
    print("Testing CNBC Indonesia Scraper")
    print("="*70)
    try:
        from scrapers.cnbc_indonesia_scraper import scrape_cnbc_indonesia_news
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        articles = await scrape_cnbc_indonesia_news(
            keywords=['energi'],
            start_date=start_date,
            end_date=end_date,
            max_articles=30
        )
        print(f"✓ CNBC Indonesia: Found {len(articles)} articles")
        if articles:
            print(f"  Sample: {articles[0].title[:60]}...")
        return True
    except Exception as e:
        print(f"✗ CNBC Indonesia FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_kompas_scraper():
    """Test Kompas scraper"""
    print("\n" + "="*70)
    print("Testing Kompas Scraper")
    print("="*70)
    try:
        from scrapers.kompas_scraper import scrape_kompas_news
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        articles = await scrape_kompas_news(
            keywords=['energi'],
            start_date=start_date,
            end_date=end_date,
            max_articles=30
        )
        print(f"✓ Kompas: Found {len(articles)} articles")
        if articles:
            print(f"  Sample: {articles[0].title[:60]}...")
        return True
    except Exception as e:
        print(f"✗ Kompas FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_kontan_scraper():
    """Test Kontan scraper"""
    print("\n" + "="*70)
    print("Testing Kontan Scraper")
    print("="*70)
    try:
        from scrapers.kontan_scraper import scrape_kontan_news
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        articles = await scrape_kontan_news(
            keywords=['energi'],
            start_date=start_date,
            end_date=end_date,
            max_articles=30
        )
        print(f"✓ Kontan: Found {len(articles)} articles")
        if articles:
            print(f"  Sample: {articles[0].title[:60]}...")
        return True
    except Exception as e:
        print(f"✗ Kontan FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tempo_scraper():
    """Test Tempo scraper"""
    print("\n" + "="*70)
    print("Testing Tempo Scraper")
    print("="*70)
    try:
        from scrapers.tempo_scraper import scrape_tempo_news
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        articles = await scrape_tempo_news(
            keywords=['energi'],
            start_date=start_date,
            end_date=end_date,
            max_articles=25
        )
        print(f"✓ Tempo: Found {len(articles)} articles")
        if articles:
            print(f"  Sample: {articles[0].title[:60]}...")
        return True
    except Exception as e:
        print(f"✗ Tempo FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all scraper tests"""
    print("\n" + "="*70)
    print("LOCAL SCRAPER TESTING")
    print("="*70)
    print("Testing all 10 scrapers locally before Azure deployment...")
    
    results = {}
    
    # Test international scrapers
    print("\n### INTERNATIONAL SCRAPERS ###")
    results['CNBC'] = await test_cnbc_scraper()
    results['CNN'] = await test_cnn_scraper()
    results['Reuters'] = await test_reuters_scraper()
    results['The Guardian'] = await test_theguardian_scraper()
    results['OilPrice'] = await test_oilprice_scraper()
    
    # Test Indonesian scrapers
    print("\n### INDONESIAN SCRAPERS ###")
    results['Bisnis Indonesia'] = await test_bisnis_indonesia_scraper()
    results['CNBC Indonesia'] = await test_cnbc_indonesia_scraper()
    results['Kompas'] = await test_kompas_scraper()
    results['Kontan'] = await test_kontan_scraper()
    results['Tempo'] = await test_tempo_scraper()
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    
    for scraper, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {scraper}")
    
    print("\n" + "="*70)
    print(f"Total: {len(results)} scrapers")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("="*70)
    
    if failed > 0:
        print("\n⚠️  Some scrapers failed. Fix issues before deploying to Azure.")
        sys.exit(1)
    else:
        print("\n✓ All scrapers passed! Ready to deploy to Azure.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
