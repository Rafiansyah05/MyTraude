"""
Helper utilities for the trading bot.
Common functions for formatting, validation, and async utilities.
"""

import asyncio
from typing import Optional, List, Dict, Any, Callable, TypeVar, Coroutine
from datetime import datetime, timedelta
import re

from utils.logger import get_logger
import html

logger = get_logger(__name__)

T = TypeVar("T")


def format_currency(amount: float) -> str:
    """Format currency as Indonesian Rupiah."""
    return f"Rp{int(amount):,}".replace(",", ".")


def format_percentage(value: float) -> str:
    """Format percentage value."""
    return f"{value:.2f}%"


def parse_capital_input(user_input: str) -> Optional[int]:
    """
    Parse user capital input. Accept various formats:
    - "1000000" -> 1000000
    - "1juta" -> 1000000
    - "2.5juta" -> 2500000
    """
    try:
        # Remove spaces
        text = user_input.strip().lower()
        
        # Check for "juta" (million) notation
        if "juta" in text:
            text = text.replace("juta", "").strip()
            # Handle decimal points (Indonesian uses comma)
            text = text.replace(",", ".")
            amount = float(text) * 1_000_000
            return int(amount)
        
        # Direct number
        return int(float(text))
    except (ValueError, AttributeError):
        return None


def validate_capital(capital: int, min_val: int, max_val: int) -> tuple[bool, str]:
    """Validate trading capital against min/max limits."""
    if capital < min_val:
        return False, f"Modal terlalu kecil. Minimum: {format_currency(min_val)}"
    if capital > max_val:
        return False, f"Modal terlalu besar. Maximum: {format_currency(max_val)}"
    return True, "Valid"


def is_market_open_wib() -> bool:
    """Check if market hours in WIB (UTC+7)."""
    from datetime import datetime, timezone, timedelta
    
    # Convert to WIB (UTC+7)
    wib_tz = timezone(timedelta(hours=7))
    now = datetime.now(wib_tz)
    
    # Market open: Mon-Fri, 09:00-15:30 WIB
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    market_open = now.replace(hour=9, minute=0, second=0)
    market_close = now.replace(hour=15, minute=30, second=0)
    
    return market_open <= now <= market_close


def get_next_market_open_time() -> datetime:
    """Get next market open time in WIB."""
    from datetime import datetime, timezone, timedelta
    
    wib_tz = timezone(timedelta(hours=7))
    now = datetime.now(wib_tz)
    
    # Next open: tomorrow at 09:00 if weekend/after hours
    next_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # If today is within market hours, return today's time
    if 9 <= now.hour < 15 and now.weekday() < 5:
        if now < next_open:
            return next_open
    
    # Add days until next weekday
    days_ahead = 0
    if now.hour >= 15 or now.weekday() >= 5:
        days_ahead = 1
    
    next_open = next_open + timedelta(days=days_ahead)
    
    # Skip weekends
    while next_open.weekday() >= 5:
        next_open = next_open + timedelta(days=1)
    
    return next_open


def is_stock_related_question(text: str) -> bool:
    """Check if a text is related to stocks or trading."""
    if not text or not isinstance(text, str):
        return False

    text_lower = text.lower()
    keywords = [
        "saham", "trading", "market", "bursa", "ihsg", "rsi", "ma20",
        "ma", "harga", "entry", "target", "cut loss", "cutloss",
        "strategi", "analisis", "volume", "investasi", "rekomendasi",
        "lot", "aset", "portofolio", "fundamental", "teknikal"
    ]

    return any(keyword in text_lower for keyword in keywords)


async def retry_async(
    func: Callable[..., Coroutine[Any, Any, T]],
    max_attempts: int = 3,
    backoff_seconds: int = 5,
    timeout_seconds: Optional[int] = None,
    *args,
    **kwargs
) -> Optional[T]:
    """
    Retry async function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_attempts: Maximum retry attempts
        backoff_seconds: Base backoff time
        timeout_seconds: Timeout per attempt
        *args, **kwargs: Arguments for func
    
    Returns:
        Function result or None if all retries fail
    """
    for attempt in range(max_attempts):
        try:
            if timeout_seconds:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
            else:
                return await func(*args, **kwargs)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout in {func.__name__} (attempt {attempt + 1}/{max_attempts})")
        except Exception as e:
            logger.warning(f"Error in {func.__name__} (attempt {attempt + 1}/{max_attempts}): {e}")
        
        if attempt < max_attempts - 1:
            wait_time = backoff_seconds * (2 ** attempt)
            logger.debug(f"Retrying {func.__name__} in {wait_time}s...")
            await asyncio.sleep(wait_time)
    
    logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
    return None


def extract_numbers(text: str) -> List[float]:
    """Extract all numbers from text."""
    pattern = r"[-+]?\d*\.?\d+"
    matches = re.findall(pattern, text)
    return [float(m) for m in matches]


def normalize_ticker(ticker: str) -> str:
    """Normalize IDX ticker by stripping .JK suffix and uppercasing."""
    if not ticker or not isinstance(ticker, str):
        return ""
    return ticker.strip().upper().replace(".JK", "")


def is_valid_ticker(ticker: str) -> bool:
    """Validate Indonesian stock ticker format."""
    ticker = normalize_ticker(ticker)
    return bool(re.match(r"^[A-Z]{3,5}$", ticker))


def batch_list(items: List[Any], batch_size: int) -> List[List[Any]]:
    """Split list into batches."""
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def escape_html(text: str) -> str:
    """Escape text for safe HTML parse_mode in Telegram messages."""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return html.escape(text)


def clean_markdown(text: str) -> str:
    """Remove common markdown artifacts to produce clean plain text for Telegram.

    Strips headings, bold/italic markers, code fences, and excessive newlines.
    """
    if not text or not isinstance(text, str):
        return text

    # Remove code fences and inline code
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`.+?`", "", text)

    # Remove markdown headings (###, ##, #)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)

    # Remove bold/italic markers
    text = text.replace("**", "").replace("__", "")
    text = text.replace("*", "").replace("_", "")

    # Remove excessive asterisks or underscores leftover
    text = re.sub(r"\*{2,}", "", text)

    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
