"""
Portfolio performance, sector allocation, and forward-looking rebalancing engine.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import time
import yfinance as yf
from backend.portfolio.models import PortfolioLot, PositionSummary, PortfolioReport
from backend.portfolio.storage import load_lots


# Benchmark sector weights (approximate S&P 500 weights for reference)
BENCHMARK_SECTOR_WEIGHTS = {
    "Technology": 31.0,
    "Financial Services": 13.0,
    "Healthcare": 12.0,
    "Consumer Cyclical": 10.0,
    "Communication Services": 9.0,
    "Industrials": 8.5,
    "Consumer Defensive": 6.0,
    "Energy": 4.0,
    "Real Estate": 2.5,
    "Utilities": 2.5,
    "Basic Materials": 2.0,
}

# High-quality candidates across sectors for diversification screening
SECTOR_DIVERSIFICATION_CANDIDATES = {
    "Healthcare": ["ABBV", "JNJ", "UNH", "PFE"],
    "Financial Services": ["JPM", "V", "MA", "BRK-B"],
    "Consumer Defensive": ["PG", "KO", "PEP", "COST"],
    "Energy": ["XOM", "CVX", "COP"],
    "Industrials": ["CAT", "HON", "GE", "UNP"],
    "Technology": ["MSFT", "AAPL", "GOOGL", "NVDA"],
    "Communication Services": ["GOOGL", "META", "DIS"],
}

# Known ETF / stock classifications to eliminate redundant slow API calls and correctly classify funds
KNOWN_CLASSIFICATIONS: Dict[str, Dict[str, str]] = {
    # Core ETFs
    "SPY": {"sector": "Broad Market ETF", "industry": "S&P 500 Index"},
    "VOO": {"sector": "Broad Market ETF", "industry": "S&P 500 Index"},
    "VTI": {"sector": "Broad Market ETF", "industry": "Total US Stock Market"},
    "IVOG": {"sector": "Broad Market ETF", "industry": "S&P Mid-Cap 400 Growth"},
    "VOOG": {"sector": "Broad Market ETF", "industry": "S&P 500 Growth"},
    "VTWO": {"sector": "Broad Market ETF", "industry": "Russell 2000 Small-Cap"},
    "SPXL": {"sector": "Broad Market ETF", "industry": "3x Leveraged S&P 500 Bull"},
    "SPYD": {"sector": "Dividend / Income ETF", "industry": "S&P 500 High Dividend"},
    "IEFA": {"sector": "International ETF", "industry": "MSCI EAFE Developed Markets"},
    "VXUS": {"sector": "International ETF", "industry": "Total International Stock"},
    "VGT": {"sector": "Technology", "industry": "Technology Sector ETF"},
    "ITA": {"sector": "Industrials", "industry": "Aerospace & Defense ETF"},
    "QQQ": {"sector": "Technology", "industry": "Nasdaq-100 Index ETF"},
    "XLF": {"sector": "Financial Services", "industry": "Financial Sector ETF"},
    "XLV": {"sector": "Healthcare", "industry": "Healthcare Sector ETF"},
    "XLE": {"sector": "Energy", "industry": "Energy Sector ETF"},
    "XLI": {"sector": "Industrials", "industry": "Industrial Sector ETF"},

    # User Holdings & Common Equities
    "AAL": {"sector": "Industrials", "industry": "Airlines"},
    "AMD": {"sector": "Technology", "industry": "Semiconductors"},
    "LAC": {"sector": "Basic Materials", "industry": "Lithium & Chemicals"},
    "LMT": {"sector": "Industrials", "industry": "Aerospace & Defense"},
    "MSFT": {"sector": "Technology", "industry": "Software - Infrastructure"},
    "NVDA": {"sector": "Technology", "industry": "Semiconductors"},
    "T": {"sector": "Communication Services", "industry": "Telecom Services"},
    "TSLA": {"sector": "Consumer Cyclical", "industry": "Auto Manufacturers"},
    "AAPL": {"sector": "Technology", "industry": "Consumer Electronics"},
    "AMZN": {"sector": "Consumer Cyclical", "industry": "Internet Retail"},
    "GOOGL": {"sector": "Communication Services", "industry": "Internet Content"},
    "GOOG": {"sector": "Communication Services", "industry": "Internet Content"},
    "META": {"sector": "Communication Services", "industry": "Internet Content"},
    "AVGO": {"sector": "Technology", "industry": "Semiconductors"},
    "JNJ": {"sector": "Healthcare", "industry": "Pharmaceuticals"},
    "JPM": {"sector": "Financial Services", "industry": "Diversified Banking"},
    "V": {"sector": "Financial Services", "industry": "Payment Services"},
    "MA": {"sector": "Financial Services", "industry": "Payment Services"},
    "PG": {"sector": "Consumer Defensive", "industry": "Household Products"},
    "KO": {"sector": "Consumer Defensive", "industry": "Beverages"},
    "PEP": {"sector": "Consumer Defensive", "industry": "Beverages"},
    "COST": {"sector": "Consumer Defensive", "industry": "Discount Stores"},
    "WMT": {"sector": "Consumer Defensive", "industry": "Discount Stores"},
    "XOM": {"sector": "Energy", "industry": "Oil & Gas"},
    "CVX": {"sector": "Energy", "industry": "Oil & Gas"},
    "UNH": {"sector": "Healthcare", "industry": "Managed Healthcare"},
    "PFE": {"sector": "Healthcare", "industry": "Pharmaceuticals"},
    "ABBV": {"sector": "Healthcare", "industry": "Pharmaceuticals"},
    "CAT": {"sector": "Industrials", "industry": "Heavy Machinery"},
    "GE": {"sector": "Industrials", "industry": "Aerospace"},
    "HON": {"sector": "Industrials", "industry": "Conglomerates"},
    "UNP": {"sector": "Industrials", "industry": "Railroads"},
    "DIS": {"sector": "Communication Services", "industry": "Entertainment"},
    "NFLX": {"sector": "Communication Services", "industry": "Entertainment"},
    "BAC": {"sector": "Financial Services", "industry": "Banking"},
    "BRK-B": {"sector": "Financial Services", "industry": "Conglomerates"},
}

_METADATA_CACHE: Dict[str, Dict[str, str]] = dict(KNOWN_CLASSIFICATIONS)
_PRICE_CACHE: Dict[str, Dict[str, Any]] = {}
_REPORT_CACHE: Dict[str, Any] = {"report": None, "timestamp": 0.0, "lots_fingerprint": ""}


def invalidate_portfolio_cache() -> None:
    """Invalidate cached report so next access computes fresh valuation."""
    global _REPORT_CACHE
    _REPORT_CACHE = {"report": None, "timestamp": 0.0, "lots_fingerprint": ""}


def get_ticker_live_data(symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Retrieves live price and sector/industry metadata with caching.
    Prices cached for 60 seconds; metadata cached permanently in memory.
    """
    now = time.time()
    cached_price = _PRICE_CACHE.get(symbol)
    price: Optional[float] = None

    if not force_refresh and cached_price and (now - cached_price["timestamp"] < 60.0):
        price = cached_price["price"]

    # Check metadata cache
    meta = _METADATA_CACHE.get(symbol)
    sector = meta.get("sector") if meta else None
    industry = meta.get("industry") if meta else None

    # If price already cached and metadata known, return immediately (0ms)
    if price is not None and sector is not None:
        return {
            "price": price,
            "sector": sector,
            "industry": industry,
        }

    try:
        stock = yf.Ticker(symbol)
        if price is None:
            fast_info = getattr(stock, "fast_info", None)
            if fast_info and fast_info.last_price is not None:
                price = float(fast_info.last_price)
            else:
                hist = stock.history(period="2d")
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])

        if sector is None or industry is None:
            info = stock.info or {}
            quote_type = info.get("quoteType", "")
            if quote_type == "ETF":
                category = info.get("category") or "Exchange Traded Fund"
                sector = "Broad Market ETF" if any(w in category.lower() for w in ["large", "blend", "total", "cap"]) else (info.get("sector") or "ETF")
                industry = category
            else:
                sector = info.get("sector") or "Unknown"
                industry = info.get("industry") or "Unknown"

            _METADATA_CACHE[symbol] = {"sector": sector, "industry": industry}

    except Exception as e:
        print(f"[Analytics Warning] Could not fetch live quote for {symbol}: {e}")

    if price is None or price <= 0:
        price = cached_price["price"] if cached_price else 0.0

    _PRICE_CACHE[symbol] = {"price": price, "timestamp": now}

    return {
        "price": price,
        "sector": sector or "Unknown",
        "industry": industry or "Unknown",
    }


