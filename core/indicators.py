"""
Technical indicators calculator.
Implements MA20, RSI, Volume analysis using ta-lib.
"""

from typing import Optional
import pandas as pd
import ta

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class TechnicalIndicators:
    """Calculate technical indicators for stock analysis."""
    
    @staticmethod
    def calculate_ma20(df: pd.DataFrame) -> Optional[pd.Series]:
        """
        Calculate 20-period Moving Average.
        
        Args:
            df: DataFrame with 'Close' column
        
        Returns:
            Series with MA20 values or None if failed
        """
        try:
            if df is None or df.empty or "Close" not in df.columns:
                return None

            # Ensure Close is a 1D Series
            close = df["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]

            ma20 = close.rolling(window=settings.MA_PERIOD).mean()
            logger.debug(f"Calculated MA{settings.MA_PERIOD}")
            return ma20
        except Exception as e:
            logger.error(f"Error calculating MA: {e}")
            return None
    
    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: Optional[int] = None) -> Optional[pd.Series]:
        """
        Calculate RSI (Relative Strength Index).
        
        Args:
            df: DataFrame with 'Close' column
            period: RSI period (default from config)
        
        Returns:
            Series with RSI values or None if failed
        """
        try:
            if df is None or df.empty or "Close" not in df.columns:
                return None

            period = period or settings.RSI_PERIOD

            # Ensure Close is a 1D Series
            close = df["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]

            # Using ta-lib RSI
            rsi = ta.momentum.rsi(close, window=period)
            logger.debug(f"Calculated RSI({period})")
            return rsi
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return None
    
    @staticmethod
    def calculate_relative_volume(df: pd.DataFrame, period: int = 20) -> Optional[pd.Series]:
        """
        Calculate relative volume (current volume / average volume).
        
        Args:
            df: DataFrame with 'Volume' column
            period: Period for volume average
        
        Returns:
            Series with relative volume or None if failed
        """
        try:
            if df is None or df.empty or "Volume" not in df.columns:
                return None

            vol = df["Volume"]
            if isinstance(vol, pd.DataFrame):
                vol = vol.iloc[:, 0]

            avg_volume = vol.rolling(window=period).mean()
            rel_volume = vol / avg_volume
            
            logger.debug(f"Calculated relative volume")
            return rel_volume
        except Exception as e:
            logger.error(f"Error calculating relative volume: {e}")
            return None
    
    @staticmethod
    def detect_volume_accumulation(
        df: pd.DataFrame,
        threshold: float = 1.5
    ) -> Optional[bool]:
        """
        Detect volume accumulation signal.
        True if current volume > threshold * average volume.
        
        Args:
            df: DataFrame with 'Volume' column
            threshold: Volume spike multiplier
        
        Returns:
            True if accumulation detected, False otherwise
        """
        try:
            if df is None or df.empty or "Volume" not in df.columns:
                return False
            
            # Use last 20 days for average
            avg_volume = df["Volume"].tail(20).mean()
            current_volume = df["Volume"].iloc[-1]
            
            is_accumulation = current_volume > (threshold * avg_volume)
            logger.debug(f"Volume accumulation check: {is_accumulation}")
            return is_accumulation
        except Exception as e:
            logger.error(f"Error detecting volume accumulation: {e}")
            return False
    
    @staticmethod
    def detect_ma_breakout(df: pd.DataFrame) -> Optional[bool]:
        """
        Detect price above MA20 (potential breakout).
        
        Args:
            df: DataFrame with 'Close' column
        
        Returns:
            True if price > MA20, False otherwise
        """
        try:
            if df is None or df.empty:
                return False
            
            ma20 = TechnicalIndicators.calculate_ma20(df)
            if ma20 is None or ma20.isna().all():
                return False
            
            current_price = df["Close"].iloc[-1]
            current_ma = ma20.iloc[-1]
            
            is_breakout = current_price > current_ma
            logger.debug(f"MA breakout check: {is_breakout}")
            return is_breakout
        except Exception as e:
            logger.error(f"Error detecting MA breakout: {e}")
            return False
    
    @staticmethod
    def detect_uptrend(df: pd.DataFrame, period: int = 20) -> Optional[bool]:
        """
        Simple uptrend detection: close > open on average.
        
        Args:
            df: DataFrame with 'Close' and 'Open' columns
            period: Period to check
        
        Returns:
            True if uptrend, False otherwise
        """
        try:
            if df is None or df.empty or len(df) < period:
                return False
            
            recent = df.tail(period)
            uptrend = (recent["Close"] > recent["Open"]).sum() > (period * 0.6)
            logger.debug(f"Uptrend check: {uptrend}")
            return uptrend
        except Exception as e:
            logger.error(f"Error detecting uptrend: {e}")
            return False
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Calculate all technical indicators and add to DataFrame.
        
        Args:
            df: Original DataFrame with OHLCV
        
        Returns:
            Enhanced DataFrame with indicator columns
        """
        try:
            result = df.copy()
            
            # Add indicators
            result["MA20"] = TechnicalIndicators.calculate_ma20(result)
            result["RSI14"] = TechnicalIndicators.calculate_rsi(result)
            result["RelVolume"] = TechnicalIndicators.calculate_relative_volume(result)
            
            logger.debug("All indicators calculated")
            return result
        except Exception as e:
            logger.error(f"Error calculating all indicators: {e}")
            return None
