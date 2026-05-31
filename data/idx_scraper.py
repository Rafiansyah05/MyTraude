"""
IDX (Indonesia Stock Exchange) market data scraper.
Fetches and caches IDX market data including IHSG index and stock lists.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import aiohttp
from bs4 import BeautifulSoup
import json

from config.settings import settings
from utils.logger import get_logger
from utils.helpers import retry_async

logger = get_logger(__name__)


class IDXScraper:
    """Fetches data from Indonesia Stock Exchange."""
    
    # Cache management
    _cache: Dict = {}
    _cache_timestamp: Optional[datetime] = None
    
    @staticmethod
    def _normalize_ticker(ticker: str) -> str:
        """Normalize IDX ticker by stripping .JK suffix and uppercasing."""
        if not ticker or not isinstance(ticker, str):
            return ""
        return str(ticker).strip().upper().replace(".JK", "")

    @staticmethod
    def _is_cache_valid() -> bool:
        """Check if cache is still valid."""
        if IDXScraper._cache_timestamp is None:
            return False
        
        elapsed = (datetime.now() - IDXScraper._cache_timestamp).total_seconds()
        return elapsed < settings.IDX_UPDATE_INTERVAL
    
    @staticmethod
    async def get_idx_stocks() -> List[Dict]:
        """
        Get list of stocks from IDX.
        Returns list of stock data: {ticker, name, sector, etc}
        """
        # Check cache
        if IDXScraper._is_cache_valid() and "stocks" in IDXScraper._cache:
            logger.debug("Using cached IDX stocks list")
            return IDXScraper._cache["stocks"]
        
        logger.info("Fetching IDX stocks list...")

        # Try scraping the IDX summary page for a comprehensive list
        try:
            summary = await IDXScraper.fetch_summary()
            if summary:
                # Convert into expected dict form
                stocks = [
                    {"ticker": item.get("ticker"), "name": item.get("name"), "sector": item.get("sector", "Unknown")}
                    for item in summary
                ]
            else:
                stocks = await IDXScraper._get_major_stocks()
        except Exception:
            stocks = await IDXScraper._get_major_stocks()
        
        # Cache the result
        IDXScraper._cache["stocks"] = stocks
        IDXScraper._cache_timestamp = datetime.now()
        
        logger.info(f"Fetched {len(stocks)} stocks from IDX")
        return stocks
    
    @staticmethod
    async def _get_major_stocks() -> List[Dict]:
        """Get list of major Indonesian stocks (fallback list)."""
        # These are well-known Indonesian stocks that trade on IDX
        # In production, fetch from IDX API or database
        major_stocks = [
            {"ticker": "BBCA", "name": "Bank Central Asia", "sector": "Banking"},
            {"ticker": "BBRI", "name": "Bank Rakyat Indonesia", "sector": "Banking"},
            {"ticker": "BMRI", "name": "Bank Mandiri", "sector": "Banking"},
            {"ticker": "ASII", "name": "Astra International", "sector": "Automotive"},
            {"ticker": "UNTR", "name": "United Tractors", "sector": "Mining"},
            {"ticker": "PGAS", "name": "Perusahaan Gas Negara", "sector": "Energy"},
            {"ticker": "INDF", "name": "Indofood Sukses Makmur", "sector": "Food & Beverage"},
            {"ticker": "JSMR", "name": "Jalan Tol Mitra", "sector": "Infrastructure"},
            {"ticker": "TLKM", "name": "Telekomunikasi Indonesia", "sector": "Telecom"},
            {"ticker": "AKRA", "name": "Astra International", "sector": "Automotive"},
            {"ticker": "ADRO", "name": "Adaro Energy", "sector": "Mining"},
            {"ticker": "SMGR", "name": "Semen Indonesia", "sector": "Cement"},
            {"ticker": "TINS", "name": "Timah", "sector": "Mining"},
            {"ticker": "ITMG", "name": "Indo Tambangraya Megah", "sector": "Mining"},
            {"ticker": "ELSA", "name": "Elsa Prima", "sector": "Technology"},
            {"ticker": "MNCN", "name": "Media Nusantara Citra", "sector": "Media"},
            {"ticker": "PZZA", "name": "Pizza Hut Indonesia", "sector": "Food & Beverage"},
            {"ticker": "WIKA", "name": "Wijaya Karya", "sector": "Construction"},
        ]
        return major_stocks

    @staticmethod
    async def fetch_summary(timeout: int = 15) -> Optional[List[Dict[str, Any]]]:
        """Async fetch of IDX summary page. Parses HTML table into list of dicts."""
        url = "https://www.idx.co.id/id/data-pasar/ringkasan-perdagangan/ringkasan-saham/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Referer": "https://www.idx.co.id/",
        }

        def _parse_idx_api_payload(payload: Any) -> Optional[List[Dict[str, Any]]]:
            try:
                if isinstance(payload, str):
                    payload = json.loads(payload)
                if isinstance(payload, dict):
                    rows = payload.get("data") or payload.get("rows") or payload.get("results") or payload
                else:
                    rows = payload

                if not rows:
                    return None

                results: List[Dict[str, Any]] = []
                for row in rows:
                    if isinstance(row, dict):
                        code = row.get("code") or row.get("Code") or row.get("symbol")
                        name = row.get("name") or row.get("Name") or row.get("company")
                        last = row.get("last_price") or row.get("last") or row.get("close") or row.get("last_price")
                        change = row.get("change") or row.get("Change") or 0
                        pct = row.get("change_percent") or row.get("ChangePercent") or row.get("pct") or 0
                        volume = row.get("volume") or row.get("Volume") or 0
                        value = row.get("value") or row.get("Value") or 0
                    elif isinstance(row, (list, tuple)) and len(row) >= 3:
                        code = row[0]
                        name = row[1]
                        last = row[2]
                        change = row[3] if len(row) > 3 else 0
                        pct = row[4] if len(row) > 4 else 0
                        volume = row[5] if len(row) > 5 else 0
                        value = row[6] if len(row) > 6 else 0
                    else:
                        continue

                    if not code:
                        continue

                    try:
                        last_price = float(last) if last is not None else None
                    except Exception:
                        last_price = None

                    results.append({
                        "ticker": str(code).replace(".JK", "").strip(),
                        "name": name,
                        "last_price": last_price,
                        "change": float(change) if change is not None else None,
                        "change_percent": float(pct) if pct is not None else None,
                        "volume": float(volume) if volume is not None else None,
                        "value": float(value) if value is not None else None,
                        "frequency": None,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    })

                return results if results else None
            except Exception as e:
                logger.debug(f"Error parsing IDX API payload: {e}")
                return None

        def _parse_rows_from_html(text: str) -> Optional[List[Dict[str, Any]]]:
            try:
                soup = BeautifulSoup(text, "html.parser")

                # Attempt to find JSON data embedded in scripts
                scripts = soup.find_all("script")
                for s in scripts:
                    if s.string and ("var data" in s.string or "DataTable" in s.string or "json" in s.string):
                        try:
                            start = s.string.find("[")
                            end = s.string.rfind("]")
                            if start != -1 and end != -1:
                                payload = s.string[start:end + 1]
                                parsed = json.loads(payload)
                                results = _parse_idx_api_payload(parsed)
                                if results:
                                    return results
                        except Exception:
                            continue

                table = soup.find("table")
                if not table:
                    return None

                rows = table.find_all("tr")
                results: List[Dict[str, Any]] = []
                for r in rows[1:]:
                    cols = [c.get_text(strip=True) for c in r.find_all(["td", "th"])]
                    if not cols or len(cols) < 6:
                        continue

                    def _parse_num(s: str):
                        try:
                            return float(s.replace(",", "").replace("%", "").replace("—", "0"))
                        except Exception:
                            return 0.0

                    code = cols[0].replace('.JK', '').strip()
                    name = cols[1]
                    last = _parse_num(cols[2])
                    change = _parse_num(cols[3])
                    pct = _parse_num(cols[4])
                    vol = _parse_num(cols[5])
                    value = _parse_num(cols[6]) if len(cols) > 6 else 0.0

                    results.append({
                        'ticker': code,
                        'name': name,
                        'last_price': last,
                        'change': change,
                        'change_percent': pct,
                        'volume': vol,
                        'value': value,
                        'frequency': None,
                        'timestamp': datetime.utcnow().isoformat() + 'Z'
                    })

                return results if results else None
            except Exception as e:
                logger.debug(f"Error parsing IDX HTML: {e}")
                return None

        def _try_official_idx_api() -> Optional[List[Dict[str, Any]]]:
            candidate_urls = []
            if settings.IDX_API_URL:
                candidate_urls.append(settings.IDX_API_URL)

            candidate_urls.extend([
                "https://www.idx.co.id/umbraco/api/marketdata/GetStockSummary",
                "https://www.idx.co.id/umbraco/api/stock/GetStockSummary",
                "https://www.idx.co.id/umbraco/Api/MarketData/GetStockSummary",
                "https://www.idx.co.id/umbraco/Api/Stock/GetStockSummary",
            ])

            import requests as _requests
            headers_api = {
                'Accept': 'application/json',
                'User-Agent': headers['User-Agent'],
            }
            if settings.IDX_API_TOKEN:
                headers_api['Authorization'] = f"Bearer {settings.IDX_API_TOKEN}"

            for api_url in candidate_urls:
                if not api_url:
                    continue
                try:
                    resp_api = _requests.get(api_url, headers=headers_api, timeout=timeout)
                    if resp_api.status_code != 200:
                        continue
                    payload = resp_api.json()
                    results = _parse_idx_api_payload(payload)
                    if results:
                        logger.info(f"Fetched IDX data from API endpoint: {api_url}")
                        return results
                except Exception as e_api:
                    logger.debug(f"IDX API endpoint {api_url} failed: {e_api}")
            return None

        def _playwright_fetch() -> Optional[str]:
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox',
                            '--disable-setuid-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-blink-features=AutomationControlled',
                            '--disable-infobars',
                        ],
                    )
                    context = browser.new_context(
                        user_agent=headers['User-Agent'],
                        viewport={"width": 1280, "height": 900},
                        locale="en-US",
                        java_script_enabled=True,
                        bypass_csp=True,
                    )
                    page = context.new_page()
                    page.add_init_script(
                        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
                        "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});"
                        "Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});"
                    )
                    page.goto(url, wait_until='domcontentloaded', timeout=timeout * 1000)
                    page.wait_for_timeout(3000)
                    content = page.content()
                    context.close()
                    browser.close()
                    return content
            except Exception as e:
                logger.debug(f"Playwright fetch error: {e}")
                return None

        try:
            # Official IDX API first
            api_results = _try_official_idx_api()
            if api_results:
                return api_results

            # HTML fetch path
            text = None
            try:
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.get(url, timeout=timeout) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                        else:
                            logger.error(f"IDX fetch failed with status {resp.status}")
            except Exception as e:
                logger.debug(f"Async HTML request failed: {e}")

            if not text:
                try:
                    import requests
                    r = requests.get(url, headers=headers, timeout=timeout)
                    if r.status_code == 200:
                        text = r.text
                    else:
                        logger.error(f"IDX sync fetch failed with status {r.status_code}")
                except Exception as re:
                    logger.debug(f"IDX sync fallback exception: {re}")

            if text:
                results = _parse_rows_from_html(text)
                if results:
                    return results

            # Headless fallback after HTML parse failure
            playwright_text = _playwright_fetch()
            if playwright_text:
                results = _parse_rows_from_html(playwright_text)
                if results:
                    logger.info('Fetched IDX data via Playwright fallback')
                    return results

            logger.error('IDX summary could not be parsed from any source')
            return None
        except Exception as e:
            logger.exception(f"IDX fetch error: {e}")
            return None

    @staticmethod
    def get_stock_by_ticker(ticker: str) -> Optional[Dict[str, Any]]:
        """Synchronous helper used by fallback paths to get a single stock info."""
        try:
            # run blocking fetch_summary
            import asyncio as _asyncio
            loop = _asyncio.new_event_loop()
            _asyncio.set_event_loop(loop)
            data = loop.run_until_complete(IDXScraper.fetch_summary())
            loop.close()
            if not data:
                return None
            t = ticker.replace('.JK', '').upper()
            for item in data:
                if item.get('ticker') and item['ticker'].upper() == t:
                    return item
            return None
        except Exception as e:
            logger.debug(f"get_stock_by_ticker error: {e}")
            return None
    
    @staticmethod
    async def get_ihsg_index() -> Optional[Dict]:
        """
        Get current IHSG (Indonesia Composite Index) data.
        Returns: {value, change, change_percent}
        """
        try:
            # In production, fetch from IDX API or financial data provider
            # For now, return placeholder
            logger.debug("Fetching IHSG index data...")
            
            # This would be a real API call
            ihsg_data = {
                "value": 7000,  # Placeholder
                "change": 50,
                "change_percent": 0.72,
                "timestamp": datetime.now().isoformat()
            }
            return ihsg_data
        except Exception as e:
            logger.error(f"Failed to fetch IHSG index: {e}")
            return None
    
    @staticmethod
    async def get_sector_data() -> List[Dict]:
        """
        Get sector-wise market data.
        Returns list of sectors with their performance.
        """
        try:
            logger.debug("Fetching sector data...")
            
            sectors = [
                {"name": "Banking", "change_percent": 1.2},
                {"name": "Mining", "change_percent": 0.8},
                {"name": "Energy", "change_percent": -0.5},
                {"name": "Automotive", "change_percent": 1.5},
                {"name": "Infrastructure", "change_percent": 0.3},
            ]
            return sectors
        except Exception as e:
            logger.error(f"Failed to fetch sector data: {e}")
            return []
    
    @staticmethod
    def clear_cache():
        """Clear all cached data."""
        IDXScraper._cache.clear()
        IDXScraper._cache_timestamp = None
        logger.debug("IDX cache cleared")