def compute_portfolio_report(
    lots: Optional[List[PortfolioLot]] = None,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Computes a full financial valuation of the portfolio using live prices from yfinance.
    Aggregates bought lots into positions, calculates unrealized P&L, sector weights, and concentration.
    Uses an in-memory cache to ensure near-instant responses.
    """
    if lots is None:
        lots = load_lots()

    if not lots:
        return {
            "message": "Your portfolio is currently empty. Import a CSV or add lots to see your portfolio analysis.",
            "total_invested_cost": 0.0,
            "current_portfolio_value": 0.0,
            "total_unrealized_pnl": 0.0,
            "total_unrealized_pnl_percent": "0.00%",
            "positions": [],
            "sector_breakdown": {},
            "concentration_risk": {"status": "No holdings"},
        }

    now = time.time()
    lots_fingerprint = f"{len(lots)}:" + ",".join(f"{l.lot_id}:{l.shares}:{l.buy_price}" for l in lots)
    if (
        not force_refresh
        and _REPORT_CACHE.get("report") is not None
        and _REPORT_CACHE.get("lots_fingerprint") == lots_fingerprint
        and (now - _REPORT_CACHE.get("timestamp", 0.0) < 60.0)
    ):
        return _REPORT_CACHE["report"]

    # Group lots by ticker
    lots_by_ticker: Dict[str, List[PortfolioLot]] = {}
    for lot in lots:
        lots_by_ticker.setdefault(lot.ticker, []).append(lot)

    positions: List[Dict[str, Any]] = []
    total_cost = 0.0
    total_value = 0.0

    # Fetch quotes and metadata (using fast cache)
    for symbol, ticker_lots in lots_by_ticker.items():
        total_shares = sum(lot.shares for lot in ticker_lots)
        lot_cost = sum(lot.shares * lot.buy_price for lot in ticker_lots)
        avg_price = lot_cost / total_shares if total_shares > 0 else 0.0

        live_data = get_ticker_live_data(symbol, force_refresh=force_refresh)
        current_price = live_data["price"] if live_data["price"] > 0 else avg_price
        sector = live_data["sector"]
        industry = live_data["industry"]

        position_value = round(total_shares * current_price, 2)
        unrealized_pnl = round(position_value - lot_cost, 2)
        unrealized_pct = ((position_value - lot_cost) / lot_cost * 100.0) if lot_cost > 0 else 0.0

        total_cost += lot_cost
        total_value += position_value

        positions.append({
            "ticker": symbol,
            "total_shares": round(total_shares, 4),
            "average_buy_price": round(avg_price, 2),
            "total_cost": round(lot_cost, 2),
            "current_price": round(current_price, 2),
            "current_value": position_value,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_percent": f"{unrealized_pct:+.2f}%",
            "sector": sector,
            "industry": industry,
            "lot_count": len(ticker_lots),
            "lots": [l.model_dump() for l in ticker_lots]
        })

    # Compute portfolio weights and sector allocations
    sector_breakdown: Dict[str, Dict[str, Any]] = {}
    for p in positions:
        weight = (p["current_value"] / total_value * 100.0) if total_value > 0 else 0.0
        p["portfolio_weight_percent"] = f"{weight:.2f}%"
        p["portfolio_weight_raw"] = round(weight, 2)

        sector = p["sector"]
        if sector not in sector_breakdown:
            sector_breakdown[sector] = {"value": 0.0, "weight_percent": 0.0, "tickers": []}
        sector_breakdown[sector]["value"] = round(sector_breakdown[sector]["value"] + p["current_value"], 2)
        sector_breakdown[sector]["tickers"].append(p["ticker"])

    for s_name, s_data in sector_breakdown.items():
        s_weight = (s_data["value"] / total_value * 100.0) if total_value > 0 else 0.0
        s_data["weight_percent"] = f"{s_weight:.2f}%"
        s_data["weight_raw"] = round(s_weight, 2)

    # Sort positions by value descending
    positions.sort(key=lambda x: x["current_value"], reverse=True)

    # Concentration analysis
    top_3_weight = sum(p["portfolio_weight_raw"] for p in positions[:3]) if positions else 0.0
    top_1_weight = positions[0]["portfolio_weight_raw"] if positions else 0.0

    if top_1_weight > 35.0:
        conc_status = f"HIGH RISK: Top holding ({positions[0]['ticker']}) represents {top_1_weight:.1f}% of your portfolio."
    elif top_3_weight > 60.0:
        conc_status = f"MODERATE RISK: Top 3 holdings represent {top_3_weight:.1f}% of your total portfolio."
    else:
        conc_status = "HEALTHY: Portfolio is well-distributed across multiple positions."

    total_unrealized_pnl = round(total_value - total_cost, 2)
    total_unrealized_pct = ((total_value - total_cost) / total_cost * 100.0) if total_cost > 0 else 0.0

    report_data = {
        "total_invested_cost": round(total_cost, 2),
        "current_portfolio_value": round(total_value, 2),
        "total_unrealized_pnl": total_unrealized_pnl,
        "total_unrealized_pnl_percent": f"{total_unrealized_pct:+.2f}%",
        "position_count": len(positions),
        "total_lot_count": len(lots),
        "positions": positions,
        "sector_breakdown": sector_breakdown,
        "concentration_risk": {
            "top_1_holding": positions[0]["ticker"] if positions else None,
            "top_1_weight": f"{top_1_weight:.2f}%",
            "top_3_weight": f"{top_3_weight:.2f}%",
            "status": conc_status
        },
        "last_updated": datetime.now().isoformat()
    }

    _REPORT_CACHE["report"] = report_data
    _REPORT_CACHE["timestamp"] = now
    _REPORT_CACHE["lots_fingerprint"] = lots_fingerprint

    return report_data


def analyze_diversification_gaps(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates current sector allocations against S&P 500 benchmarks.
    Identifies over-concentrations and underweight/missing defensive sectors.
    """
    sector_breakdown = report.get("sector_breakdown", {})
    total_value = report.get("current_portfolio_value", 0.0)

    overweight_sectors: List[Dict[str, Any]] = []
    underweight_or_missing_sectors: List[Dict[str, Any]] = []

    for b_sector, benchmark_pct in BENCHMARK_SECTOR_WEIGHTS.items():
        actual_info = sector_breakdown.get(b_sector, {})
        actual_pct = actual_info.get("weight_raw", 0.0)
        diff = actual_pct - benchmark_pct

        if diff > 15.0:
            overweight_sectors.append({
                "sector": b_sector,
                "current_weight": f"{actual_pct:.1f}%",
                "benchmark_weight": f"{benchmark_pct:.1f}%",
                "variance": f"+{diff:.1f}%",
                "tickers_held": actual_info.get("tickers", [])
            })
        elif diff < -5.0 or actual_pct == 0.0:
            underweight_or_missing_sectors.append({
                "sector": b_sector,
                "current_weight": f"{actual_pct:.1f}%",
                "benchmark_weight": f"{benchmark_pct:.1f}%",
                "deficit": f"{diff:.1f}%",
                "status": "Missing entirely" if actual_pct == 0.0 else "Underweight"
            })

    # Sort deficits descending
    underweight_or_missing_sectors.sort(key=lambda x: float(x["deficit"].replace("%", "")))

    return {
        "portfolio_value": total_value,
        "overweight_sectors": overweight_sectors,
        "underweight_or_missing_sectors": underweight_or_missing_sectors,
        "summary": (
            f"Found {len(overweight_sectors)} overweight sectors and "
            f"{len(underweight_or_missing_sectors)} underweight/missing sectors."
        )
    }


def recommend_rebalancing_buys(
    budget: float = 2000.0,
    focus: str = "diversify"
) -> Dict[str, Any]:
    """
    Forward-looking rebalancing engine:
    1. Evaluates current portfolio gaps.
    2. Screens high-quality candidate stocks in underrepresented sectors.
    3. Fetches live valuation (P/E, PEG) and analyst upside targets from yfinance.
    4. Proposes concrete dollar allocation suggestions to balance risk.
    """
    report = compute_portfolio_report()
    gaps = analyze_diversification_gaps(report)

    target_sectors = [s["sector"] for s in gaps["underweight_or_missing_sectors"][:3]]
    if not target_sectors:
        target_sectors = ["Healthcare", "Financial Services", "Consumer Defensive"]

    proposals: List[Dict[str, Any]] = []
    budget_remaining = budget

    for sector in target_sectors:
        candidates = SECTOR_DIVERSIFICATION_CANDIDATES.get(sector, [])
        best_candidate = None

        for ticker in candidates:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info or {}
                cur_price = info.get("currentPrice") or info.get("regularMarketPrice")
                target_mean = info.get("targetMeanPrice")
                peg = info.get("pegRatio")
                pe = info.get("trailingPE") or info.get("forwardPE")
                div_yield = info.get("dividendYield")

                if cur_price:
                    upside = round(((target_mean - cur_price) / cur_price) * 100.0, 1) if target_mean else 0.0
                    best_candidate = {
                        "ticker": ticker,
                        "company_name": info.get("shortName") or ticker,
                        "sector": sector,
                        "current_price": round(float(cur_price), 2),
                        "analyst_target": target_mean,
                        "analyst_upside": f"{upside:+0.1f}%",
                        "pe_ratio": round(pe, 1) if pe else None,
                        "peg_ratio": round(peg, 2) if peg else None,
                        "dividend_yield": f"{div_yield * 100:.2f}%" if div_yield else "0.00%",
                        "thesis": f"Provides immediate exposure to {sector} with solid fundamentals."
                    }
                    break
            except Exception:
                continue

        if best_candidate and budget_remaining > 0:
            alloc_amt = min(round(budget / len(target_sectors), 2), budget_remaining)
            est_shares = round(alloc_amt / best_candidate["current_price"], 2) if best_candidate["current_price"] > 0 else 0
            best_candidate["recommended_allocation_usd"] = alloc_amt
            best_candidate["estimated_shares"] = est_shares
            proposals.append(best_candidate)
            budget_remaining -= alloc_amt

    return {
        "budget_total": budget,
        "unallocated_cash": round(budget_remaining, 2),
        "target_sectors_addressed": target_sectors,
        "recommendations": proposals,
        "rationale": (
            f"Deploying ${budget:,.2f} across {len(proposals)} high-quality companies in "
            f"{', '.join(target_sectors)} will significantly reduce portfolio concentration "
            "and establish defensive stability without sacrificing capital growth."
        )
    }
