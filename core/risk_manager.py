"""
Risk management engine for trading calculations.
Hardcoded calculations (NOT delegated to AI).
"""

from typing import Dict, Optional, List
from dataclasses import dataclass

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RiskAnalysis:
    """Risk management analysis result."""
    ticker: str
    total_capital: int
    allocated_capital: int
    entry_price: float
    target_price: float
    cut_loss: float
    quantity_shares: int
    quantity_lots: int
    profit_target: int
    loss_limit: int
    risk_reward_ratio: float
    potential_profit_percent: float
    potential_loss_percent: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "ticker": self.ticker,
            "total_capital": self.total_capital,
            "allocated": self.allocated_capital,
            "entry_price": self.entry_price,
            "target_price": self.target_price,
            "cut_loss": self.cut_loss,
            "shares": self.quantity_shares,
            "lots": self.quantity_lots,
            "profit_target": self.profit_target,
            "loss_limit": self.loss_limit,
            "rr_ratio": self.risk_reward_ratio,
            "potential_profit_pct": self.potential_profit_percent,
            "potential_loss_pct": self.potential_loss_percent,
        }


class RiskManager:
    """Hardcoded risk management calculations."""
    
    # Constants
    SHARES_PER_LOT = 100  # Indonesian standard lot size
    MAX_ALLOCATION_PERCENT = 0.20  # 20% per stock
    MIN_ALLOCATION_AMOUNT = 100000  # Rp 100k minimum
    MAX_POSITIONS = 5  # Max number of positions
    
    @staticmethod
    def calculate_allocation(
        total_capital: int,
        max_percent: Optional[float] = None
    ) -> int:
        """
        Calculate maximum allocation per stock.
        Formula: Ms = Mtotal × 0.20
        
        Args:
            total_capital: Total trading capital (Rp)
            max_percent: Max allocation percentage (default: 20%)
        
        Returns:
            Maximum allocation amount
        """
        max_percent = max_percent or RiskManager.MAX_ALLOCATION_PERCENT
        allocation = int(total_capital * max_percent)
        
        logger.debug(f"Allocation: {allocation} (from {total_capital})")
        return allocation
    
    @staticmethod
    def calculate_quantity_shares(
        allocated_capital: int,
        entry_price: float
    ) -> int:
        """
        Calculate quantity of shares to buy.
        Formula: Qshares = Ms / EntryPrice
        
        Args:
            allocated_capital: Allocated capital for this stock (Rp)
            entry_price: Entry price (Rp)
        
        Returns:
            Number of shares
        """
        if entry_price <= 0:
            logger.error(f"Invalid entry price: {entry_price}")
            return 0
        
        quantity = int(allocated_capital / entry_price)
        logger.debug(f"Share quantity: {quantity}")
        return quantity
    
    @staticmethod
    def calculate_quantity_lots(
        quantity_shares: int,
        shares_per_lot: Optional[int] = None
    ) -> int:
        """
        Calculate quantity of lots (100-share lots).
        Formula: Qlots = max(1, floor(Qshares / 100))
        
        Args:
            quantity_shares: Number of shares
            shares_per_lot: Shares per lot (default: 100 for Indonesia)
        
        Returns:
            Number of lots
        """
        shares_per_lot = shares_per_lot or RiskManager.SHARES_PER_LOT
        
        if quantity_shares <= 0:
            return 0
        
        lots = max(1, int(quantity_shares // shares_per_lot))
        logger.debug(f"Lot quantity: {lots}")
        return lots
    
    @staticmethod
    def calculate_total_shares(
        quantity_lots: int,
        shares_per_lot: Optional[int] = None
    ) -> int:
        """Calculate total shares from lots."""
        shares_per_lot = shares_per_lot or RiskManager.SHARES_PER_LOT
        return quantity_lots * shares_per_lot
    
    @staticmethod
    def calculate_entry_cost(
        quantity_shares: int,
        entry_price: float
    ) -> int:
        """Calculate total cost at entry."""
        return int(quantity_shares * entry_price)
    
    @staticmethod
    def calculate_profit_target(
        quantity_shares: int,
        target_price: float
    ) -> int:
        """Calculate profit at target price."""
        return int(quantity_shares * target_price)
    
    @staticmethod
    def calculate_loss_limit(
        quantity_shares: int,
        cut_loss_price: float
    ) -> int:
        """Calculate loss at cut loss price."""
        return int(quantity_shares * cut_loss_price)
    
    @staticmethod
    def calculate_risk_reward_ratio(
        entry_price: float,
        target_price: float,
        cut_loss_price: float
    ) -> float:
        """
        Calculate risk/reward ratio.
        RR = (Target - Entry) / (Entry - CutLoss)
        
        Args:
            entry_price: Entry price
            target_price: Target price
            cut_loss_price: Cut loss price
        
        Returns:
            Risk/reward ratio (higher is better)
        """
        try:
            reward = target_price - entry_price
            risk = entry_price - cut_loss_price
            
            if risk <= 0:
                logger.warning(f"Invalid risk calculation: CL={cut_loss_price}, Entry={entry_price}")
                return 0
            
            rr_ratio = reward / risk
            logger.debug(f"Risk/Reward ratio: {rr_ratio:.2f}")
            return rr_ratio
        except Exception as e:
            logger.error(f"Error calculating RR ratio: {e}")
            return 0
    
    @staticmethod
    def calculate_profit_loss_percent(
        entry_price: float,
        target_or_loss_price: float
    ) -> float:
        """Calculate profit/loss percentage."""
        if entry_price <= 0:
            return 0
        return (target_or_loss_price - entry_price) / entry_price * 100
    
    @staticmethod
    def analyze_trade(
        ticker: str,
        total_capital: int,
        entry_price: float,
        target_price: float,
        cut_loss_price: float
    ) -> Optional[RiskAnalysis]:
        """
        Complete risk analysis for a trade.
        
        Args:
            ticker: Stock ticker
            total_capital: Total trading capital
            entry_price: Entry price
            target_price: Target price
            cut_loss_price: Cut loss price
        
        Returns:
            RiskAnalysis object or None if invalid
        """
        try:
            # Validate prices
            if not (cut_loss_price <= entry_price <= target_price):
                logger.error(
                    f"Invalid price sequence for {ticker}: "
                    f"CL={cut_loss_price}, Entry={entry_price}, Target={target_price}"
                )
                return None
            
            # Calculate components
            allocated = RiskManager.calculate_allocation(total_capital)
            shares = RiskManager.calculate_quantity_shares(allocated, entry_price)
            lots = RiskManager.calculate_quantity_lots(shares)
            
            if lots == 0:
                logger.warning(f"Zero lots for {ticker}, allocation too low or price too high")
                return None
            
            # Recalculate with actual lots
            actual_shares = RiskManager.calculate_total_shares(lots)
            
            profit_target = RiskManager.calculate_profit_target(actual_shares, target_price)
            loss_limit = RiskManager.calculate_loss_limit(actual_shares, cut_loss_price)
            
            rr_ratio = RiskManager.calculate_risk_reward_ratio(
                entry_price, target_price, cut_loss_price
            )
            
            profit_pct = RiskManager.calculate_profit_loss_percent(entry_price, target_price)
            loss_pct = RiskManager.calculate_profit_loss_percent(entry_price, cut_loss_price)
            
            analysis = RiskAnalysis(
                ticker=ticker,
                total_capital=total_capital,
                allocated_capital=allocated,
                entry_price=entry_price,
                target_price=target_price,
                cut_loss=cut_loss_price,
                quantity_shares=actual_shares,
                quantity_lots=lots,
                profit_target=profit_target,
                loss_limit=loss_limit,
                risk_reward_ratio=rr_ratio,
                potential_profit_percent=profit_pct,
                potential_loss_percent=loss_pct
            )
            
            logger.info(f"Risk analysis for {ticker}: {lots} lots, RR={rr_ratio:.2f}")
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing trade for {ticker}: {e}")
            return None
    
    @staticmethod
    def analyze_portfolio(
        total_capital: int,
        trades: List[Dict]
    ) -> Optional[Dict]:
        """
        Analyze portfolio risk for multiple trades.
        
        Args:
            total_capital: Total trading capital
            trades: List of trade specs with entry, target, cut_loss
        
        Returns:
            Portfolio analysis
        """
        try:
            analyses = []
            total_allocated = 0
            
            for trade in trades[:RiskManager.MAX_POSITIONS]:
                analysis = RiskManager.analyze_trade(
                    trade["ticker"],
                    total_capital,
                    trade["entry_price"],
                    trade["target_price"],
                    trade["cut_loss_price"]
                )
                if analysis:
                    analyses.append(analysis)
                    total_allocated += analysis.allocated_capital
            
            return {
                "count": len(analyses),
                "analyses": [a.to_dict() for a in analyses],
                "total_allocated": total_allocated,
                "allocation_percent": (total_allocated / total_capital * 100) if total_capital > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error analyzing portfolio: {e}")
            return None
