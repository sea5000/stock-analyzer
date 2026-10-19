"""
Financial market intelligence tools powered by yfinance.
Designed for robust execution with LangChain/LangGraph and local LLM tool calling.
"""

from typing import Any, Dict, List, Optional
import yfinance as yf
from langchain_core.tools import tool


def _sanitize_ticker(ticker: str) -> str:
    """Normalize and clean ticker symbol string."""
    return ticker.strip().upper()


@tool("get_stock_price", description="Fetch the real-time or latest market price for a given stock ticker symbol.")
def get_stock_price(ticker: str) -> Dict[str, Any]:
    """
    Args:
        ticker: The stock ticker symbol (e.g., 'AAPL', 'NVDA', 'MSFT').
    Returns:
        Dictionary containing current price, currency, daily change, and volume.
    """
    symbol = _sanitize_ticker(ticker)
    print(f"[Tool Invoked] get_stock_price({symbol})")
    
    try:
        stock = yf.Ticker(symbol)
        
        # Fast path via fast_info
        fast_info = getattr(stock, "fast_info", None)
        if fast_info:
            price = fast_info.last_price
            prev_close = fast_info.previous_close
            currency = fast_info.currency or "USD"
            if price is not None:
                change = price - prev_close if prev_close else 0.0
                change_pct = (change / prev_close * 100.0) if prev_close else 0.0
                return {
                    "ticker": symbol,
                    "current_price": round(float(price), 2),
                    "previous_close": round(float(prev_close), 2) if prev_close else None,
                    "change": round(float(change), 2),
                    "change_percent": f"{change_pct:+.2f}%",
                    "currency": currency,
                }
        
        # Fallback to history
        hist = stock.history(period="5d")
        if hist.empty:
            return {"error": f"No market data found for ticker '{symbol}'. Please verify the symbol."}
        
        latest_close = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else latest_close
        change = latest_close - prev_close
        change_pct = (change / prev_close * 100.0) if prev_close else 0.0

        return {
            "ticker": symbol,
            "current_price": round(latest_close, 2),
            "previous_close": round(prev_close, 2),
            "change": round(change, 2),
            "change_percent": f"{change_pct:+.2f}%",
            "currency": "USD"
        }
    except Exception as e:
        return {"error": f"Failed to retrieve stock price for '{symbol}': {str(e)}"}


@tool("get_historical_stock_price", description="Retrieve historical daily closing stock prices for a ticker over a given date range or standard period.")
def get_historical_stock_price(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: Optional[str] = "1mo"
) -> Dict[str, Any]:
    """
    Args:
        ticker: The stock ticker symbol (e.g., 'AAPL', 'NVDA').
        start_date: Start date in 'YYYY-MM-DD' format (optional if period is used).
        end_date: End date in 'YYYY-MM-DD' format (optional).
        period: Standard period if dates not specified (e.g., '1mo', '3mo', '6mo', '1y', '5y').
    Returns:
        Dictionary with historical dates and closing prices formatted for charts.
    """
    symbol = _sanitize_ticker(ticker)
    print(f"[Tool Invoked] get_historical_stock_price({symbol}, start={start_date}, end={end_date}, period={period})")

    try:
        stock = yf.Ticker(symbol)
        if start_date:
            hist = stock.history(start=start_date, end=end_date)
        else:
            hist = stock.history(period=period or "1mo")

        if hist.empty:
            return {"error": f"No historical price data found for '{symbol}' in the specified range."}

        # Convert timestamps to ISO string dates and sanitize values for JSON
        prices: List[Dict[str, Any]] = []
        for index, row in hist.iterrows():
            date_str = index.strftime("%Y-%m-%d") if hasattr(index, "strftime") else str(index)[:10]
            prices.append({
                "date": date_str,
                "close": round(float(row["Close"]), 2),
                "open": round(float(row["Open"]), 2) if "Open" in row else None,
                "high": round(float(row["High"]), 2) if "High" in row else None,
                "low": round(float(row["Low"]), 2) if "Low" in row else None,
                "volume": int(row["Volume"]) if "Volume" in row else None,
            })

        min_close = min(p["close"] for p in prices)
        max_close = max(p["close"] for p in prices)
        first_close = prices[0]["close"]
        last_close = prices[-1]["close"]
        total_change_pct = ((last_close - first_close) / first_close * 100.0) if first_close else 0.0

        return {
            "ticker": symbol,
            "data_points": len(prices),
            "start_date": prices[0]["date"],
            "end_date": prices[-1]["date"],
            "first_close": first_close,
            "last_close": last_close,
            "period_return": f"{total_change_pct:+.2f}%",
            "min_close": min_close,
            "max_close": max_close,
            "prices": prices
        }
    except Exception as e:
        return {"error": f"Failed to retrieve history for '{symbol}': {str(e)}"}


