"""
Portfolio management and forward-looking rebalancing tools for LangGraph and Ollama.
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool
from backend.portfolio.analytics import (
    compute_portfolio_report,
    analyze_diversification_gaps,
    recommend_rebalancing_buys,
)
from backend.portfolio.storage import add_lot, clear_lots, load_lots


@tool("get_portfolio_summary", description="Retrieve the user's current stock portfolio summary, total invested cost, current live market value, unrealized profit/loss ($ and %), and breakdown of all positions.")
def get_portfolio_summary() -> Dict[str, Any]:
    """
    Returns:
        Aggregated portfolio metrics, total P&L, position breakdown, and concentration risk.
    """
    print("[Tool Invoked] get_portfolio_summary()")
    try:
        report = compute_portfolio_report()
        return report
    except Exception as e:
        return {"error": f"Failed to compute portfolio summary: {str(e)}"}


@tool("analyze_portfolio_diversification", description="Analyze the user's current portfolio sector diversification, highlight overweight tech exposure or concentration risks, and identify missing or underweight defensive sectors.")
def analyze_portfolio_diversification() -> Dict[str, Any]:
    """
    Returns:
        Overweight and underweight sectors compared to market benchmarks, and asset concentration warnings.
    """
    print("[Tool Invoked] analyze_portfolio_diversification()")
    try:
        report = compute_portfolio_report()
        gaps = analyze_diversification_gaps(report)
        return {
            "portfolio_value": report.get("current_portfolio_value"),
            "sector_breakdown": report.get("sector_breakdown"),
            "concentration_risk": report.get("concentration_risk"),
            "diversification_audit": gaps
        }
    except Exception as e:
        return {"error": f"Failed to analyze portfolio diversification: {str(e)}"}


@tool("recommend_next_buys", description="Generate forward-looking rebalancing and diversification recommendations. Recommends specific high-quality stocks to buy next, estimated shares, and dollar allocations to fix portfolio vulnerabilities.")
def recommend_next_buys(
    budget: float = 2000.0,
    focus: Optional[str] = "diversify"
) -> Dict[str, Any]:
    """
    Args:
        budget: Cash amount in USD available to deploy (default: 2000.0).
        focus: Strategy focus (e.g. 'diversify', 'growth', 'dividend_defensive').
    Returns:
        Concrete purchase recommendations with target allocations, valuation ratios, and analyst upside targets.
    """
    print(f"[Tool Invoked] recommend_next_buys(budget={budget}, focus={focus})")
    try:
        recommendations = recommend_rebalancing_buys(budget=budget, focus=focus or "diversify")
        return recommendations
    except Exception as e:
        return {"error": f"Failed to generate buy recommendations: {str(e)}"}


@tool("add_bought_lot", description="Record a new bought stock lot into the user's portfolio with ticker, number of shares, purchase price, and date.")
def add_bought_lot(
    ticker: str,
    shares: float,
    buy_price: float,
    buy_date: Optional[str] = None,
    account_type: Optional[str] = "Taxable",
    notes: Optional[str] = ""
) -> Dict[str, Any]:
    """
    Args:
        ticker: The stock ticker symbol (e.g., 'NVDA', 'AAPL').
        shares: Number of shares purchased (e.g., 10.5).
        buy_price: Purchase price per share / cost basis (e.g., 125.00).
        buy_date: Purchase date in 'YYYY-MM-DD' format.
        account_type: Optional account type (e.g. 'Taxable', 'Roth IRA').
        notes: Optional purchase rationale.
    Returns:
        Confirmation of recorded lot and updated portfolio holdings count.
    """
    print(f"[Tool Invoked] add_bought_lot({ticker}, {shares} shares @ ${buy_price})")
    try:
        lot = add_lot(
            ticker=ticker,
            shares=shares,
            buy_price=buy_price,
            buy_date=buy_date,
            account_type=account_type or "Taxable",
            notes=notes or ""
        )
        total_lots = len(load_lots())
        return {
            "status": "success",
            "message": f"Successfully added {shares} shares of {lot.ticker} at ${buy_price:.2f} per share.",
            "lot_id": lot.lot_id,
            "total_lots_in_portfolio": total_lots
        }
    except Exception as e:
        return {"error": f"Failed to add lot: {str(e)}"}


ALL_PORTFOLIO_TOOLS = [
    get_portfolio_summary,
    analyze_portfolio_diversification,
    recommend_next_buys,
    add_bought_lot,
]
