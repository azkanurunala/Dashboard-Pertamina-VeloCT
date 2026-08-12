import gzip
import io
import threading

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


# Constants

REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}
REQUEST_TIMEOUT = 15

# Chrome window size used for all Selenium sessions
CHROME_WINDOW_SIZE = "1920,1080"

# Selenium's own page-load deadline. Without this, driver.get() can hang past
# call_with_hard_timeout's join() -- that only stops the orchestrator from
# waiting, it can't kill the browser thread, which keeps driving the *shared*
# driver in the background. The next keyword then reuses that same driver
# while the old call is still mid-navigation, wedging the ChromeDriver session
# for every call after it. Bounding navigation here means Selenium raises
# TimeoutException (already handled by callers) well before that can happen.
PAGE_LOAD_TIMEOUT_SECONDS = 90

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
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT_SECONDS)
        return driver
    except Exception as exc:
        print(f"[Driver] Failed to initialise ChromeDriver: {exc}")
        print("[Driver] Ensure ChromeDriver is installed and matches your Chrome version.")
        raise


# Hard-Deadline Wrapper
#
# requests' own `timeout=` param doesn't cover DNS resolution -- getaddrinfo()
# is a blocking OS-level call that runs before any socket exists, so it can
# hang indefinitely regardless of the timeout passed to requests.get(). This
# is what silently ate ~4h40m of a 6h GitHub Actions job on 2026-08-11 (a
# single Bloomberg Technoz search request that never returned or raised).
#
# Runs func in a daemon thread with a hard wall-clock join deadline. Daemon
# threads never block process exit (unlike ThreadPoolExecutor's default
# worker threads, which are joined at interpreter shutdown) -- if func never
# returns, the thread is simply abandoned when the process ends.

def call_with_hard_timeout(func, *args, timeout: float = 120, **kwargs):
    """
    Call func(*args, **kwargs) with a hard wall-clock deadline.

    Raises TimeoutError if func hasn't returned within `timeout` seconds --
    including hangs that a request's own `timeout=` parameter can't catch
    (e.g. a stuck DNS lookup). The call may keep running in the background
    past the deadline; it is abandoned, not killed (Python can't force-stop
    a thread), but a daemon thread never prevents the process from exiting.
    """
    result: dict = {}

    def _run():
        try:
            result["value"] = func(*args, **kwargs)
        except Exception as exc:
            result["error"] = exc

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        name = getattr(func, "__name__", repr(func))
        raise TimeoutError(f"{name} did not return within {timeout}s (hard deadline)")

    if "error" in result:
        raise result["error"]

    return result.get("value")


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