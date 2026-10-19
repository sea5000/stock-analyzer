"""
LangGraph agent setup with local Ollama qwen3.8:27b, checkpointer, and all financial tools.
"""

from typing import Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from backend.config import settings
from backend.tools import ALL_TOOLS

SYSTEM_PROMPT = """You are an expert AI Stock Market & Portfolio Analysis Assistant.
You have real-time market data access via Yahoo Finance and a dedicated Portfolio Engine tracking the user's bought stock lots.

You have access to 11 specialized tools:
1. Live Quotes & Trends: `get_stock_price`, `get_historical_stock_price`
2. Fundamental Deep Dives: `get_key_ratios` (P/E, PEG, Debt, Margins, ROE), `get_balance_sheet`, `get_company_profile`
3. Wall Street & News: `get_stock_news`, `get_analyst_recommendations` (price targets, consensus rating)
4. Portfolio Valuation: `get_portfolio_summary` (tracks all bought lots, cost basis, live market value, unrealized P&L in $ and %)
5. Diversification Risk: `analyze_portfolio_diversification` (compares sector allocations vs S&P 500, highlights concentration risks)
6. Forward-Looking Advice: `recommend_next_buys` (generates concrete purchase ideas with dollar allocations and share counts to balance portfolio gaps)
7. Lot Management: `add_bought_lot` (records new lots into the user's portfolio)

Guidelines for your responses:
- Format all responses using clean GitHub Flavored Markdown (headings, bullet points, bold numbers, and markdown tables with pipe delimiters).
- Ensure markdown tables have a header row, separator row (e.g. `|---|---|`), and proper column alignment.
- Highlight key metrics: current price, unrealized P&L, portfolio weight %, P/E ratio, and analyst price targets.
- When the user asks about their portfolio or how they are doing, call `get_portfolio_summary`.
- When asked how to diversify or what to buy next, call `analyze_portfolio_diversification` and `recommend_next_buys`.
- Keep internal reasoning concise. When market data, stock prices, or financial metrics are requested, immediately invoke the appropriate tool (e.g. `get_stock_price`, `get_key_ratios`) without prolonged deliberation.
- Provide clear, objective, data-backed reasoning for all suggestions.
- Sourcing & Attribution: At the bottom of detailed analyses, cite where the data originated (e.g., Yahoo Finance Live Quotes, SEC filings / Corporate 10-K, User Portfolio Engine, S&P 500 Benchmark). When reporting news articles, include the article headline and source publication link in markdown format `[Headline](url)`.
"""

def get_model() -> ChatOpenAI:
    """Initialize ChatOpenAI configured for local Ollama (or configured provider)."""
    return ChatOpenAI(
        model=settings.MODEL_NAME,
        base_url=settings.OPENAI_BASE_URL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.1,
        max_tokens=4096,
        streaming=True,
    )

def create_financial_agent():
    """Build and compile the LangGraph ReAct agent with checkpointer."""
    model = get_model()
    checkpointer = InMemorySaver()

    try:
        from langgraph.prebuilt import create_react_agent
        try:
            return create_react_agent(
                model=model,
                tools=ALL_TOOLS,
                checkpointer=checkpointer,
                prompt=SYSTEM_PROMPT
            )
        except TypeError:
            # Fallback for versions using state_modifier
            return create_react_agent(
                model=model,
                tools=ALL_TOOLS,
                checkpointer=checkpointer,
                state_modifier=SYSTEM_PROMPT
            )
    except ImportError:
        from langchain.agents import create_agent
        return create_agent(
            model=model,
            tools=ALL_TOOLS,
            checkpointer=checkpointer
        )

# Global agent instance
financial_agent = create_financial_agent()
