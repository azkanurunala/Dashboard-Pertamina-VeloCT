
import aiohttp
import asyncio
import sys

async def test_sipsn():
    url = "https://sipsn.kemenlh.go.id/sipsn/public/home/ajax_list"
    years = ["2026", "2025", "2024"]
    
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    }

    async with aiohttp.ClientSession() as session:
        for year in years:
            print(f"\n--- Testing Year {year} ---")
            payload = {
                'length': '-1',
                'jenis': 'sumber',
                'tahun': year
            }
            
            try:
                async with session.post(url, data=payload, headers=headers) as response:
                    print(f"Status: {response.status}")
                    print(f"Content-Type: {response.headers.get('Content-Type')}")
                    
                    try:
                        data = await response.json()
                        print("JSON Response received!")
                        print(f"Data count: {len(data.get('data', []))}")
                    except Exception as e:
                        print(f"Failed to decode JSON: {e}")
                        text = await response.text()
                        print(f"Response Text (first 500 chars): {text[:500]}")
            except Exception as e:
                print(f"Request failed: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_sipsn())
