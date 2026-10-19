"""
Pydantic data models for stock portfolio lots, positions, and analytics.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
from datetime import date


class PortfolioLot(BaseModel):
    """Represents a specific bought lot of a stock."""
    lot_id: str = Field(default_factory=lambda: f"lot_{uuid.uuid4().hex[:8]}")
    ticker: str
    shares: float = Field(gt=0, description="Number of shares bought")
    buy_price: float = Field(ge=0, description="Cost basis price per share at purchase")
    buy_date: str = Field(default_factory=lambda: date.today().isoformat(), description="Date in YYYY-MM-DD format")
    account_type: str = Field(default="Taxable", description="e.g., Taxable, Roth IRA, 401k, Crypto")
    notes: Optional[str] = Field(default="", description="Optional purchase thesis or notes")

    @property
    def total_cost(self) -> float:
        return round(self.shares * self.buy_price, 2)


class PositionSummary(BaseModel):
    """Aggregated summary of all lots for a single stock ticker."""
    ticker: str
    total_shares: float
    average_buy_price: float
    total_cost: float
    current_price: float
    current_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: str
    portfolio_weight_percent: str
    sector: str = "Unknown"
    industry: str = "Unknown"
    lot_count: int
    lots: List[PortfolioLot] = []


class PortfolioReport(BaseModel):
    """Comprehensive portfolio analytics report."""
    total_invested_cost: float
    current_portfolio_value: float
    total_unrealized_pnl: float
    total_unrealized_pnl_percent: str
    position_count: int
    total_lot_count: int
    positions: List[PositionSummary]
    sector_breakdown: Dict[str, Dict[str, Any]]
    concentration_risk: Dict[str, Any]
    last_updated: str
