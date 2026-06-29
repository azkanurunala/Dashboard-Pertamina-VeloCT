import gzip
import io

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


# Constants

REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}
REQUEST_TIMEOUT = 15

# Chrome window size used for all Selenium sessions
CHROME_WINDOW_SIZE = "1920,1080"

# User-agent string passed to Chrome to mimic a real browser
CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# Selenium Driver Setup

def setup_driver(headless: bool = True) -> webdriver.Chrome:
    """
    Create and return a configured Chrome WebDriver instance.

    Applies standard anti-detection flags and disables automation-related
    Chrome features. Raises if ChromeDriver is not installed or incompatible.
    """
    chrome_options = Options()

    if headless:
        chrome_options.add_argument("--headless")

    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"--window-size={CHROME_WINDOW_SIZE}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(f"user-agent={CHROME_USER_AGENT}")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as exc:
        print(f"[Driver] Failed to initialise ChromeDriver: {exc}")
        print("[Driver] Ensure ChromeDriver is installed and matches your Chrome version.")
        raise


# XML Fetching

def fetch_xml(url: str) -> bytes:
    """
    Fetch XML content from a URL, transparently decompressing gzip if needed.

    Returns raw bytes of the (decompressed) XML, or raises on HTTP errors.
    """
    headers = REQUEST_HEADERS
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    content = response.content

    # Decompress if the URL ends with .gz or the magic bytes indicate gzip
    if url.endswith(".gz") or content[:2] == b"\x1f\x8b":
        with gzip.GzipFile(fileobj=io.BytesIO(content)) as f:
            content = f.read()

    return content