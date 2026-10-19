# Implementation Plan: AI Stock Analysis & Portfolio Assistant (Local AI + Ollama)

## Overview
This project implements an advanced, privacy-first AI stock and portfolio analysis assistant. It evolves the architecture demonstrated in NeuralNine's tutorial (*"Advanced AI Stock Analysis Assistant in Python"* - YouTube `AE_6F8cuXsA`) from a simple quote bot into a full-fledged **Personal AI Portfolio Analyst and Wealth Advisor**.

The system runs on a **local-first AI architecture** using **Ollama** running **`qwen3.8:27b`** (with optional support for Thesys GenUI or other OpenAI-compatible endpoints). It pairs a FastAPI + LangChain/LangGraph backend with a React + TypeScript frontend. It empowers users not only to analyze individual stocks with live Yahoo Finance data, but also to **import bought stock lots, evaluate current portfolio performance, analyze sector diversification, and generate forward-looking rebalancing and "what to buy next" recommendations**.

---

## Why Portfolio & Bought Lots Analysis Fits Perfectly (Not Scope Creep)

Adding portfolio and bought lots analysis is **not scope creep**—it is the natural, high-leverage application of the financial tools we are building:
1. **Tool Synergy:** We already build real-time pricing (`get_stock_price`), fundamentals (`get_key_ratios`), and analyst consensus (`get_analyst_recommendations`). By storing user bought lots, we can instantly enrich raw lot data with live P&L, sector weights, and analyst targets.
2. **Forward-Looking Wealth Intelligence:** Rather than just answering *"What did NVDA do yesterday?"*, the assistant can answer *"You have 62% in semiconductors. To protect against cyclical downturns while maintaining growth, here are 3 undervalued healthcare and consumer staples candidates to buy next with your remaining cash."*
3. **Clean Modular Boundaries:** The portfolio logic is encapsulated in a dedicated `portfolio/` module with a clean JSON/CSV persistence schema, keeping the agent and API clean and decoupled.

---

## Architectural Blueprint

```
                     ┌────────────────────────────────────────────────────────┐
                     │                   Client Browser                       │
                     │  ┌──────────────────────────────────────────────────┐  │
                     │  │        React + TypeScript (Vite on :3000)        │  │
                     │  │   <ThemeProvider mode="dark">                    │  │
                     │  │     - Interactive AI Chat Interface              │  │
                     │  │     - Portfolio CSV/JSON Import & Lots Table     │  │
                     │  │     - Visual Asset Allocation & Sector Breakdown │  │
                     │  └────────────────────────┬─────────────────────────┘  │
                     └───────────────────────────┼────────────────────────────┘
                                                 │
                                                 │ HTTP POST /api/chat
                                                 │ HTTP POST /api/portfolio/import
                                                 │ (Vite Proxy -> :8888)
                                                 ▼
                     ┌────────────────────────────────────────────────────────┐
                     │                   FastAPI Backend                      │
                     │  ┌──────────────────────────────────────────────────┐  │
                     │  │              FastAPI Server (:8888)              │  │
                     │  │  - CORS Middleware (enabled for dev & prod)     │  │
                     │  │  - StreamingResponse (text/event-stream)         │  │
                     │  │  - REST Endpoints: /api/chat, /api/portfolio     │  │
                     │  └────────────────────────┬─────────────────────────┘  │
                     │                           │                            │
                     │  ┌────────────────────────▼─────────────────────────┐  │
                     │  │       LangChain / LangGraph Agent Engine         │  │
                     │  │  - Primary: Local Ollama (qwen3.8:27b)           │  │
                     │  │  - Optional: Thesys GenUI / OpenAI-compatible    │  │
                     │  │  - InMemorySaver Checkpointer (keyed on threadId)│  │
                     │  │  - SSE Token Streaming Generator                 │  │
                     │  └────────────────────────┬─────────────────────────┘  │
                     │                           │                            │
                     │  ┌────────────────────────▼─────────────────────────┐  │
                     │  │                Tools Ecosystem                   │  │
                     │  │  [Market Intelligence Tools (yfinance)]          │  │
                     │  │  - get_stock_price(ticker)                       │  │
                     │  │  - get_historical_stock_price(ticker, start, end)│  │
                     │  │  - get_balance_sheet(ticker)                     │  │
                     │  │  - get_stock_news(ticker)                        │  │
                     │  │  - get_key_ratios(ticker) (P/E, Debt, Margins)   │  │
                     │  │  - get_analyst_recommendations(ticker)           │  │
                     │  │  - get_company_profile(ticker)                   │  │
                     │  │                                                  │  │
                     │  │  [Portfolio & Forward-Looking Tools]             │  │
                     │  │  - get_portfolio_summary() (P&L, weights)        │  │
                     │  │  - analyze_portfolio_diversification() (sectors) │  │
                     │  │  - recommend_next_buys(budget, risk_tolerance)   │  │
                     │  │  - import_bought_lots(lots_data)                 │  │
                     │  └────────────────────────┬─────────────────────────┘  │
                     └───────────────────────────┼────────────────────────────┘
                                                 │
                                                 ▼
                     ┌────────────────────────────────────────────────────────┐
                     │              Local Engine & Data Storage               │
                     │  - Local Ollama Server (http://localhost:11434/v1)     │
                     │    Model: qwen3.8:27b                                  │
                     │  - Portfolio Store (JSON/SQLite in backend/data/)      │
                     │  - Yahoo Finance (yfinance live market data)           │
                     └────────────────────────────────────────────────────────┘
```