@tool("get_balance_sheet", description="Retrieve the company balance sheet and financial health items (cash, debt, assets, liabilities) for a ticker.")
def get_balance_sheet(ticker: str) -> Dict[str, Any]:
    """
    Args:
        ticker: The stock ticker symbol (e.g., 'AAPL', 'MSFT').
    Returns:
        Dictionary of key balance sheet line items formatted as JSON-safe data.
    """
    symbol = _sanitize_ticker(ticker)
    print(f"[Tool Invoked] get_balance_sheet({symbol})")

    try:
        stock = yf.Ticker(symbol)
        bs = stock.balance_sheet

        if bs is None or bs.empty:
            # Fallback to annual balance sheet or quarterly
            bs = stock.quarterly_balance_sheet
            if bs is None or bs.empty:
                return {"error": f"No balance sheet data available for '{symbol}'."}

        # Convert DataFrame index (line items) and column dates to clean string dict
        sanitized_bs: Dict[str, Dict[str, Any]] = {}
        # Select top relevant financial items to keep context clean
        key_items = [
            "Total Assets", "Total Liabilities Net Minority Interest",
            "Stockholders Equity", "Cash And Cash Equivalents",
            "Total Debt", "Net Debt", "Working Capital", "Ordinary Shares Number"
        ]

        for item_idx in bs.index:
            item_name = str(item_idx)
            # Match key items or include all if few
            sanitized_bs[item_name] = {}
            for col in bs.columns:
                date_str = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)[:10]
                val = bs.loc[item_idx, col]
                sanitized_bs[item_name][date_str] = int(val) if isinstance(val, (int, float)) and not (val != val) else str(val)

        return {
            "ticker": symbol,
            "reporting_dates": [
                col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)[:10]
                for col in bs.columns
            ],
            "financial_metrics": sanitized_bs
        }
    except Exception as e:
        return {"error": f"Failed to retrieve balance sheet for '{symbol}': {str(e)}"}


@tool("get_stock_news", description="Retrieve recent financial news, press releases, and articles for a stock ticker symbol.")
def get_stock_news(ticker: str) -> Dict[str, Any]:
    """
    Args:
        ticker: The stock ticker symbol (e.g., 'NVDA', 'TSLA').
    Returns:
        List of recent news stories with titles, publishers, publish time, and links.
    """
    symbol = _sanitize_ticker(ticker)
    print(f"[Tool Invoked] get_stock_news({symbol})")

    try:
        stock = yf.Ticker(symbol)
        raw_news = stock.news

        if not raw_news:
            return {"ticker": symbol, "articles": [], "message": f"No current news found for '{symbol}'."}

        articles: List[Dict[str, Any]] = []
        for item in raw_news[:8]:  # Limit to 8 most relevant
            content = item.get("content", {}) if isinstance(item.get("content"), dict) else item
            title = content.get("title") or item.get("title")
            link = content.get("canonicalUrl", {}).get("url") or item.get("link")
            publisher = content.get("provider", {}).get("displayName") or item.get("publisher")
            pub_date = content.get("pubDate") or item.get("providerPublishTime")

            if title:
                articles.append({
                    "title": title,
                    "publisher": publisher or "Financial News",
                    "published": pub_date,
                    "url": link or ""
                })

        return {
            "ticker": symbol,
            "article_count": len(articles),
            "articles": articles
        }
    except Exception as e:
        return {"error": f"Failed to retrieve news for '{symbol}': {str(e)}"}


