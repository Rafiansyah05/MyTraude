"""
Google Gemini API client for AI-powered analysis.
Implements retry logic, API key rotation, and response parsing.
"""

import asyncio
from typing import Optional, List, Dict
# pyrefly: ignore [missing-import]
import google.generativeai as genai

from config.settings import settings
from utils.logger import get_logger
from utils.helpers import retry_async

logger = get_logger(__name__)


class GeminiClient:
    """Gemini API client with key rotation and retry logic."""
    
    _api_keys: List[str] = []
    _current_key_index: int = 0
    _model: Optional[genai.GenerativeModel] = None
    
    @classmethod
    def initialize(cls):
        """Initialize Gemini client with API keys."""
        cls._api_keys = settings.GEMINI_API_KEYS
        if not cls._api_keys:
            raise ValueError("No Gemini API keys configured")
        
        logger.info(f"Initialized Gemini with {len(cls._api_keys)} API keys")
        cls._set_current_key()
    
    @classmethod
    def _set_current_key(cls):
        """Set current API key."""
        if not cls._api_keys:
            raise ValueError("No API keys available")
        
        key = cls._api_keys[cls._current_key_index % len(cls._api_keys)]
        genai.configure(api_key=key)
        cls._model = genai.GenerativeModel(settings.GEMINI_MODEL)
        logger.debug(f"Using API key {cls._current_key_index % len(cls._api_keys)}")
    
    @classmethod
    def _rotate_key(cls):
        """Rotate to next API key."""
        cls._current_key_index += 1
        logger.info(f"Rotating API key to {cls._current_key_index % len(cls._api_keys)}")
        cls._set_current_key()
    
    @classmethod
    async def generate_response(
        cls,
        prompt: str,
        max_retries: Optional[int] = None,
        timeout: Optional[int] = None
    ) -> Optional[str]:
        """
        Generate response from Gemini API.
        
        Args:
            prompt: Input prompt for Gemini
            max_retries: Max retry attempts (default from config)
            timeout: Request timeout in seconds (default from config)
        
        Returns:
            Generated text or None if failed
        """
        max_retries = max_retries or settings.GEMINI_RETRY_ATTEMPTS
        timeout = timeout or settings.GEMINI_TIMEOUT_SECONDS
        
        async def _generate():
            if not cls._model:
                cls.initialize()
            
            try:
                # Run in executor to avoid blocking
                loop = asyncio.get_event_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: cls._model.generate_content(prompt)
                    ),
                    timeout=timeout
                )
                
                if response and hasattr(response, 'text'):
                    logger.debug(f"Gemini response received ({len(response.text)} chars)")
                    return response.text
                else:
                    logger.error("Empty or invalid Gemini response")
                    return None
            
            except asyncio.TimeoutError:
                logger.warning(f"Gemini request timeout after {timeout}s")
                raise
            except Exception as e:
                logger.error(f"Gemini API error: {e}")
                # Try rotating key on error
                cls._rotate_key()
                raise
        
        # Retry with exponential backoff
        result = await retry_async(
            _generate,
            max_attempts=max_retries,
            backoff_seconds=settings.RETRY_BACKOFF_SECONDS,
            timeout_seconds=timeout
        )
        
        return result
    
    @classmethod
    async def analyze_stocks(
        cls,
        screened_stocks: List[Dict],
        total_capital: int
    ) -> Optional[str]:
        """
        Generate trading recommendations using Gemini.
        
        Args:
            screened_stocks: List of screened stock data
            total_capital: Total trading capital
        
        Returns:
            Formatted recommendations or None if failed
        """
        try:
            # Build prompt
            prompt = cls._build_analysis_prompt(screened_stocks, total_capital)
            
            # Generate response
            response = await cls.generate_response(prompt)
            
            if response:
                logger.info("Successfully generated recommendations")
            else:
                logger.error("Failed to generate recommendations")
            
            return response
        
        except Exception as e:
            logger.error(f"Error in analyze_stocks: {e}")
            return None
    
    @staticmethod
    def _build_analysis_prompt(
        screened_stocks: List[Dict],
        total_capital: int
    ) -> str:
        """Build structured prompt for Gemini."""
        
        # Format stock data
        stock_text = ""
        for stock in screened_stocks[:10]:  # Limit to top 10
            ticker = stock.get('ticker', 'N/A')
            price = stock.get('price', 'N/A')
            ma20 = stock.get('ma20', 'N/A')
            rsi = stock.get('rsi', 'N/A')
            vol = stock.get('volume_spike', 'N/A')

            try:
                rsi_str = f"{float(rsi):.1f}"
            except Exception:
                rsi_str = "N/A"

            try:
                vol_str = f"{float(vol):.2f}"
            except Exception:
                vol_str = "N/A"

            stock_text += (
                f"\n- {ticker}: Price={price}, MA20={ma20}, RSI={rsi_str}, Volume Spike={vol_str}x"
            )
        
        prompt = f"""You are a Senior Technical & Volume Action Analyst for Indonesian Stock Market.

ROLE: Analyze screened stocks and provide entry/target/cut loss levels.

CAPITAL: {total_capital:,} IDR

SCREENED STOCKS (with technical data):
{stock_text}

INSTRUCTIONS:
1. Use the latest available closing price for each stock. Do not rely on stale historical prices.
2. Select 2-3 best candidates from the list
3. For each stock, analyze price action and volume
4. Determine entry price, target price, cut loss price
5. Consider risk-reward ratio and technical levels

OUTPUT FORMAT (STRICT - NO MARKDOWN):
For each recommendation, output EXACTLY one line per stock:
TICKER|ANALYSIS_REASON|ENTRY_PRICE|TARGET_PRICE|CUT_LOSS

RULES:
- Do NOT include markdown, asterisks, or headers
- Do NOT include explanations outside the format
- Do NOT add numbering or bullets
- Each line must be one recommendation
- Prices must be numbers only
- Entry must be between cut loss and target
- Target should show 2-5% potential profit

EXAMPLE OUTPUT (exact format):
BBCA|Strong accumulation with breakout above MA20|9500|9900|9300
ASII|Volume spike on uptrend|7200|7500|7000"""
        
        return prompt