---

## Portfolio Engine: Data Model & Forward-Looking Analytics

### 1. Bought Lots Data Model (`PortfolioLot`)
```python
class PortfolioLot:
    lot_id: str             # e.g., "lot_001"
    ticker: str             # e.g., "NVDA"
    shares: float           # e.g., 25.0
    buy_price: float        # e.g., 105.50 (cost basis per share)
    buy_date: str           # e.g., "2024-05-15"
    account_type: str       # "Taxable", "Roth IRA", "401k", "General"
    notes: Optional[str]    # "Dollar cost averaging tranche 1"
```

### 2. Calculated Portfolio Metrics
* **Cost Basis vs. Current Value:** Total invested capital vs. live value from `yfinance`.
* **Unrealized Gain / Loss:** Absolute dollar return and percentage return per lot and aggregated per ticker.
* **Portfolio Concentration:** % weight of each asset and top-3 asset concentration ratio.
* **Sector & Industry Exposure:** Automatic grouping by sector (`Technology`, `Healthcare`, `Financial Services`, `Energy`, `Consumer Defensive`, etc.) to measure exposure vs. S&P 500 benchmarks.

### 3. Forward-Looking Insights & "What to Buy Next"
The `recommend_next_buys` tool performs forward-looking asset evaluation:
1. **Concentration Risk Audit:** Identifies over-concentrated positions (e.g. >30% in a single stock or >50% in tech).
2. **Gap Analysis:** Identifies underweight or missing sectors that provide protective diversification.
3. **Valuation & Analyst Upside Scan:** Compares candidate assets using forward P/E, PEG ratios, and analyst consensus targets from `yfinance`.
4. **Actionable Rebalancing Plan:** Generates concrete allocation ideas (e.g., *"If you have $2,000 to deploy, allocate $1,200 to ABBV [Healthcare, 3.8% dividend, PEG 1.4] and $800 to V [Financials] to reduce your tech concentration from 68% down to 54%"*).

---

## Model Provider Configuration: Local Ollama (`qwen3.8:27b`)

Default configuration in `backend/.env`:
```env
LLM_PROVIDER=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
MODEL_NAME=qwen3.8:27b
PORT=8888
```

The system connects to Ollama's native OpenAI-compatible API endpoint (`/v1`). LangChain's `ChatOpenAI` connects effortlessly to `http://localhost:11434/v1`, using `qwen3.8:27b` with native tool/function calling.

---

## Main Tasks and Objectives

### Objective 1: Backend Foundation & Virtual Environment
Set up `backend/` using standard Python `venv` (`python3 -m venv .venv`), install dependencies, configure `.env` pointing to Ollama `qwen3.8:27b`, and build the base FastAPI server with CORS and health checks.

### Objective 2: Financial Market Data Tools (`yfinance`)
Implement the 7 core market analysis tools (stock price, history, balance sheet, news, key valuation ratios, analyst recommendations, company profile) with robust JSON serialization.

### Objective 3: Portfolio & Bought Lots Engine
Implement the portfolio lot data model, file persistence (JSON/SQLite in `backend/data/`), CSV import parser, and analytics engine (P&L calculations, sector exposure, and forward-looking diversification scanner).

### Objective 4: LangGraph Agent & Chat Streaming Endpoint
Wire `qwen3.8:27b` into the LangGraph agent with both market and portfolio tools, configure memory checkpointing (`InMemorySaver`), and implement the `/api/chat` SSE streaming route.

### Objective 5: Frontend Development (React + TypeScript + Vite)
Build the frontend chat interface, add portfolio CSV upload and lots overview tab, configure Vite proxy to `:8888`, and ensure responsive dark mode.

### Objective 6: End-to-End Verification, Documentation & Developer Experience
Test local Ollama interaction, test portfolio import and forward-looking diversification advice, write comprehensive `README.md` and startup scripts.

### Objective 7: Local Git Repository & Chat UX Polishing
- Initialized local git repository on branch `main` with comprehensive `.gitignore`.
- Created structured local commits tracking backend architecture, frontend dashboard, and UX polishes.
- Rewrote markdown parser (`MarkdownRenderer.tsx`) with multi-line fenced code block support, code copy button, collapsible model reasoning `<think>` block, and robust GFM tables.
- Added message-level Copy button with visual feedback.
- Added live Sourcing & Attribution pills and external citation links for financial market data, corporate SEC filings, user portfolio lots, and financial news.