@tool("get_key_ratios", description="Fetch key financial valuation ratios and profitability metrics (P/E, PEG, Price-to-Book, Debt-to-Equity, Profit Margins, ROE, Free Cash Flow) for fundamental analysis.")
def get_key_ratios(ticker: str) -> Dict[str, Any]:
    """
    Args:
        ticker: The stock ticker symbol (e.g., 'AAPL', 'MSFT', 'AMZN').
    Returns:
        Valuation multiples, profitability margins, debt metrics, and growth indicators.
    """
    symbol = _sanitize_ticker(ticker)
    print(f"[Tool Invoked] get_key_ratios({symbol})")

    try:
        stock = yf.Ticker(symbol)
        info = stock.info or {}

        def _fmt_pct(val: Optional[float]) -> Optional[str]:
            return f"{val * 100:.2f}%" if val is not None else None

        def _fmt_num(val: Optional[float], decimals: int = 2) -> Optional[float]:
            return round(val, decimals) if val is not None else None

        return {
            "ticker": symbol,
            "company_name": info.get("shortName") or info.get("longName"),
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "valuation_multiples": {
                "trailing_pe": _fmt_num(info.get("trailingPE")),
                "forward_pe": _fmt_num(info.get("forwardPE")),
                "peg_ratio": _fmt_num(info.get("pegRatio")),
                "price_to_book": _fmt_num(info.get("priceToBook")),
                "price_to_sales": _fmt_num(info.get("priceToSalesTrailing12Months")),
                "enterprise_to_ebitda": _fmt_num(info.get("enterpriseToEbitda")),
            },
            "profitability_and_returns": {
                "profit_margins": _fmt_pct(info.get("profitMargins")),
                "operating_margins": _fmt_pct(info.get("operatingMargins")),
                "return_on_equity_roe": _fmt_pct(info.get("returnOnEquity")),
                "return_on_assets_roa": _fmt_pct(info.get("returnOnAssets")),
            },
            "financial_health": {
                "total_debt": info.get("totalDebt"),
                "debt_to_equity": _fmt_num(info.get("debtToEquity")),
                "current_ratio": _fmt_num(info.get("currentRatio")),
                "free_cashflow": info.get("freeCashflow"),
            },
            "dividends": {
                "dividend_yield": _fmt_pct(info.get("dividendYield")),
                "payout_ratio": _fmt_pct(info.get("payoutRatio")),
            }
        }
    except Exception as e:
        return {"error": f"Failed to retrieve key ratios for '{symbol}': {str(e)}"}


@tool("get_analyst_recommendations", description="Fetch Wall Street analyst consensus ratings, price targets (mean, high, low), and recommendation trends for a stock.")
def get_analyst_recommendations(ticker: str) -> Dict[str, Any]:
    """
    Args:
        ticker: The stock ticker symbol (e.g., 'NVDA', 'GOOGL').
    Returns:
        Analyst price target range, consensus rating, and buy/hold/sell breakdown.
    """
    symbol = _sanitize_ticker(ticker)
    print(f"[Tool Invoked] get_analyst_recommendations({symbol})")

    try:
        stock = yf.Ticker(symbol)
        info = stock.info or {}

        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        target_mean = info.get("targetMeanPrice")
        target_high = info.get("targetHighPrice")
        target_low = info.get("targetLowPrice")
        
        upside_pct = None
        if current_price and target_mean:
            upside_pct = round(((target_mean - current_price) / current_price) * 100.0, 2)

        return {
            "ticker": symbol,
            "current_price": current_price,
            "consensus_rating": info.get("recommendationKey", "N/A").upper(),
            "number_of_analysts": info.get("numberOfAnalystOpinions"),
            "price_targets": {
                "target_mean": target_mean,
                "target_high": target_high,
                "target_low": target_low,
                "potential_upside_percent": f"{upside_pct:+0.2f}%" if upside_pct is not None else None
            },
            "target_median": info.get("targetMedianPrice")
        }
    except Exception as e:
        return {"error": f"Failed to retrieve analyst recommendations for '{symbol}': {str(e)}"}


@tool("get_company_profile", description="Retrieve company background, sector, industry, key officers, market capitalization, and business model description.")
def get_company_profile(ticker: str) -> Dict[str, Any]:
    """
    Args:
        ticker: The stock ticker symbol (e.g., 'AAPL', 'TSLA').
    Returns:
        Company profile, sector, industry classification, website, and business overview.
    """
    symbol = _sanitize_ticker(ticker)
    print(f"[Tool Invoked] get_company_profile({symbol})")

    try:
        stock = yf.Ticker(symbol)
        info = stock.info or {}

        return {
            "ticker": symbol,
            "company_name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "country": info.get("country"),
            "website": info.get("website"),
            "full_time_employees": info.get("fullTimeEmployees"),
            "market_cap": info.get("marketCap"),
            "business_summary": info.get("longBusinessSummary", "No summary available.")
        }
    except Exception as e:
        return {"error": f"Failed to retrieve company profile for '{symbol}': {str(e)}"}


ALL_MARKET_TOOLS = [
    get_stock_price,
    get_historical_stock_price,
    get_balance_sheet,
    get_stock_news,
    get_key_ratios,
    get_analyst_recommendations,
    get_company_profile,
]
