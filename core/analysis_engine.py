"""
Analysis engine for the trading bot.
Contains the shared workflow for stock screening, Gemini analysis, and recommendation formatting.
"""

from typing import List, Optional

from config.settings import settings
from data.idx_scraper import IDXScraper
from data.yahoo_fetcher import YahooFetcher
from core.screener import StockScreener
from core.risk_manager import RiskManager
from core.parser import ResponseParser
from core.parser import StockRecommendation
from ai.gemini_client import GeminiClient
from utils.logger import get_logger
from utils.helpers import escape_html, format_currency

logger = get_logger(__name__)


class AnalysisEngine:
    """Shared analysis workflow for the trading bot."""

    @staticmethod
    async def run_analysis_workflow(
        user_id: int,
        total_capital: int
    ) -> Optional[str]:
        """Run the full stock analysis workflow and return formatted results."""
        try:
            logger.info(f"Starting analysis workflow for user {user_id}")

            # Validate critical settings and initialize Gemini
            settings.validate()
            GeminiClient.initialize()

            # Load stock list and fetch data
            stocks_list = await IDXScraper.get_idx_stocks()
            tickers = [stock["ticker"] for stock in stocks_list]

            logger.info(f"Fetching data for {len(tickers)} stocks...")
            stocks_data = await YahooFetcher.fetch_multiple_stocks(tickers, period="3mo")

            # Fetch IDX JSON summary and merge metadata
            try:
                idx_summary = await IDXScraper.fetch_idx_summary()
                if idx_summary:
                    logger.info(f"IDX summary fetched: {len(idx_summary)} symbols")
                else:
                    logger.warning("IDX summary not available; continuing with Yahoo-only data")
            except Exception as e:
                idx_summary = None
                logger.warning(f"Failed to fetch IDX summary: {e}")

            logger.info("Screening stocks based on technical criteria...")
            screened = await StockScreener.screen_stocks(stocks_data, None, idx_summary)
            if not screened:
                logger.warning("No stocks passed screening")
                return "⚠️ Maaf, belum ada saham yang lolos screening saat ini. Coba lagi nanti."

            top_candidates = StockScreener.get_top_candidates(screened, limit=3)
            logger.info(f"Got {len(top_candidates)} top candidates")

            # Refresh latest prices for top candidates to ensure 'today' price
            for cand in top_candidates:
                try:
                    latest = await YahooFetcher.get_current_price(cand["ticker"])
                    if latest:
                        cand["price"] = latest
                        continue
                except Exception as e:
                    logger.debug(f"Could not refresh price for {cand['ticker']} from Yahoo: {e}")

                latest = AnalysisEngine._get_latest_price_from_data(cand["ticker"], stocks_data)
                if latest:
                    cand["price"] = latest

            ai_response = await GeminiClient.analyze_stocks(top_candidates, total_capital)
            recommendations = []
            if ai_response:
                recommendations = ResponseParser.parse_recommendations(ai_response)
                recommendations = ResponseParser.filter_valid_recommendations(recommendations)
                recommendations = recommendations[:3]

            if not recommendations:
                logger.error("AI did not return valid recommendations, using deterministic fallback")
                recommendations = AnalysisEngine._build_fallback_recommendations(top_candidates)
                recommendations = ResponseParser.filter_valid_recommendations(recommendations)

            if not recommendations:
                logger.warning("No valid recommendations available after fallback")
                return (
                    "⚠️ Analisis selesai, tetapi sistem tidak dapat membuat rekomendasi valid. "
                    "Silakan coba lagi nanti."
                )

            formatted_output = await AnalysisEngine._format_recommendations(
                recommendations, total_capital
            )
            return formatted_output

        except Exception as e:
            logger.error(f"Error in analysis workflow: {e}")
            return "❌ Terjadi kesalahan saat melakukan analisis. Silakan cek kembali konfigurasi dan coba lagi."

    @staticmethod
    async def run_watchlist_workflow() -> str:
        """Run a quick daily watchlist workflow and return formatted top stocks."""
        try:
            settings.validate()

            stocks_list = await IDXScraper.get_idx_stocks()
            tickers = [stock["ticker"] for stock in stocks_list]
            stocks_data = await YahooFetcher.fetch_multiple_stocks(tickers, period="1mo")

            # Try to enrich with IDX JSON data
            try:
                idx_summary = await IDXScraper.fetch_idx_summary()
                if idx_summary:
                    logger.info(f"IDX summary fetched for watchlist: {len(idx_summary)} symbols")
                else:
                    logger.warning("IDX summary not available for watchlist; proceeding without it")
            except Exception as e:
                idx_summary = None
                logger.warning(f"Failed to fetch IDX summary for watchlist: {e}")

            screened = await StockScreener.screen_stocks(stocks_data, None, idx_summary)
            if not screened:
                return (
                    "⚠️ Belum ada saham yang menarik untuk hari ini. "
                    "Silakan coba lagi nanti."
                )

            top_stocks = StockScreener.get_top_candidates(screened, limit=5)
            if not top_stocks:
                return (
                    "⚠️ Belum ada saham yang memenuhi kriteria saat ini. "
                    "Silakan coba lagi nanti."
                )

            message = "<b>📋 WATCHLIST SAHAM HARI INI</b>\n\n"
            message += (
                "Berikut 5 saham yang menarik untuk dipantau hari ini, "
                "lengkap dengan alasan, entry, target, dan cut loss.\n\n"
            )

            for index, stock in enumerate(top_stocks, 1):
                latest_price = await YahooFetcher.get_current_price(stock["ticker"])
                if latest_price is not None:
                    entry_price = float(latest_price)
                else:
                    latest = AnalysisEngine._get_latest_price_from_data(stock["ticker"], stocks_data)
                    entry_price = float(latest or stock.get("price", 0))

                target_price = entry_price * 1.04
                cut_loss_price = entry_price * 0.98

                message += f"<b>{escape_html(stock['ticker'])}</b>\n"
                message += f"• Alasan: {escape_html(stock.get('reason', 'Signal teknikal'))}\n"
                message += f"• Entry: {format_currency(entry_price)}\n"
                message += f"• Target: {format_currency(target_price)}\n"
                message += f"• Cut Loss: {format_currency(cut_loss_price)}\n\n"

            message += (
                "<i>Watchlist di-update berdasarkan screening teknikal harian. "
                "Gunakan /analyze untuk rekomendasi yang lebih detail.</i>"
            )
            return message
        except Exception as e:
            logger.error(f"Error in watchlist workflow: {e}")
            return "❌ Terjadi kesalahan saat membuat watchlist. Silakan coba lagi nanti."

    @staticmethod
    async def _format_recommendations(
        recommendations: List,
        total_capital: int
    ) -> str:
        """Format recommendations into a Telegram-friendly HTML message."""
        try:
            output = "<b>📈 REKOMENDASI TRADING PAGI</b>\n\n"

            for i, rec in enumerate(recommendations, 1):
                try:
                    risk = RiskManager.analyze_trade(
                        rec.ticker,
                        total_capital,
                        rec.entry_price,
                        rec.target_price,
                        rec.cut_loss,
                    )

                    if not risk:
                        continue

                    output += f"<b>#{i} {escape_html(rec.ticker)}</b>\n"
                    output += f"<b>Analisis:</b> {escape_html(rec.analysis_reason)}\n\n"
                    output += f"<b>Level Harga:</b>\n"
                    output += f"  Entry:  <b>{format_currency(rec.entry_price)}</b>\n"
                    output += f"  Target: <b>{format_currency(rec.target_price)}</b>\n"
                    output += f"  SL:     <b>{format_currency(rec.cut_loss)}</b>\n\n"
                    output += f"<b>Money Management:</b>\n"
                    output += f"  Modal Total:   {format_currency(total_capital)}\n"
                    output += f"  Alokasi Saham: {format_currency(risk.allocated_capital)}\n"
                    output += f"  Jumlah Lembar: {risk.quantity_shares:,} saham\n"
                    output += f"  Jumlah Lot:    {risk.quantity_lots} lot\n\n"
                    output += f"<b>Risk/Reward:</b>\n"
                    output += f"  Ratio: 1:{risk.risk_reward_ratio:.2f}\n"
                    output += f"  Potensi Profit: <b>{format_currency(risk.profit_target)}</b>\n"
                    output += f"  Max Loss:       <b>{format_currency(risk.loss_limit)}</b>\n"
                    output += f"{'-'*40}\n\n"

                except Exception as e:
                    logger.error(f"Error formatting recommendation for {rec.ticker}: {e}")
                    continue

            output += "\n<i>⚠️  DISCLAIMER: Rekomendasi ini untuk edukasi saja.\n"
            output += "Selalu lakukan riset sendiri sebelum trading.\n"
            output += "Tanya Gemini jika ada pertanyaan lebih lanjut.</i>\n"
            return output
        except Exception as e:
            logger.error(f"Error formatting recommendations: {e}")
            return "❌ Terjadi kesalahan saat memformat rekomendasi."

    @staticmethod
    def _get_latest_price_from_data(ticker: str, stocks_data: dict) -> Optional[float]:
        try:
            df = stocks_data.get(ticker)
            if df is None or df.empty or "Close" not in df.columns:
                return None

            last_close = df["Close"].iloc[-1]
            if isinstance(last_close, float) or isinstance(last_close, int):
                return float(last_close)
            if hasattr(last_close, "iloc"):
                return float(last_close.iloc[-1])
            return float(last_close)
        except Exception as e:
            logger.debug(f"Unable to derive latest price for {ticker}: {e}")
            return None

    @staticmethod
    def _build_fallback_recommendations(top_candidates: List[dict]) -> List[StockRecommendation]:
        fallback = []
        for cand in top_candidates[:3]:
            price = float(cand.get("price", 0) or 0)
            if price <= 0:
                continue

            entry_price = price
            target_price = round(entry_price * 1.03)
            cut_loss_price = round(entry_price * 0.98)
            rec = StockRecommendation(
                ticker=cand.get("ticker"),
                analysis_reason=cand.get("reason", "Signal teknikal"),
                entry_price=entry_price,
                target_price=float(target_price),
                cut_loss=float(cut_loss_price)
            )
            fallback.append(rec)
        return fallback
