"""
S&P Global Data Scraper for Azure Functions.
Fetches energy price data, forecasts, and petrochemical data from S&P Global API.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import aiohttp
import pandas as pd

# Add parent directory to Python path
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError
from shared.models import ScrapingConfig
from shared.logging_config import setup_logging

logger = setup_logging(__name__)


class SAndPDataScraper(BaseNewsScraper):
    """
    S&P Global Data Scraper.
    Fetches energy price data and forecasts from S&P Global API.
    """
    
    # Symbol mappings for BBM products
    BBM_SYMBOLS = {
        'PGAEY00': 'RON92',
        'PGAEZ00': 'RON95',
        'PGAMS00': 'RON97',
        'AMFSA00': 'FO05',
        'PJABF00': 'JetKero',
        'AAPPF00': 'GO50',
        'AACUE00': 'GO2500',
        'PCAAS00': 'Brent'
    }
    
    # Petrochemical products configuration
    PETROCHEMICAL_PRODUCTS = [
        {"name": "Paraxylene", "basis": "Spot CFR China"},
        {"name": "Propylene", "basis": "CFR SE Asia"},
        {"name": "Benzene", "basis": "Spot FOB Korea"}
    ]
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize S&P Global data scraper."""
        if config is None:
            config = ScrapingConfig(
                source_name="S&P Global",
                base_url="https://api.ci.spglobal.com",
                selectors={
                    "auth_url": "https://api.ci.spglobal.com/auth/api",
                    "history_url": "https://api.ci.spglobal.com/market-data/v3/value/history/symbol",
                    "current_url": "https://api.ci.spglobal.com/market-data/v3/value/current/symbol",
                    "forecast_long": "https://api.ci.spglobal.com/energy-price-forecast/v1/prices-long-term",
                    "forecast_short": "https://api.ci.spglobal.com/energy-price-forecast/v1/prices-short-term",
                    "petrochemical": "https://api.ci.spglobal.com/odata/petchem-analytics/v1.2/Prices"
                },
                rate_limit_delay=1.0,
                max_retries=3,
                timeout=60
            )
        
        super().__init__(config)
        self._access_token = None
        self._sp_username = os.getenv("S&P_USERNAME") or os.getenv("SP_USERNAME")
        self._sp_password = os.getenv("S&P_PASSWORD") or os.getenv("SP_PASSWORD")

    async def _login(self) -> Optional[str]:
        """
        Authenticate with S&P Global API.
        
        Returns:
            Access token or None if authentication fails
        """
        if not self._sp_username or not self._sp_password:
            self.logger.error("S&P_USERNAME or S&P_PASSWORD not found in environment variables")
            return None
        
        try:
            await self._ensure_session()
            
            auth_url = self.config.selectors.get("auth_url")
            payload = {
                "username": self._sp_username,
                "password": self._sp_password
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            
            async with self._session.post(auth_url, data=payload, headers=headers,
                                          timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                data = await response.json()
                
                access_token = data.get('access_token')
                if access_token:
                    self.logger.info("S&P Global login successful")
                    self._access_token = access_token
                    return access_token
                else:
                    self.logger.error("Access token not found in response")
                    return None
                    
        except Exception as e:
            self.logger.error(f"S&P Global login failed: {e}")
            return None

    async def _make_api_request(
        self, 
        url: str, 
        params: Dict[str, Any], 
        method: str = 'GET'
    ) -> Optional[Dict]:
        """
        Make an authenticated API request to S&P Global.
        
        Args:
            url: API endpoint URL
            params: Request parameters
            method: HTTP method (GET/POST)
            
        Returns:
            Response JSON or None
        """
        if not self._access_token:
            await self._login()
        
        if not self._access_token:
            raise ScrapingError("Failed to authenticate with S&P Global", source=self.source_name)
        
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            await self._ensure_session()
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            
            if method == 'GET':
                async with self._session.get(url, params=params, headers=headers, 
                                             timeout=timeout) as response:
                    response.raise_for_status()
                    return await response.json()
            else:
                async with self._session.post(url, json=params, headers=headers,
                                              timeout=timeout) as response:
                    response.raise_for_status()
                    return await response.json()
                    
        except aiohttp.ClientResponseError as e:
            if e.status == 401:
                # Token expired, try to re-authenticate
                self._access_token = None
                await self._login()
                if self._access_token:
                    return await self._make_api_request(url, params, method)
            raise ScrapingError(f"API request failed: {e}", source=self.source_name)
        except Exception as e:
            self.logger.error(f"API request error: {e}")
            raise ScrapingError(f"API request error: {e}", source=self.source_name)

    async def get_historical_data(
        self, 
        symbols: List[str], 
        start_date: str, 
        end_date: str,
        fields: Optional[List[str]] = None
    ) -> Optional[pd.DataFrame]:
        """
        Get historical market data for specified symbols.
        
        Args:
            symbols: List of price symbols
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            fields: Optional list of additional fields
            
        Returns:
            DataFrame with historical data or None
        """
        if fields is None:
            fields = ["UOM", "Currency", "description"]
        
        url = self.config.selectors.get("history_url")
        symbols_str = ",".join([f'"{s}"' for s in symbols])
        filter_query = f'symbol IN ({symbols_str}) AND assessDate>"{start_date}" AND assessDate<"{end_date}"'
        
        params = {
            "Field": ",".join(fields),
            "Filter": filter_query,
            "PageSize": 2000
        }
        
        self.logger.info(f"Fetching historical data from {start_date} to {end_date}")
        
        data = await self._make_api_request(url, params)
        if not data or 'results' not in data:
            return None
        
        flat_data = []
        for item in data['results']:
            symbol = item.get('symbol', '')
            for data_point in item.get('data', []):
                bate = data_point.get('bate', '')
                # Filter for close prices only
                if bate != 'c' and symbol not in ['PTAAF10', 'PTAAM10']:
                    continue
                
                assess_date = data_point.get('assessDate', '')
                if assess_date and 'T' in assess_date:
                    assess_date = assess_date.split('T')[0]
                
                flat_data.append({
                    'symbol': symbol,
                    'assessDate': assess_date,
                    'value': data_point.get('value', ''),
                    'modDate': data_point.get('modDate', '')
                })
        
        if not flat_data:
            return None
        
        df = pd.DataFrame(flat_data)
        if 'value' in df.columns:
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
        
        self.logger.info(f"Retrieved {len(df)} rows of historical data")
        return df

    async def get_forecast_short_term(
        self, 
        symbols: List[str], 
        year: int, 
        month: int,
        unit_name: str = "BBL"
    ) -> Optional[pd.DataFrame]:
        """
        Get short-term price forecasts.
        
        Args:
            symbols: List of price symbols
            year: Target year
            month: Target month
            unit_name: Unit of measurement (BBL, MT)
            
        Returns:
            DataFrame with forecast data or None
        """
        url = self.config.selectors.get("forecast_short")
        symbols_str = ",".join([f'"{s}"' for s in symbols])
        filter_query = f'priceSymbol IN ({symbols_str}) AND year={year} AND month={month} AND unitName="{unit_name}"'
        
        params = {
            "field": "year,month,price,priceSymbol",
            "filter": filter_query,
            "pageSize": 1000
        }
        
        self.logger.info(f"Fetching short-term forecast for {year}-{month:02d}")
        
        data = await self._make_api_request(url, params)
        if not data or 'results' not in data:
            return None
        
        flat_data = []
        for item in data['results']:
            flat_data.append({
                'year': item.get('year'),
                'month': item.get('month'),
                'price': item.get('price'),
                'priceSymbol': item.get('priceSymbol')
            })
        
        if not flat_data:
            return None
        
        df = pd.DataFrame(flat_data)
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
        
        return df

    async def get_forecast_long_term(
        self, 
        symbols: List[str], 
        start_year: int, 
        end_year: int,
        unit_name: str = "BBL"
    ) -> Optional[pd.DataFrame]:
        """
        Get long-term price forecasts.
        
        Args:
            symbols: List of price symbols
            start_year: Start year
            end_year: End year
            unit_name: Unit of measurement
            
        Returns:
            DataFrame with forecast data or None
        """
        url = self.config.selectors.get("forecast_long")
        symbols_str = ",".join([f'"{s}"' for s in symbols])
        filter_query = f'priceSymbol IN ({symbols_str}) AND year>={start_year} AND year<={end_year} AND unitName="{unit_name}"'
        
        params = {
            "field": "year,price,priceSymbol",
            "filter": filter_query,
            "pageSize": 1000
        }
        
        self.logger.info(f"Fetching long-term forecast for {start_year}-{end_year}")
        
        data = await self._make_api_request(url, params)
        if not data or 'results' not in data:
            return None
        
        flat_data = []
        for item in data['results']:
            flat_data.append({
                'year': item.get('year'),
                'price': item.get('price'),
                'priceSymbol': item.get('priceSymbol')
            })
        
        if not flat_data:
            return None
        
        df = pd.DataFrame(flat_data)
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
        
        return df

    async def get_petrochemical_prices(
        self, 
        product_name: str, 
        basis: str, 
        year: int, 
        month: int
    ) -> List[Dict]:
        """
        Get petrochemical prices.
        
        Args:
            product_name: Product name (Paraxylene, Propylene, Benzene)
            basis: Price basis
            year: Target year
            month: Target month
            
        Returns:
            List of price data
        """
        url = self.config.selectors.get("petrochemical")
        filter_str = f"Product eq '{product_name}' and DateYear eq {year} and DateMonth eq {month} and Basis eq '{basis}'"
        
        params = {
            "$select": "Product,Value,DateMonth,DateYear",
            "$filter": filter_str,
            "$top": 1000
        }
        
        self.logger.info(f"Fetching petrochemical data for {product_name} {year}-{month:02d}")
        
        data = await self._make_api_request(url, params)
        if not data:
            return []
        
        results = data.get('value', [])
        flat_data = []
        
        for item in results:
            flat_data.append({
                'Year': item.get('DateYear'),
                'Month': item.get('DateMonth'),
                f'Price_{product_name}': item.get('Value')
            })
        
        return flat_data

    def pivot_bbm_forecast(self, df: pd.DataFrame, is_short_term: bool = True) -> pd.DataFrame:
        """
        Pivot BBM forecast data and calculate crackspreads.
        
        Args:
            df: Raw forecast DataFrame
            is_short_term: Whether data is short-term (includes month) or long-term
            
        Returns:
            Pivoted DataFrame with crackspreads
        """
        df['suffix'] = df['priceSymbol'].map(self.BBM_SYMBOLS)
        
        index_cols = ['year', 'month'] if is_short_term else ['year']
        
        df_price = df.pivot_table(
            index=index_cols,
            columns='suffix',
            values='price',
            aggfunc='first'
        ).reset_index()
        
        # Rename columns
        price_cols = [col for col in df_price.columns if col not in index_cols]
        rename_map = {col: f'price_{col}' for col in price_cols}
        df_price = df_price.rename(columns=rename_map)
        
        # Calculate crackspreads if Brent is available
        if 'price_Brent' in df_price.columns:
            products = ['RON92', 'RON95', 'RON97', 'FO05', 'JetKero', 'GO50', 'GO2500']
            for product in products:
                price_col = f'price_{product}'
                if price_col in df_price.columns:
                    df_price[f'price_{product}_crackspread'] = (
                        df_price[price_col] - df_price['price_Brent']
                    )
        
        return df_price.sort_values(index_cols)

    async def _scrape_articles_from_source(
        self, 
        keywords: List[str], 
        start_date: datetime, 
        end_date: datetime, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Main entry point for S&P data fetching.
        This scraper returns data dictionaries instead of NewsArticle objects.
        
        Args:
            keywords: List indicating data types to fetch ('bbm', 'petrochemical', 'saf')
            start_date: Start date
            end_date: End date
            **kwargs: Additional parameters (data_type, symbols, etc.)
            
        Returns:
            List of data dictionaries with fetched results
        """
        data_type = kwargs.get('data_type', 'bbm_forecast_short')
        results = []
        
        try:
            # Login first
            if not await self._login():
                raise ScrapingError("Failed to login to S&P Global", source=self.source_name)
            
            if data_type == 'bbm_forecast_short':
                year = end_date.year
                month = end_date.month
                if month == 1:
                    month = 12
                    year -= 1
                else:
                    month -= 1
                
                symbols = list(self.BBM_SYMBOLS.keys())
                df = await self.get_forecast_short_term(symbols, year, month)
                
                if df is not None and not df.empty:
                    df_pivoted = self.pivot_bbm_forecast(df, is_short_term=True)
                    results.append({
                        'type': 'data_fossil_prediction',
                        'data': df_pivoted.to_dict('records'),
                        'period': f"{year}-{month:02d}"
                    })
            
            elif data_type == 'bbm_forecast_long':
                year = end_date.year
                symbols = list(self.BBM_SYMBOLS.keys())
                df = await self.get_forecast_long_term(symbols, year, year)
                
                if df is not None and not df.empty:
                    df_pivoted = self.pivot_bbm_forecast(df, is_short_term=False)
                    results.append({
                        'type': 'data_fossil_prediction',
                        'data': df_pivoted.to_dict('records'),
                        'period': str(year)
                    })
            
            elif data_type == 'petrochemical':
                year = end_date.year
                month = end_date.month
                if month == 1:
                    month = 12
                    year -= 1
                else:
                    month -= 1
                
                all_data = []
                for product in self.PETROCHEMICAL_PRODUCTS:
                    data = await self.get_petrochemical_prices(
                        product['name'], product['basis'], year, month
                    )
                    if data:
                        all_data.extend(data)
                
                if all_data:
                    results.append({
                        'type': 'data_petrochemical_prices',
                        'data': all_data,
                        'period': f"{year}-{month:02d}"
                    })
            
            elif data_type == 'historical':
                symbols = kwargs.get('symbols', list(self.BBM_SYMBOLS.keys()))
                df = await self.get_historical_data(
                    symbols,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                if df is not None and not df.empty:
                    results.append({
                        'type': 'data_oil_prices',
                        'data': df.to_dict('records'),
                        'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                    })
            
            self.logger.info(f"Successfully fetched {len(results)} S&P data results")
            return results
            
        except Exception as e:
            raise ScrapingError(f"Failed to fetch S&P data: {str(e)}", source=self.source_name)

    async def scrape_news(
        self, 
        keywords: List[str], 
        start_date: datetime, 
        end_date: datetime, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Override base scrape_news to bypass object validation.
        The S&P Data scraper returns structured data, not standard articles.
        """
        return await self._scrape_articles_from_source(
            keywords, start_date, end_date, **kwargs
        )


# Azure Function wrappers
async def scrape_sandp_bbm_forecast_short(year: int, month: int) -> List[Dict]:
    """Fetch S&P BBM short-term forecast data."""
    async with SAndPDataScraper() as scraper:
        return await scraper._scrape_articles_from_source(
            [], datetime.now(), datetime.now(),
            data_type='bbm_forecast_short'
        )


async def scrape_sandp_bbm_forecast_long(year: int) -> List[Dict]:
    """Fetch S&P BBM long-term forecast data."""
    async with SAndPDataScraper() as scraper:
        return await scraper._scrape_articles_from_source(
            [], datetime.now(), datetime.now(),
            data_type='bbm_forecast_long'
        )


async def scrape_sandp_petrochemical(year: int, month: int) -> List[Dict]:
    """Fetch S&P petrochemical data."""
    async with SAndPDataScraper() as scraper:
        return await scraper._scrape_articles_from_source(
            [], datetime.now(), datetime.now(),
            data_type='petrochemical'
        )


async def scrape_sandp_historical(
    symbols: List[str], 
    start_date: datetime, 
    end_date: datetime
) -> List[Dict]:
    """Fetch S&P historical market data."""
    async with SAndPDataScraper() as scraper:
        return await scraper._scrape_articles_from_source(
            [], start_date, end_date,
            data_type='historical',
            symbols=symbols
        )
