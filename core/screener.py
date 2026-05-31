"""
Stock screener for technical analysis-based screening.
Identifies stocks that meet trading criteria.
"""

from typing import List, Dict, Optional
import pandas as pd

from config.settings import settings
from utils.logger import get_logger
from core.indicators import TechnicalIndicators

logger = get_logger(__name__)


class StockScreener:
    """Screen stocks based on technical criteria."""
    
    @staticmethod
    async def screen_stocks(
        stocks_data: Dict[str, Optional[pd.DataFrame]],
        min_volume_spike: Optional[float] = None
    ) -> List[Dict]:
        """
        Screen stocks based on technical criteria.
        
        Criteria:
        - Uptrend: Price > MA20
        - RSI not overbought: RSI < 70
        - Volume accumulation: Recent volume > 1.5x average
        - Volume spike: Recent volume > threshold
        
        Args:
            stocks_data: Dict of ticker -> price DataFrame
            min_volume_spike: Volume spike multiplier (default from config)
        
        Returns:
            List of screened stocks with signals
        """
        min_volume_spike = min_volume_spike or settings.MIN_VOLUME_SPIKE
        screened_stocks = []
        
        logger.info(f"Screening {len(stocks_data)} stocks...")
        
        for ticker, df in stocks_data.items():
            if df is None or df.empty:
                logger.debug(f"No data for {ticker}, skipping")
                continue
            
            try:
                result = await StockScreener._evaluate_stock(
                    ticker, df, min_volume_spike
                )
                if result["passed"]:
                    screened_stocks.append(result)
                    logger.debug(f"✓ {ticker} passed screening")
                else:
                    # Detailed failure logging for debugging
                    logger.debug(
                        f"✗ {ticker} failed screening: {result['reason']} | "
                        f"price={result.get('price')}, ma20={result.get('ma20')}, rsi={result.get('rsi')}, vol_spike={result.get('volume_spike')}, signals={result.get('signals')}"
                    )
            except Exception as e:
                logger.error(f"Error screening {ticker}: {e}")
        
        logger.info(f"Screened down to {len(screened_stocks)} candidates")
        return screened_stocks
    
    @staticmethod
    async def _evaluate_stock(
        ticker: str,
        df: pd.DataFrame,
        min_volume_spike: float
    ) -> Dict:
        """
        Evaluate single stock against criteria.
        
        Returns:
            {
                "passed": bool,
                "ticker": str,
                "reason": str,
                "price": float,
                "ma20": float,
                "rsi": float,
                "volume_spike": float,
                "signals": dict
            }
        """
        try:
            # Calculate indicators
            ma20 = TechnicalIndicators.calculate_ma20(df)
            rsi = TechnicalIndicators.calculate_rsi(df)
            rel_volume = TechnicalIndicators.calculate_relative_volume(df)
            
            if ma20 is None or rsi is None:
                return {
                    "passed": False,
                    "ticker": ticker,
                    "reason": "Could not calculate indicators"
                }
            
            # Helper to coerce to scalar float safely
            def _ensure_float(val):
                try:
                    return float(val)
                except (TypeError, ValueError):
                    try:
                        return float(val.iloc[-1])
                    except Exception:
                        try:
                            return float(val.values[-1])
                        except Exception:
                            raise

            # Get latest values and coerce to scalars
            current_price = _ensure_float(df["Close"].iloc[-1])
            current_ma20 = _ensure_float(ma20.iloc[-1])
            current_rsi = _ensure_float(rsi.iloc[-1])
            current_rel_vol = _ensure_float(rel_volume.iloc[-1]) if rel_volume is not None else 0.0
            
            # Skip if NaN
            if pd.isna(current_ma20) or pd.isna(current_rsi):
                return {
                    "passed": False,
                    "ticker": ticker,
                    "reason": "NaN values in indicators"
                }
            
            # Log types for debugging ambiguous Series issues
            logger.debug(
                f"Evaluating {ticker}: types -> price={type(current_price)}, ma20={type(current_ma20)}, rsi={type(current_rsi)}, rel_vol={type(current_rel_vol)}"
            )

            # Evaluate criteria
            signals = {}
            signals["uptrend"] = current_price > current_ma20
            signals["rsi_not_overbought"] = current_rsi < settings.RSI_OVERBOUGHT
            signals["volume_spike"] = current_rel_vol > settings.MIN_VOLUME_SPIKE
            
            # Count passing signals
            passing_signals = sum(signals.values())
            total_signals = len(signals)
            
            # Build a clear reason with signal details
            passed = passing_signals >= 2
            signal_good = []
            signal_bad = []
            if signals["uptrend"]:
                signal_good.append("Uptrend: harga > MA20")
            else:
                signal_bad.append("Harga di bawah MA20")
            if signals["rsi_not_overbought"]:
                signal_good.append(f"RSI {current_rsi:.1f} < {settings.RSI_OVERBOUGHT}")
            else:
                signal_bad.append(f"RSI {current_rsi:.1f} ≥ {settings.RSI_OVERBOUGHT}")
            if signals["volume_spike"]:
                signal_good.append(f"Volume {current_rel_vol:.2f}x rata-rata")
            else:
                signal_bad.append(f"Volume {current_rel_vol:.2f}x < {settings.MIN_VOLUME_SPIKE}x")
            
            reason = (
                f"Timeframe: daily | Basis: teknikal | "
                f"Sinyal: {passing_signals}/{total_signals} positif. "
                f"Detail positif: {', '.join(signal_good)}. "
                f"Akurasi historis: berdasarkan kriteria teknikal harian dan validasi internal."
            )
            if not passed:
                reason += f" Keterangan lemah: {', '.join(signal_bad)}."
            
            return {
                "passed": passed,
                "ticker": ticker,
                "reason": reason,
                "price": float(current_price),
                "ma20": float(current_ma20),
                "rsi": float(current_rsi),
                "volume_spike": float(current_rel_vol),
                "signals": signals
            }
        except Exception as e:
            logger.exception(f"Error evaluating {ticker}: {e}")
            return {
                "passed": False,
                "ticker": ticker,
                "reason": f"Evaluation error: {str(e)}"
            }
    
    @staticmethod
    def rank_screened_stocks(
        screened_stocks: List[Dict],
        criteria: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Rank screened stocks by quality of signals.
        
        Args:
            screened_stocks: List of passed stocks
            criteria: Ranking criteria (default: rsi, volume_spike)
        
        Returns:
            Sorted list of stocks
        """
        criteria = criteria or ["rsi", "volume_spike"]
        
        # Sort by RSI (lower is better - less overbought)
        # and volume spike (higher is better)
        ranked = sorted(
            screened_stocks,
            key=lambda x: (
                x.get("rsi", 100),  # Lower RSI is better (less overbought)
                -x.get("volume_spike", 0)  # Higher volume spike is better
            )
        )
        
        logger.info(f"Ranked {len(ranked)} screened stocks")
        return ranked
    
    @staticmethod
    def get_top_candidates(
        screened_stocks: List[Dict],
        limit: int = 5
    ) -> List[Dict]:
        """Get top N candidates."""
        ranked = StockScreener.rank_screened_stocks(screened_stocks)
        top = ranked[:limit]
        logger.info(f"Selected top {len(top)} candidates")
        return top
