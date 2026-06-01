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
        min_volume_spike: Optional[float] = None,
        idx_summary: Optional[Dict[str, Dict]] = None
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
                    ticker, df, min_volume_spike, idx_summary
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
        min_volume_spike: float,
        idx_summary: Optional[Dict[str, Dict]] = None
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

            # Additional IDX-derived metrics (if available)
            idx_entry = None
            idx_sym = ticker.replace('.JK', '').upper()
            if idx_summary and isinstance(idx_summary, dict):
                idx_entry = idx_summary.get(idx_sym) or idx_summary.get(idx_sym.upper())

            idx_volume = None
            idx_value = None
            idx_frequency = None
            foreign_buy = None
            foreign_sell = None
            foreign_net = None
            bid_volume = None
            offer_volume = None
            if idx_entry:
                try:
                    idx_volume = float(idx_entry.get('volume') or 0)
                    idx_value = float(idx_entry.get('value') or 0)
                    idx_frequency = int(idx_entry.get('frequency') or 0)
                    foreign_buy = float(idx_entry.get('foreign_buy') or 0)
                    foreign_sell = float(idx_entry.get('foreign_sell') or 0)
                    foreign_net = float(idx_entry.get('foreign_net') or (foreign_buy - foreign_sell))
                    bid_volume = int(idx_entry.get('bid_volume') or 0)
                    offer_volume = int(idx_entry.get('offer_volume') or 0)
                except Exception:
                    pass
            
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

            # Evaluate base criteria (unchanged logic)
            signals = {}
            signals["uptrend"] = current_price > current_ma20
            signals["rsi_not_overbought"] = current_rsi < settings.RSI_OVERBOUGHT
            signals["volume_spike"] = current_rel_vol > settings.MIN_VOLUME_SPIKE

            # Compute additional metrics and extra signals
            avg_vol_20 = None
            volume_ratio = None
            if 'Volume' in df.columns and len(df['Volume'].dropna()) >= 5:
                try:
                    avg_vol_20 = float(df['Volume'].tail(20).mean())
                    if avg_vol_20 and idx_volume is not None:
                        volume_ratio = idx_volume / avg_vol_20 if avg_vol_20 > 0 else None
                except Exception:
                    avg_vol_20 = None

            extra_signals = {}
            # foreign flow signal
            if foreign_net is not None:
                extra_signals['foreign_flow_bull'] = foreign_net > 0
                extra_signals['foreign_flow_bear'] = foreign_net < 0
            else:
                extra_signals['foreign_flow_bull'] = False
                extra_signals['foreign_flow_bear'] = False

            # volume ratio signal (use MIN_VOLUME_SPIKE threshold as heuristic)
            if volume_ratio is not None:
                extra_signals['volume_ratio_high'] = volume_ratio > settings.MIN_VOLUME_SPIKE
            else:
                extra_signals['volume_ratio_high'] = False

            # frequency signal
            try:
                extra_signals['frequency_high'] = (idx_frequency is not None and idx_frequency > 1000)
            except Exception:
                extra_signals['frequency_high'] = False
            
            # Count passing base signals (preserve original pass logic)
            passing_signals = sum(signals.values())
            total_signals = len(signals)

            # Preserve original pass threshold
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
            # Append extra metrics summary if available
            extras = []
            if volume_ratio is not None:
                extras.append(f"volume_ratio={volume_ratio:.2f}x")
            if foreign_net is not None:
                extras.append(f"foreign_net={foreign_net:+.0f}")
            if idx_frequency is not None:
                extras.append(f"frequency={idx_frequency}")
            if extras:
                reason += " Extra: " + ", ".join(extras) + "."

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
                "signals": signals,
                # IDX enriched fields
                "idx_volume": idx_volume,
                "idx_value": idx_value,
                "idx_frequency": idx_frequency,
                "foreign_buy": foreign_buy,
                "foreign_sell": foreign_sell,
                "foreign_net": foreign_net,
                "bid_volume": bid_volume,
                "offer_volume": offer_volume,
                "volume_ratio": volume_ratio,
                "extra_signals": extra_signals
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
                -x.get("volume_spike", 0),  # Higher volume spike is better
                - (x.get('foreign_net') or 0),  # Higher foreign_net (net buy) is better
                - (x.get('idx_frequency') or 0)  # Higher trading frequency is better
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
