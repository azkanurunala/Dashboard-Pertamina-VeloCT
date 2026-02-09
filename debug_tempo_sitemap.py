
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime

async def debug_sitemap():
    url = "https://www.tempo.co/ekonomi-sitemap.xml"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept-Encoding': 'gzip, deflate'
    }
    
    print(f"Fetching {url}...")
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as response:
            content = await response.read()
            print(f"Content length: {len(content)}")
            
            # Try ET
            try:
                root = ET.fromstring(content)
                print("ET Parse Success")
            except Exception as e:
                print(f"ET Parse Failed: {e}")
                
                # Try BS
                soup = BeautifulSoup(content, 'xml')
                url_tags = soup.find_all('url')
                print(f"BS find_all('url') found: {len(url_tags)} tags")
                
                if len(url_tags) > 0:
                    sample_tag = url_tags[0]
                    print(f"Sample Tag: {sample_tag}")
                    loc = sample_tag.find('loc')
                    print(f"Loc child: {loc}")
                    if loc:
                        print(f"Loc text: {loc.text}")

if __name__ == "__main__":
    asyncio.run(debug_sitemap())
