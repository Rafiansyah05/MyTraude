"""
Prompt builder for structured AI prompts.
Constructs deterministic prompts for consistent AI responses.
"""

from typing import List, Dict, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class PromptBuilder:
    """Build structured prompts for AI analysis."""
    
    @staticmethod
    def build_stock_analysis_prompt(
        screened_stocks: List[Dict],
        total_capital: int,
        market_context: Optional[str] = None
    ) -> str:
        """
        Build prompt for stock analysis and recommendations.
        
        Args:
            screened_stocks: List of screened stocks
            total_capital: Trading capital
            market_context: Optional market context info
        
        Returns:
            Formatted prompt string
        """
        
        # Format stock data
        stock_lines = []
        for i, stock in enumerate(screened_stocks[:10], 1):
            line = (
                f"#{i} {stock.get('ticker', 'N/A')}: "
                f"Price={stock.get('price', 0):.0f}, "
                f"MA20={stock.get('ma20', 0):.0f}, "
                f"RSI={stock.get('rsi', 0):.1f}, "
                f"Vol={stock.get('volume_spike', 0):.2f}x, "
                f"Signal: {stock.get('reason', 'N/A')}"
            )
            stock_lines.append(line)
        
        stocks_data = "\n".join(stock_lines)
        
        prompt = f"""ROLE: Senior Technical & Volume Action Analyst for Indonesian Stock Market (IHSG)

CAPITAL: Rp {total_capital:,}

TASK: Analyze screened stocks and provide entry/target/cut loss recommendations

SCREENED CANDIDATES:
{stocks_data}

ANALYSIS REQUIREMENTS:
- Focus on technical price action and volume patterns
- Consider current market conditions
- Evaluate risk-reward ratio (minimum 1:2)
- Price levels should be realistic based on technical support/resistance

OUTPUT FORMAT (CRITICAL - FOLLOW EXACTLY):
Return ONLY recommendations in this format, one line per stock:
TICKER|ANALYSIS_REASON|ENTRY_PRICE|TARGET_PRICE|CUT_LOSS

STRICT RULES:
- NO markdown formatting
- NO introduction or explanation text
- NO bullet points or numbering
- NO extra information
- Each line must be: TICKER|REASON|ENTRY|TARGET|CUTLOSS
- Prices must be numeric only
- Entry Price must be: CUT_LOSS < ENTRY < TARGET
- Target should represent 2-5% upside
- Cut Loss should represent 2-3% downside
- REASON must explain the technical setup (max 50 chars)

EXAMPLE (exact format to follow):
BBCA|Accumulation breakout MA20|9500|9900|9300
ASII|Volume spike uptrend|7200|7500|7000
BMRI|RSI bounce support|3500|3700|3350

Analyze and recommend."""
        
        logger.debug("Stock analysis prompt built")
        return prompt
    
    @staticmethod
    def build_casual_chat_prompt(
        user_message: str,
        context: Optional[str] = None
    ) -> str:
        """
        Build prompt for casual financial chat (outside trading hours).
        
        Args:
            user_message: User's question
            context: Optional conversation context
        
        Returns:
            Formatted prompt
        """
        
        system_prompt = """You are a helpful financial analyst specializing in Indonesian stock market (IHSG).

INSTRUCTIONS:
- Answer questions about stocks, technical analysis, market conditions
- Provide educational information about trading and investing
- Be concise and helpful
- Explain concepts in simple terms
- Disclaimer: This is for educational purposes only, not financial advice

USER QUESTION:"""
        
        if context:
            prompt = f"{system_prompt}\nContext: {context}\n\nQuestion: {user_message}"
        else:
            prompt = f"{system_prompt}\n{user_message}"
        
        logger.debug("Casual chat prompt built")
        return prompt
    
    @staticmethod
    def build_market_analysis_prompt(
        market_data: Dict,
        recent_news: Optional[List[str]] = None
    ) -> str:
        """Build prompt for broader market analysis."""
        
        prompt = f"""Analyze current Indonesian stock market (IHSG) conditions:

MARKET DATA:
- IHSG Index: {market_data.get('ihsg_value', 'N/A')}
- Change: {market_data.get('change_pct', 'N/A')}%
- Top Sectors: {market_data.get('top_sectors', 'N/A')}

RECENT NEWS:"""
        
        if recent_news:
            for news in recent_news[:5]:
                prompt += f"\n- {news}"
        
        prompt += "\n\nProvide brief market outlook and sector recommendations."
        
        return prompt
    
    @staticmethod
    def build_risk_assessment_prompt(
        ticker: str,
        entry_price: float,
        target_price: float,
        cut_loss_price: float,
        stock_data: Optional[Dict] = None
    ) -> str:
        """Build prompt for risk assessment of a trade."""
        
        prompt = f"""Assess trade setup risk for {ticker}:

TRADE SETUP:
- Entry: {entry_price:.0f}
- Target: {target_price:.0f}
- Cut Loss: {cut_loss_price:.0f}
"""
        
        if stock_data:
            prompt += f"\nTECHNICAL DATA:\n"
            for key, value in stock_data.items():
                prompt += f"- {key}: {value}\n"
        
        prompt += "\nAssess: Risk-Reward Ratio, Setup Quality, Entry Timing"
        
        return prompt
