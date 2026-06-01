"""
IDX (Indonesia Stock Exchange) market data scraper.
Fetches and caches IDX market data including IHSG index and stock lists.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from playwright.async_api import async_playwright, Error as PlaywrightError

from config.settings import settings
from utils.logger import get_logger
from utils.helpers import retry_async

logger = get_logger(__name__)


class IDXScraper:
    """Fetches data from Indonesia Stock Exchange."""
    
    # Cache management
    _cache: Dict = {}
    _cache_timestamp: Optional[datetime] = None
    _snapshot_cache_path: Path = Path(__file__).resolve().parent / "idx_summary_cache.json"
    _snapshot_cache_days: int = 1
    
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

        # Use IDX JSON API as primary source
        try:
            idx_map = await IDXScraper.fetch_idx_summary()
            if idx_map:
                # Convert into expected dict form for compatibility
                stocks = [
                    {"ticker": k, "name": v.get("stock_name"), "sector": v.get("sector", "Unknown")}
                    for k, v in idx_map.items()
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
        """Fetch IDX market summary using official JSON endpoint.

        This function replaces HTML scraping. It returns a list of rows
        in a normalized dict form or None on failure.
        """
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'MyTraude/1.0 (+https://github.com)'
        }

        def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
            # Normalize common field names
            code = row.get('StockCode') or row.get('code') or row.get('symbol')
            name = row.get('StockName') or row.get('name') or row.get('company')
            prev = row.get('Previous') or row.get('PreviousClose') or row.get('previous') or None
            openp = row.get('OpenPrice') or row.get('Open') or row.get('open') or None
            high = row.get('High') or row.get('high') or None
            low = row.get('Low') or row.get('low') or None
            close = row.get('Close') or row.get('close') or None
            change = row.get('Change') or row.get('change') or None
            volume = row.get('Volume') or row.get('volume') or None
            value = row.get('Value') or row.get('value') or None
            freq = row.get('Frequency') or row.get('frequency') or None
            foreign_sell = row.get('ForeignSell') or row.get('foreignSell') or 0
            foreign_buy = row.get('ForeignBuy') or row.get('foreignBuy') or 0
            bid = row.get('Bid') or row.get('bid') or None
            offer = row.get('Offer') or row.get('offer') or None
            bid_volume = row.get('BidVolume') or row.get('bidVolume') or None
            offer_volume = row.get('OfferVolume') or row.get('offerVolume') or None

            foreign_buy_v = float(foreign_buy) if foreign_buy is not None else 0.0
            foreign_sell_v = float(foreign_sell) if foreign_sell is not None else 0.0

            return {
                'symbol': str(code).replace('.JK', '').upper() if code else None,
                'stock_name': name,
                'open': float(openp) if openp is not None else None,
                'high': float(high) if high is not None else None,
                'low': float(low) if low is not None else None,
                'close': float(close) if close is not None else None,
                'previous_close': float(prev) if prev is not None else None,
                'change': float(change) if change is not None else None,
                'volume': float(volume) if volume is not None else None,
                'value': float(value) if value is not None else None,
                'frequency': int(freq) if freq is not None else None,
                'foreign_buy': foreign_buy_v,
                'foreign_sell': foreign_sell_v,
                'foreign_net': foreign_buy_v - foreign_sell_v,
                'bid': float(bid) if bid is not None else None,
                'offer': float(offer) if offer is not None else None,
                'bid_volume': float(bid_volume) if bid_volume is not None else None,
                'offer_volume': float(offer_volume) if offer_volume is not None else None,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }

        api_url = settings.IDX_API_URL or 'https://www.idx.co.id/primary/TradingSummary/GetStockSummary?length=9999&start=0'

        async def _fetch_browser_summary(url: str, timeout_seconds: int) -> Optional[List[Dict[str, Any]]]:
            page_url = 'https://www.idx.co.id/id/data-pasar/ringkasan-perdagangan/ringkasan-saham/'
            user_agent = (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            )
            try:
                async with async_playwright() as playwright:
                    browser = await playwright.chromium.launch(
                        headless=True,
                        args=['--disable-blink-features=AutomationControlled']
                    )
                    context = await browser.new_context(
                        user_agent=user_agent,
                        locale='en-US',
                        viewport={'width': 1280, 'height': 800},
                        java_script_enabled=True,
                    )
                    page = await context.new_page()
                    await page.add_init_script(
                        """
                        Object.defineProperty(navigator, 'webdriver', {get: () => false});
                        Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                        """
                    )
                    await page.set_extra_http_headers({'Accept-Language': 'en-US,en;q=0.9'})
                    await page.goto(page_url, timeout=timeout_seconds * 1000, wait_until='networkidle')
                    await page.wait_for_timeout(2000)
                    result = await page.evaluate(f"""
                        async () => {{
                            const resp = await fetch('{url}', {{
                                method: 'GET',
                                headers: {{ 'Accept': 'application/json' }},
                                credentials: 'same-origin'
                            }});
                            if (!resp.ok) throw new Error(`IDX browser fetch failed: ${{resp.status}}`);
                            return await resp.json();
                        }}
                    """)
                    await context.close()
                    await browser.close()

                    if not isinstance(result, dict):
                        logger.warning('IDX browser fetch returned unexpected payload type')
                        return None

                    rows = result.get('data') or result.get('Data') or result.get('results') or []
                    normalized: List[Dict[str, Any]] = [_normalize_row(row) for row in rows]
                    logger.info(f'Fetched {len(normalized)} records from IDX via Playwright')
                    return normalized
            except PlaywrightError as e:
                logger.warning(f'IDX Playwright fetch failed: {e}')
            except Exception as e:
                logger.warning(f'IDX Playwright fetch error: {e}')
            return None

        def _save_cache(rows: List[Dict[str, Any]]) -> None:
            try:
                with IDXScraper._snapshot_cache_path.open('w', encoding='utf-8') as f:
                    json.dump({'fetched_at': datetime.utcnow().isoformat() + 'Z', 'data': rows}, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f'Failed to write IDX snapshot cache: {e}')

        def _load_cache() -> Optional[List[Dict[str, Any]]]:
            if not IDXScraper._snapshot_cache_path.exists():
                return None
            try:
                age_seconds = (datetime.now() - datetime.fromtimestamp(IDXScraper._snapshot_cache_path.stat().st_mtime)).total_seconds()
                if age_seconds > IDXScraper._snapshot_cache_days * 86400:
                    logger.info('IDX snapshot cache expired')
                    return None
                with IDXScraper._snapshot_cache_path.open('r', encoding='utf-8') as f:
                    payload = json.load(f)
                    rows = payload.get('data') or []
                    if not isinstance(rows, list):
                        return None
                    logger.info(f'Loaded {len(rows)} records from IDX cache')
                    return rows
            except Exception as e:
                logger.warning(f'Failed to load IDX snapshot cache: {e}')
                return None

        cached = _load_cache()
        if cached:
            logger.debug('Using file cache for IDX summary')
            return cached

        rows = await _fetch_browser_summary(api_url, timeout)
        if rows:
            _save_cache(rows)
            return rows

        if not rows and IDXScraper._snapshot_cache_path.exists():
            fallback = _load_cache()
            if fallback:
                logger.warning('Using stale IDX snapshot cache after browser fetch failure')
                return fallback

        return None

    @staticmethod
    async def fetch_idx_summary(timeout: int = 15) -> Optional[Dict[str, Dict[str, Any]]]:
        """Return IDX summary as a mapping symbol -> normalized row dict."""
        try:
            rows = await IDXScraper.fetch_summary(timeout=timeout)
            if not rows:
                return None
            mapping: Dict[str, Dict[str, Any]] = {}
            for r in rows:
                sym = r.get('symbol') or r.get('ticker')
                if not sym:
                    continue
                mapping[str(sym).upper()] = r
            logger.info(f"IDX summary mapping built with {len(mapping)} entries")
            return mapping
        except Exception as e:
            logger.error(f"fetch_idx_summary failed: {e}")
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
                symbol = item.get('symbol') or item.get('StockCode') or item.get('code')
                if symbol and str(symbol).replace('.JK', '').upper() == t:
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
