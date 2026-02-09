import asyncio
import aiohttp
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

async def test_cnbc():
    url = "https://www.cnbc.com/sitemap_news.xml"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    }
    
    print(f"Testing fetch of {url}")
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=30) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    content = await response.read()
                    print(f"Success! Fetched {len(content)} bytes")
                    print("First 200 chars:")
                    print(content[:200].decode('utf-8', errors='ignore'))
                else:
                    text = await response.text()
                    print(f"Failed! Content: {text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_cnbc())
