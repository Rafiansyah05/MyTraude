"""
Configuration loader for the trading bot.
Loads settings from .env file with defaults and validation.
"""

import os
from dotenv import load_dotenv
from typing import Optional, List

# Load environment variables
load_dotenv()


class Settings:
    """Central configuration management."""
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_USER_ID: Optional[int] = int(os.getenv("TELEGRAM_USER_ID", "0")) or None
    
    # Gemini API Configuration
    GEMINI_API_KEYS: List[str] = [
        key.strip() for key in os.getenv("GEMINI_API_KEYS", "").split(",") if key.strip()
    ]
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-pro")
    GEMINI_TIMEOUT_SECONDS: int = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "60"))
    GEMINI_RETRY_ATTEMPTS: int = int(os.getenv("GEMINI_RETRY_ATTEMPTS", "3"))
    
    # Trading Configuration
    TRADING_CAPITAL_MAX: int = int(os.getenv("TRADING_CAPITAL_MAX", "100000000"))
    TRADING_CAPITAL_MIN: int = int(os.getenv("TRADING_CAPITAL_MIN", "50000"))
    TRADING_SESSION_HOUR: int = int(os.getenv("TRADING_SESSION_HOUR", "8"))
    TRADING_SESSION_MINUTE: int = int(os.getenv("TRADING_SESSION_MINUTE", "0"))
    ALLOCATION_PERCENTAGE: float = float(os.getenv("ALLOCATION_PERCENTAGE", "0.20"))
    
    # Technical Analysis Parameters
    MA_PERIOD: int = int(os.getenv("MA_PERIOD", "20"))
    RSI_PERIOD: int = int(os.getenv("RSI_PERIOD", "14"))
    RSI_OVERBOUGHT: int = int(os.getenv("RSI_OVERBOUGHT", "70"))
    MIN_VOLUME_SPIKE: float = float(os.getenv("MIN_VOLUME_SPIKE", "1.5"))
    
    # Data Fetching
    DATA_TIMEOUT_SECONDS: int = int(os.getenv("DATA_TIMEOUT_SECONDS", "30"))
    RETRY_ATTEMPTS: int = int(os.getenv("RETRY_ATTEMPTS", "3"))
    RETRY_BACKOFF_SECONDS: int = int(os.getenv("RETRY_BACKOFF_SECONDS", "5"))
    IDX_UPDATE_INTERVAL: int = int(os.getenv("IDX_UPDATE_INTERVAL", "300"))
    
    # Session Management
    SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "120"))
    SESSION_CLEANUP_INTERVAL: int = int(os.getenv("SESSION_CLEANUP_INTERVAL", "300"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE_PATH: Optional[str] = os.getenv("LOG_FILE_PATH")
    
    # Market Data Sources
    YAHOO_FINANCE_ENABLED: bool = os.getenv("YAHOO_FINANCE_ENABLED", "true").lower() == "true"
    IDX_API_URL: Optional[str] = os.getenv("IDX_API_URL")
    IDX_API_TOKEN: Optional[str] = os.getenv("IDX_API_TOKEN")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate critical settings."""
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required in .env")
        if not cls.GEMINI_API_KEYS:
            raise ValueError("GEMINI_API_KEYS is required in .env")
        return True


# Global settings instance
settings = Settings()
