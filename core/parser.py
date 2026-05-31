"""
Safe response parser for Gemini AI responses.
Extracts structured trading recommendations from AI output.
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StockRecommendation:
    """Structured stock recommendation."""
    ticker: str
    analysis_reason: str
    entry_price: float
    target_price: float
    cut_loss: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "ticker": self.ticker,
            "reason": self.analysis_reason,
            "entry": self.entry_price,
            "target": self.target_price,
            "cut_loss": self.cut_loss,
        }


class ResponseParser:
    """Parse and validate Gemini API responses."""
    
    RECOMMENDATION_PATTERN = re.compile(
        r"([A-Z]{4,5})\s*\|\s*(.+?)\s*\|\s*([\d.,]+)\s*\|\s*([\d.,]+)\s*\|\s*([\d.,]+)",
        re.IGNORECASE
    )
    
    @staticmethod
    def parse_recommendations(response_text: str) -> List[StockRecommendation]:
        """
        Parse structured recommendations from Gemini response.
        Expected format: TICKER|REASON|ENTRY_PRICE|TARGET_PRICE|CUT_LOSS
        
        Args:
            response_text: Raw Gemini response
        
        Returns:
            List of StockRecommendation objects
        """
        try:
            recommendations = []
            
            # Split by newlines to find each recommendation
            lines = response_text.strip().split("\n")
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Try to match the pattern
                match = ResponseParser.RECOMMENDATION_PATTERN.search(line)
                if match:
                    try:
                        ticker = match.group(1).upper()
                        reason = match.group(2).strip()
                        entry = ResponseParser._parse_price(match.group(3))
                        target = ResponseParser._parse_price(match.group(4))
                        cutloss = ResponseParser._parse_price(match.group(5))
                        
                        if entry and target and cutloss:
                            rec = StockRecommendation(
                                ticker=ticker,
                                analysis_reason=reason,
                                entry_price=entry,
                                target_price=target,
                                cut_loss=cutloss
                            )
                            recommendations.append(rec)
                            logger.debug(f"Parsed recommendation: {ticker}")
                        else:
                            logger.warning(f"Could not parse prices from: {line}")
                    except ValueError as e:
                        logger.warning(f"Error parsing recommendation line '{line}': {e}")
                        continue
            
            if not recommendations:
                logger.warning("No valid recommendations found in response")
            else:
                logger.info(f"Parsed {len(recommendations)} recommendations")
            
            return recommendations
        except Exception as e:
            logger.error(f"Error parsing recommendations: {e}")
            return []
    
    @staticmethod
    def _parse_price(price_str: str) -> Optional[float]:
        """
        Parse price string, handling various formats.
        
        Args:
            price_str: Price as string (e.g., "9500", "9,500", "9.500")
        
        Returns:
            Parsed float price or None
        """
        try:
            # Remove common separators
            clean = price_str.strip()
            clean = clean.replace(",", "")  # Remove commas (Indonesian)
            clean = clean.replace(".", "")  # Remove dots used as thousands
            
            # Handle decimal points (look for smallest decimal part)
            # Indonesian uses comma as decimal, Western uses dot
            if "," in price_str and "." in price_str:
                # If both present, assume comma is decimal
                clean = price_str.replace(".", "").replace(",", ".")
            elif "." in price_str:
                # Check if it's decimal or thousands separator
                # If only 1-2 digits after dot, likely decimal
                parts = price_str.split(".")
                if len(parts[-1]) <= 2:
                    # Keep as decimal
                    clean = price_str
                else:
                    # Remove as thousands separator
                    clean = price_str.replace(".", "")
            
            price = float(clean)
            if price > 0:
                return price
            return None
        except Exception as e:
            logger.warning(f"Could not parse price '{price_str}': {e}")
            return None
    
    @staticmethod
    def validate_recommendation(rec: StockRecommendation) -> bool:
        """
        Validate recommendation logic.
        
        Args:
            rec: Recommendation to validate
        
        Returns:
            True if recommendation is logically valid
        """
        try:
            # Entry should be between cut loss and target
            if not (rec.cut_loss <= rec.entry_price <= rec.target_price):
                logger.warning(
                    f"Invalid price levels for {rec.ticker}: "
                    f"CL={rec.cut_loss}, Entry={rec.entry_price}, Target={rec.target_price}"
                )
                return False
            
            # Target should be higher than entry by at least 1%
            min_profit_pct = 0.01
            profit_pct = (rec.target_price - rec.entry_price) / rec.entry_price
            if profit_pct < min_profit_pct:
                logger.warning(
                    f"Profit potential too low for {rec.ticker}: {profit_pct:.2%}"
                )
                return False
            
            # Risk/reward ratio should be reasonable
            risk = rec.entry_price - rec.cut_loss
            reward = rec.target_price - rec.entry_price
            if risk > 0:
                rr_ratio = reward / risk
                if rr_ratio < 1:
                    logger.warning(
                        f"Risk/reward ratio too low for {rec.ticker}: {rr_ratio:.2f}"
                    )
                    # Don't reject, just warn
            
            return True
        except Exception as e:
            logger.error(f"Error validating recommendation: {e}")
            return False
    
    @staticmethod
    def filter_valid_recommendations(
        recommendations: List[StockRecommendation]
    ) -> List[StockRecommendation]:
        """Filter only valid recommendations."""
        valid = [r for r in recommendations if ResponseParser.validate_recommendation(r)]
        logger.info(f"Filtered to {len(valid)} valid recommendations")
        return valid
