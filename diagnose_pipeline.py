
import asyncio
import os
import sys
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'azure_functions')))

def log_diag(msg):
    print(msg)
    with open('diag_results_direct.txt', 'a') as f:
        f.write(str(msg) + '\n')

async def diagnose():
    if os.path.exists('diag_results_direct.txt'):
        os.remove('diag_results_direct.txt')
        
    log_diag("--- Diagnostic Script ---")
    
    # 1. Check Environment
    ai_type = os.getenv("AI_TYPE", "NOT SET")
    log_diag(f"Initial AI_TYPE from env: {ai_type}")
    
    # Force OpenAI
    os.environ["AI_TYPE"] = "OPENAI"
    log_diag(f"Forced AI_TYPE: {os.environ['AI_TYPE']}")
    
    # 2. Check OpenAI Configuration
    from shared.config import config_manager
    try:
        copilot_config = await config_manager.get_copilot_config()
        log_diag(f"Copilot Config Provider (should be OpenAI-compatible): {copilot_config.api_endpoint}")
        log_diag(f"Copilot Model Name: {copilot_config.model_name}")
    except Exception as e:
        log_diag(f"Error loading copilot config: {e}")

    # 3. Test Tempo Sitemap
    sitemap_url = "https://www.tempo.co/politik-sitemap.xml"
    log_diag(f"\nTesting Sitemap Fetch: {sitemap_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate' # Explicitly NO 'br'
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(sitemap_url) as response:
                log_diag(f"HTTP Status: {response.status}")
                log_diag(f"Content-Type: {response.headers.get('Content-Type')}")
                log_diag(f"Content-Encoding: {response.headers.get('Content-Encoding')}")
                
                content = await response.read()
                log_diag(f"Total Bytes: {len(content)}")
                
                # Check first 200 chars
                try:
                    text = content.decode('utf-8')
                    log_diag(f"First 200 chars: {text[:200]}")
                except:
                    log_diag("Could not decode content as UTF-8")
                
                # Try Parse
                try:
                    root = ET.fromstring(content)
                    log_diag(f"SUCCESS: ElementTree parsed XML. Tag: {root.tag}")
                except Exception as e:
                    log_diag(f"FAIL: ElementTree failed: {e}")
                    # Try BeautifulSoup
                    soup = BeautifulSoup(content, 'xml')
                    if soup.find('url'):
                        log_diag("SUCCESS: BeautifulSoup (xml) found <url> tags.")
                    else:
                        soup = BeautifulSoup(content, 'html.parser')
                        if soup.find('url'):
                            log_diag("SUCCESS: BeautifulSoup (html.parser) found <url> tags.")
                        else:
                            log_diag("FAIL: BeautifulSoup also failed to find <url> tags.")
                            if soup.title:
                                log_diag(f"Page Title: {soup.title.string}")

        except Exception as e:
            log_diag(f"Network error: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose())
