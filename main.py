"""
Main entry point for the AI Trading Assistant Bot.
Orchestrates bot initialization, data fetching, and analysis workflow.
"""

import asyncio
import sys
from typing import Optional, List, Dict

from config.settings import settings
from utils.logger import get_logger
from bot.telegram_bot import TradingBot
from bot.session_manager import SessionManager
from data.yahoo_fetcher import YahooFetcher
from data.idx_scraper import IDXScraper
from core.screener import StockScreener
from core.risk_manager import RiskManager
from core.indicators import TechnicalIndicators
from ai.gemini_client import GeminiClient
from core.parser import ResponseParser
from utils.helpers import format_currency

logger = get_logger(__name__)


class TradingAssistant:
    """Main orchestrator for trading analysis."""
    
    def __init__(self):
        """Initialize trading assistant."""
        self.bot: Optional[TradingBot] = None
    
    async def initialize(self):
        """Initialize all components."""
        try:
            logger.info("Initializing Trading Assistant...")
            
            # Validate settings
            settings.validate()
            logger.info("✓ Settings validated")
            
            # Initialize Gemini client
            GeminiClient.initialize()
            logger.info("✓ Gemini API initialized")
            
            # Initialize bot
            self.bot = TradingBot()
            logger.info("✓ Telegram bot initialized")
            
            logger.info("✅ All components initialized successfully")
        
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            raise
    
    async def run_analysis_workflow(
        self,
        user_id: int,
        total_capital: int
    ) -> Optional[str]:
        """
        Run complete analysis workflow.
        
        Args:
            user_id: User ID
            total_capital: Total trading capital
        
        Returns:
            Formatted recommendations text or None
        """
        try:
            logger.info(f"Starting analysis workflow for user {user_id}")
            
            # Get list of stocks to screen
            stocks_list = await IDXScraper.get_idx_stocks()
            tickers = [stock["ticker"] for stock in stocks_list]
            
            logger.info(f"Fetching data for {len(tickers)} stocks...")
            
            # Fetch data for all stocks
            stocks_data = await YahooFetcher.fetch_multiple_stocks(tickers, period="3mo")
            
            # Screen stocks
            logger.info("Screening stocks based on technical criteria...")
            screened = await StockScreener.screen_stocks(stocks_data)
            
            if not screened:
                logger.warning("No stocks passed screening")
                return None
            
            # Get top candidates
            top_candidates = StockScreener.get_top_candidates(screened, limit=5)
            logger.info(f"Got {len(top_candidates)} top candidates")
            
            # Generate AI recommendations
            logger.info("Generating AI recommendations...")
            ai_response = await GeminiClient.analyze_stocks(top_candidates, total_capital)
            
            if not ai_response:
                logger.error("AI analysis failed")
                return None
            
            # Parse AI response
            recommendations = ResponseParser.parse_recommendations(ai_response)
            recommendations = ResponseParser.filter_valid_recommendations(recommendations)
            
            if not recommendations:
                logger.warning("No valid recommendations parsed")
                return None
            
            logger.info(f"Got {len(recommendations)} valid recommendations")
            
            # Calculate risk management
            formatted_output = await self._format_recommendations(
                recommendations, total_capital
            )
            
            return formatted_output
        
        except Exception as e:
            logger.error(f"Error in analysis workflow: {e}")
            return None
    
    async def _format_recommendations(
        self,
        recommendations: List,
        total_capital: int
    ) -> str:
        """Format recommendations with risk management."""
        try:
            output = "📈 REKOMENDASI TRADING PAGI\n\n"
            
            for i, rec in enumerate(recommendations, 1):
                try:
                    # Analyze trade risk
                    risk = RiskManager.analyze_trade(
                        rec.ticker,
                        total_capital,
                        rec.entry_price,
                        rec.target_price,
                        rec.cut_loss
                    )
                    
                    if not risk:
                        continue
                    
                    output += f"{'='*50}\n"
                    output += f"#{i} {rec.ticker}\n"
                    output += f"{'='*50}\n"
                    output += f"📊 Analisis: {rec.analysis_reason}\n\n"
                    output += f"💰 Harga Entry:  Rp{rec.entry_price:>10,.0f}\n"
                    output += f"🎯 Target Price: Rp{rec.target_price:>10,.0f}\n"
                    output += f"🛑 Cut Loss:     Rp{rec.cut_loss:>10,.0f}\n\n"
                    output += f"💸 Money Management:\n"
                    output += f"   Modal Total:     {format_currency(total_capital)}\n"
                    output += f"   Alokasi:         {format_currency(risk.allocated_capital)}\n"
                    output += f"   Jumlah Saham:    {risk.quantity_shares:,} lembar\n"
                    output += f"   Jumlah Lot:      {risk.quantity_lots} lot (@ 100 saham)\n\n"
                    output += f"📈 Profit/Risk:\n"
                    output += f"   Potensi Profit:  {format_currency(risk.profit_target)}\n"
                    output += f"   Max Loss:        {format_currency(risk.loss_limit)}\n"
                    output += f"   Risk/Reward:     1:{risk.risk_reward_ratio:.2f}\n\n"
                
                except Exception as e:
                    logger.error(f"Error formatting {rec.ticker}: {e}")
                    continue
            
            output += f"{'='*50}\n"
            output += "⚠️ DISCLAIMER: Rekomendasi ini untuk edukasi saja.\n"
            output += "Selalu lakukan riset sendiri sebelum trading.\n"
            
            return output
        
        except Exception as e:
            logger.error(f"Error formatting recommendations: {e}")
            return None
    
    async def start(self):
        """Start the bot."""
        try:
            await self.initialize()
            
            if self.bot:
                await self.bot.start()
        
        except KeyboardInterrupt:
            logger.info("Bot interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the bot."""
        try:
            if self.bot:
                await self.bot.stop()
            logger.info("Trading Assistant shutdown")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


async def main():
    """Main entry point."""
    try:
        assistant = TradingAssistant()
        await assistant.start()
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated")
        sys.exit(0)
