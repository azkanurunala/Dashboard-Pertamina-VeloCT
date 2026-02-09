"""
Selenium helper module for web scraping with anti-detection features.
Provides headless Chrome browser automation as fallback for sites that block aiohttp.
"""

import asyncio
import logging
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchElementException
)

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    ChromeDriverManager = None

logger = logging.getLogger(__name__)

# Common User-Agent strings for anti-detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class SeleniumHelper:
    """
    Helper class for Selenium-based web scraping with anti-detection features.
    """
    
    def __init__(
        self,
        headless: bool = True,
        page_load_timeout: int = 30,
        implicit_wait: int = 10,
        user_agent: Optional[str] = None
    ):
        """
        Initialize Selenium helper.
        
        Args:
            headless: Run Chrome in headless mode
            page_load_timeout: Timeout for page loads in seconds
            implicit_wait: Implicit wait time for element finding
            user_agent: Custom user agent (random if not provided)
        """
        self.headless = headless
        self.page_load_timeout = page_load_timeout
        self.implicit_wait = implicit_wait
        self.user_agent = user_agent or random.choice(USER_AGENTS)
        self._driver: Optional[webdriver.Chrome] = None
        self._executor = ThreadPoolExecutor(max_workers=3)
        
    def _get_chrome_options(self) -> Options:
        """Configure Chrome options with anti-detection settings."""
        options = Options()
        
        # Headless mode
        if self.headless:
            options.add_argument("--headless=new")
        
        # Anti-detection flags
        options.add_argument(f"--user-agent={self.user_agent}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        # Azure Functions Sandbox Stability
        options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems
        options.add_argument("--no-sandbox") # Bypass OS security model
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-notifications")
        options.add_argument("--dns-prefetch-disable")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--disable-ipv6") # Force IPv4
        options.add_argument("--no-zygote") # Improve stability in container
        # options.add_argument("--single-process") # Risky but saves memory, enable if crashes persist
        
        # Window size (important for screenshots and responsive sites)
        options.add_argument("--window-size=1920,1080")
        
        # Language
        options.add_argument("--lang=en-US")
        
        # Experimental options for stealth
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Disable images for faster loading (optional)
        prefs = {
            "profile.default_content_setting_values.images": 2,
            "profile.managed_default_content_settings.images": 2
        }
        # Uncomment below to disable images:
        # options.add_experimental_option("prefs", prefs)
        
        return options
    
    def _create_driver(self) -> webdriver.Chrome:
        """Create and configure Chrome WebDriver."""
        options = self._get_chrome_options()
        
        try:
            # Try using webdriver-manager
            if ChromeDriverManager:
                try:
                    logger.info("Attempting to install/update ChromeDriver using webdriver-manager...")
                    driver_path = ChromeDriverManager().install()
                    service = Service(driver_path)
                    driver = webdriver.Chrome(service=service, options=options)
                    logger.info("Successfully created Chrome driver with webdriver-manager")
                    return driver
                except Exception as wdm_error:
                    logger.warning(f"webdriver-manager failed: {wdm_error}. Falling back to system ChromeDriver.")
            
            # Fallback to system Chrome
            logger.info("Attempting to create Chrome driver using system default...")
            driver = webdriver.Chrome(options=options)
            return driver
            
        except Exception as e:
            logger.error(f"FATAL: Failed to create Chrome driver: {e}")
            raise
        
        # Configure timeouts
        driver.set_page_load_timeout(self.page_load_timeout)
        driver.implicitly_wait(self.implicit_wait)
        
        # Execute CDP commands to prevent detection
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """
        })
        
        return driver
    
    @contextmanager
    def get_driver(self):
        """Context manager for getting a Chrome driver instance."""
        driver = None
        try:
            driver = self._create_driver()
            yield driver
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    logger.warning(f"Error closing driver: {e}")
    
    def fetch_page_sync(self, url: str, wait_for_selector: Optional[str] = None) -> str:
        """
        Fetch page content synchronously using Selenium.
        
        Args:
            url: URL to fetch
            wait_for_selector: CSS selector to wait for before returning
            
        Returns:
            Page HTML content
        """
        with self.get_driver() as driver:
            logger.info(f"Selenium: Fetching {url}")
            driver.get(url)
            
            # Wait for specific element if requested
            if wait_for_selector:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector))
                    )
                except TimeoutException:
                    logger.warning(f"Timeout waiting for selector: {wait_for_selector}")
            
            # Small delay to let JavaScript render
            time.sleep(random.uniform(1, 2))
            
            return driver.page_source
    
    async def fetch_page(self, url: str, wait_for_selector: Optional[str] = None) -> str:
        """
        Fetch page content asynchronously using Selenium.
        
        Args:
            url: URL to fetch
            wait_for_selector: CSS selector to wait for before returning
            
        Returns:
            Page HTML content
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self.fetch_page_sync,
            url,
            wait_for_selector
        )
    
    def fetch_sitemap_sync(self, url: str) -> str:
        """
        Fetch sitemap XML content synchronously.
        
        Args:
            url: Sitemap URL
            
        Returns:
            Sitemap XML content
        """
        with self.get_driver() as driver:
            logger.info(f"Selenium: Fetching sitemap {url}")
            driver.get(url)
            
            # Wait a bit for page to load
            time.sleep(random.uniform(0.5, 1.5))
            
            # Get the page source - for XML it will be wrapped in HTML
            page_source = driver.page_source
            
            # Try to extract raw XML content from pre tag (browsers wrap XML in <pre>)
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(page_source, 'html.parser')
                pre_tag = soup.find('pre')
                if pre_tag:
                    return pre_tag.get_text()
            except Exception:
                pass
            
            return page_source
    
    async def fetch_sitemap(self, url: str) -> str:
        """
        Fetch sitemap XML content asynchronously.
        
        Args:
            url: Sitemap URL
            
        Returns:
            Sitemap XML content
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self.fetch_sitemap_sync,
            url
        )
    
    def close(self):
        """Close the thread pool executor."""
        self._executor.shutdown(wait=False)


# Global singleton instance
_selenium_helper: Optional[SeleniumHelper] = None


def get_selenium_helper(
    headless: bool = None,
    page_load_timeout: int = None
) -> SeleniumHelper:
    """
    Get or create a global SeleniumHelper instance.
    
    Args:
        headless: Override headless setting
        page_load_timeout: Override page load timeout
        
    Returns:
        SeleniumHelper instance
    """
    global _selenium_helper
    
    if _selenium_helper is None:
        # Read from environment or use defaults
        _headless = headless if headless is not None else os.getenv("SELENIUM_HEADLESS", "true").lower() == "true"
        _timeout = page_load_timeout if page_load_timeout is not None else int(os.getenv("SELENIUM_PAGE_LOAD_TIMEOUT", "30"))
        
        _selenium_helper = SeleniumHelper(
            headless=_headless,
            page_load_timeout=_timeout
        )
    
    return _selenium_helper


async def fetch_with_selenium(url: str, wait_for_selector: Optional[str] = None) -> str:
    """
    Convenience function to fetch a URL using Selenium.
    
    Args:
        url: URL to fetch
        wait_for_selector: Optional CSS selector to wait for
        
    Returns:
        Page HTML content
    """
    helper = get_selenium_helper()
    return await helper.fetch_page(url, wait_for_selector)


async def fetch_sitemap_with_selenium(url: str) -> str:
    """
    Convenience function to fetch a sitemap using Selenium.
    
    Args:
        url: Sitemap URL
        
    Returns:
        Sitemap XML content
    """
    helper = get_selenium_helper()
    return await helper.fetch_sitemap(url)
