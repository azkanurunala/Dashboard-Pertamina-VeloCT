from selenium.webdriver.chrome.options import Options
from selenium import webdriver
import requests
import gzip
import io

def setup_driver(headless=True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print("Pastikan ChromeDriver sudah terinstall dan sesuai dengan versi Chrome Anda")
        raise

def fetch_xml(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    content = r.content
    if url.endswith('.gz') or content[:2] == b'\x1f\x8b':
        with gzip.GzipFile(fileobj=io.BytesIO(content)) as f:
            content = f.read()
    return content
