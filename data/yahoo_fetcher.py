"""
Yahoo Finance data fetcher for Indonesian stocks (.JK).
Fetches historical price data and calculates technical indicators.
"""

import asyncio
from typing import Optional, Dict, List, Any
import contextlib
import io
import yfinance as yf
import warnings
import re
from data.idx_scraper import IDXScraper
import pandas as pd

from config.settings import settings
from utils.logger import get_logger
from utils.helpers import retry_async, normalize_ticker

logger = get_logger(__name__)


class YahooFetcher:
    """Fetches stock data from Yahoo Finance."""
    
    @staticmethod
    async def fetch_stock_data(
        ticker: str,
        period: str = "3mo",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical price data for a stock.
        
        Args:
            ticker: Stock ticker (e.g., 'BBCA.JK' for BBCA)
            period: Data period ('1d', '5d', '1mo', '3mo', '6mo', '1y')
            interval: Candle interval ('1m', '5m', '15m', '30m', '60m', '1d')
        
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        async def _fetch():
            try:
                # Add .JK suffix if not present (Yahoo Finance format for IDX stocks)
                full_ticker = ticker if ticker.endswith(".JK") else f"{ticker}.JK"
                
                logger.debug(f"Fetching data for {full_ticker}...")
                
                # Run in executor to avoid blocking async loop
                loop = asyncio.get_event_loop()

                # Explicitly set auto_adjust to silence FutureWarning and ensure consistent columns
                def _download():
                    # suppress yfinance messages and internal warnings here
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        with contextlib.redirect_stderr(io.StringIO()):
                            return yf.download(
                                full_ticker,
                                period=period,
                                interval=interval,
                                progress=False,
                                timeout=settings.DATA_TIMEOUT_SECONDS,
                                auto_adjust=False,
                            )

                data = await loop.run_in_executor(None, _download)
                
                if data is None or data.empty:
                    logger.warning(f"No data found for {full_ticker}")
                    return None
                
                # Flatten MultiIndex columns if present (from newer yfinance versions)
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.droplevel(1)
                
                logger.debug(f"Fetched {len(data)} candles for {full_ticker}")
                return data
                
            except Exception as e:
                # If Yahoo returns crumb/unauthorized issues, try alternate fetch via Ticker.history
                logger.warning(f"Primary Yahoo download failed for {full_ticker}: {e}")
                try:
                    loop = asyncio.get_event_loop()
                    def _history():
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            return yf.Ticker(full_ticker).history(period=period, interval=interval)
                    data = await loop.run_in_executor(None, _history)
                    if data is None or (hasattr(data, 'empty') and data.empty):
                        # Last resort: try IDX scraper for latest single-row snapshot
                        logger.debug(f"Yahoo history empty, trying IDX scraper for {ticker}")
                        try:
                            idx_info = await asyncio.get_event_loop().run_in_executor(None, IDXScraper.get_stock_by_ticker, ticker)
                            if idx_info:
                                # Build minimal DataFrame from IDX data
                                from pandas import DataFrame
                                last = idx_info.get('last_price') or idx_info.get('last_price')
                                change = idx_info.get('change') or 0.0
                                open_price = float(last) - float(change)
                                df = DataFrame({
                                    'Open': [open_price],
                                    'High': [max(open_price, float(last))],
                                    'Low': [min(open_price, float(last))],
                                    'Close': [float(last)],
                                    'Volume': [idx_info.get('volume') or 0]
                                })
                                df.index = pd.to_datetime([pd.Timestamp(idx_info.get('timestamp'))])
                                logger.info(f"Built DataFrame for {ticker} from IDX data")
                                return df
                        except Exception as ie:
                            logger.debug(f"IDX fallback failed for {ticker}: {ie}")
                    else:
                        if isinstance(data.columns, pd.MultiIndex):
                            data.columns = data.columns.droplevel(1)
                        logger.debug(f"Fetched via Ticker.history {len(data)} candles for {full_ticker}")
                        return data
                except Exception as e2:
                    logger.error(f"Fallback yahoo.history failed for {ticker}: {e2}")
                return None
        
        # Retry with backoff
        result = await retry_async(
            _fetch,
            max_attempts=settings.RETRY_ATTEMPTS,
            backoff_seconds=settings.RETRY_BACKOFF_SECONDS,
            timeout_seconds=settings.DATA_TIMEOUT_SECONDS
        )
        return result
    
    @staticmethod
    async def fetch_multiple_stocks(
        tickers: List[str],
        period: str = "3mo"
    ) -> Dict[str, Optional[pd.DataFrame]]:
        """
        Fetch data for multiple stocks concurrently.
        
        Args:
            tickers: List of stock tickers
            period: Data period
        
        Returns:
            Dict mapping ticker -> DataFrame
        """
        logger.info(f"Fetching data for {len(tickers)} stocks...")
        
        # Create tasks for concurrent fetching
        tasks = [
            YahooFetcher.fetch_stock_data(ticker, period=period)
            for ticker in tickers
        ]
        
        # Run concurrently with semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(5)
        
        async def bounded_fetch(ticker, task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(
            *[bounded_fetch(ticker, task) for ticker, task in zip(tickers, tasks)],
            return_exceptions=True
        )
        
        # Map results
        data_dict = {}
        for ticker, result in zip(tickers, results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching {ticker}: {result}")
                data_dict[ticker] = None
            else:
                data_dict[ticker] = result
        
        logger.info(f"Completed fetching data for {len(tickers)} stocks")
        return data_dict
    
    @staticmethod
    def _parse_yahoo_price_from_html(html: str) -> Optional[float]:
        try:
            patterns = [
                r'"regularMarketPrice"\s*:\s*\{"raw"\s*:\s*([0-9]+(?:\.[0-9]+)?)',
                r'"currentPrice"\s*:\s*\{"raw"\s*:\s*([0-9]+(?:\.[0-9]+)?)'
            ]
            for pattern in patterns:
                match = re.search(pattern, html)
                if match:
                    return float(match.group(1))
        except Exception as e:
            logger.debug(f"Error parsing Yahoo HTML price: {e}")
        return None

    @staticmethod
    def _get_current_price_from_yahoo_html(full_ticker: str) -> Optional[float]:
        try:
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://finance.yahoo.com/",
            }
            url = f"https://finance.yahoo.com/quote/{full_ticker}"
            resp = requests.get(url, headers=headers, timeout=settings.DATA_TIMEOUT_SECONDS)
            if resp.status_code != 200:
                logger.debug(f"Yahoo HTML fetch failed for {full_ticker}: {resp.status_code}")
                return None
            return YahooFetcher._parse_yahoo_price_from_html(resp.text)
        except Exception as e:
            logger.debug(f"Yahoo HTML fallback failed for {full_ticker}: {e}")
            return None

    @staticmethod
    async def _get_idx_price_snapshot(ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch the latest IDX snapshot for a ticker when Yahoo fails."""
        normalized_ticker = normalize_ticker(ticker)
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: IDXScraper.get_stock_by_ticker(normalized_ticker))
            return result
        except Exception as e:
            logger.debug(f"IDX snapshot search failed for {ticker}: {e}")
            return None

    @staticmethod
    async def get_current_price(ticker: str) -> Optional[float]:
        """Get current price for a stock."""
        normalized_ticker = normalize_ticker(ticker)
        full_ticker = normalized_ticker if normalized_ticker.endswith(".JK") else f"{normalized_ticker}.JK"
        try:
            loop = asyncio.get_event_loop()

            def _quote():
                try:
                    with contextlib.redirect_stderr(io.StringIO()):
                        ticker_obj = yf.Ticker(full_ticker)
                        fast = getattr(ticker_obj, 'fast_info', None)
                        if fast and isinstance(fast, dict):
                            last = fast.get('last_price') or fast.get('last')
                            if last is not None:
                                return float(last)

                        info = getattr(ticker_obj, 'info', None)
                        if isinstance(info, dict):
                            market_price = info.get('regularMarketPrice') or info.get('previousClose')
                            if market_price is not None:
                                return float(market_price)

                        hist = ticker_obj.history(period="1d", interval="1m")
                        if hist is not None and not hist.empty:
                            if isinstance(hist.columns, pd.MultiIndex):
                                hist.columns = hist.columns.droplevel(1)
                            return float(hist["Close"].iloc[-1])

                        hist = ticker_obj.history(period="2d", interval="5m")
                        if hist is not None and not hist.empty:
                            if isinstance(hist.columns, pd.MultiIndex):
                                hist.columns = hist.columns.droplevel(1)
                            return float(hist["Close"].iloc[-1])

                    return None
                except Exception as e:
                    logger.debug(f"Yahoo current price direct fetch failed for {full_ticker}: {e}")
                    return None

            price = await loop.run_in_executor(None, _quote)
            if price is not None:
                return price

            html_price = await loop.run_in_executor(None, lambda: YahooFetcher._get_current_price_from_yahoo_html(full_ticker))
            if html_price is not None:
                return html_price

            # Final fallback: use latest close from daily data or IDX value
            df = await YahooFetcher.fetch_stock_data(normalized_ticker, period="1d", interval="5m")
            if df is not None and not df.empty:
                return float(df.iloc[-1]["Close"])

            idx_snapshot = await YahooFetcher._get_idx_price_snapshot(normalized_ticker)
            if idx_snapshot and idx_snapshot.get("last_price") is not None:
                return float(idx_snapshot["last_price"])

            return None
        except Exception as e:
            logger.error(f"Error getting current price for {ticker}: {e}")
            return None
    
    @staticmethod
    async def get_stock_info(ticker: str) -> Optional[Dict]:
        """Get stock info (name, sector, market cap, etc)."""
        try:
            full_ticker = ticker if ticker.endswith(".JK") else f"{ticker}.JK"
            
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: yf.Ticker(full_ticker).info
            )
            
            if info:
                return {
                    "ticker": ticker,
                    "name": info.get("longName", ticker),
                    "sector": info.get("sector", "Unknown"),
                    "market_cap": info.get("marketCap"),
                    "pe_ratio": info.get("trailingPE"),
                }
            return None
        except Exception as e:
            logger.error(f"Error getting info for {ticker}: {e}")
            return None
