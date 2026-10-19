# AI Stock & Portfolio Analysis Assistant (Local AI + Ollama)

An advanced, privacy-first **AI Stock Market Analyst and Wealth Management Assistant** powered by local Large Language Models (**Ollama** with **`qwen3.8:27b`**) and **Yahoo Finance (`yfinance`)**.

Inspired by NeuralNine's tutorial (*"Advanced AI Stock Analysis Assistant in Python"* - [YouTube: AE_6F8cuXsA](https://www.youtube.com/watch?v=AE_6F8cuXsA)), this project expands the baseline single-ticker chatbot into a complete **Portfolio Intelligence & Forward-Looking Diversification Platform**.

---

## Key Capabilities

* ⚡ **100% Local AI Execution**: Runs entirely on your machine via Ollama (`qwen3.8:27b` by default). Zero cloud subscription fees and complete privacy for your financial portfolio.
* 📊 **Real-Time Market Intelligence**: Fetches live quotes, 5-year historical trend data, balance sheet fundamentals, and current news using `yfinance`.
* 🔍 **Deep Fundamental Analysis**: Evaluates Trailing & Forward P/E, PEG ratios, Price-to-Book, Debt-to-Equity, Profit Margins, ROE, and Free Cash Flow.
* 🎯 **Wall Street Consensus & Targets**: Gathers analyst target ranges (mean, high, low) and buy/hold/sell consensus ratings to assess potential upside.
* 💼 **Portfolio & Bought Lots Management**:
  * Import lots directly via standard brokerage **CSV upload** or through conversational prompts (*"I bought 15 shares of NVDA at $118 on Oct 5"*).
  * Tracks individual purchase lots, cost basis, current live value, and unrealized profit/loss ($ and %).
* 🧭 **Forward-Looking Diversification & Rebalancing Engine**:
  * Audits sector allocations (% Technology, % Healthcare, % Financials, etc.) against S&P 500 benchmarks.
  * Identifies dangerous concentration risks (e.g., >50% tech exposure).
  * Suggests actionable **"What to Buy Next"** plans: screens high-quality stocks in missing or underweight sectors, calculates target dollar allocations, and estimates shares to buy with available cash.

---

## Architectural Blueprint

```
                      ┌────────────────────────────────────────────────────────┐
                      │                   Client Browser                       │
                      │  ┌──────────────────────────────────────────────────┐  │
                      │  │        React + TypeScript (Vite on :3000)        │  │
                      │  │   - AI Financial Advisor Chat (SSE Streaming)    │  │
                      │  │   - Portfolio & Bought Lots Manager              │  │
                      │  │   - Sector Exposure Bars & Risk Indicators       │  │
                      │  └────────────────────────┬─────────────────────────┘  │
                      └───────────────────────────┼────────────────────────────┘
                                                  │
                                                  │ HTTP POST /api/chat
                                                  │ HTTP POST /api/portfolio/*
                                                  │ (Vite Proxy -> :8888)
                                                  ▼
                      ┌────────────────────────────────────────────────────────┐
                      │                   FastAPI Backend                      │
                      │  ┌──────────────────────────────────────────────────┐  │
                      │  │              FastAPI Server (:8888)              │  │
                      │  │  - CORS Middleware                              │  │
                      │  │  - StreamingResponse (text/event-stream)         │  │
                      │  │  - REST Endpoints (/api/portfolio)               │  │
                      │  └────────────────────────┬─────────────────────────┘  │
                      │                           │                            │
                      │  ┌────────────────────────▼─────────────────────────┐  │
                      │  │       LangGraph Agent Engine (ReAct)             │  │
                      │  │  - InMemorySaver Checkpointer (threadId context) │  │
                      │  │  - ChatOpenAI client -> Local Ollama Endpoint    │  │
                      │  └────────────────────────┬─────────────────────────┘  │
                      │                           │                            │
                      │  ┌────────────────────────▼─────────────────────────┐  │
                      │  │                Tools Ecosystem                   │  │
                      │  │  [Market Tools]                                  │  │
                      │  │  - get_stock_price                               │  │
                      │  │  - get_historical_stock_price                    │  │
                      │  │  - get_balance_sheet                             │  │
                      │  │  - get_stock_news                                │  │
                      │  │  - get_key_ratios                                │  │
                      │  │  - get_analyst_recommendations                   │  │
                      │  │  - get_company_profile                           │  │
                      │  │  [Portfolio Tools]                               │  │
                      │  │  - get_portfolio_summary                         │  │
                      │  │  - analyze_portfolio_diversification             │  │
                      │  │  - recommend_next_buys                           │  │
                      │  │  - add_bought_lot                                │  │
                      │  └────────────────────────┬─────────────────────────┘  │
                      └───────────────────────────┼────────────────────────────┘
                                                  │
                                                  ▼
                      ┌────────────────────────────────────────────────────────┐
                      │              Local Engine & Data Storage               │
                      │  - Local Ollama Server (http://localhost:11434/v1)     │
                      │    Active Model: qwen3.8:27b (or any local LLM)        │
                      │  - Portfolio Store (backend/data/portfolio.json)       │
                      │  - Yahoo Finance (yfinance live market data)           │
                      └────────────────────────────────────────────────────────┘
```

---

## Prerequisites

1. **Ollama**: Installed and running locally.
   ```bash
   # Verify Ollama is running
   ollama list

   # Pull the target model (if not already downloaded)
   ollama pull qwen3.8:27b
   ```
2. **Python**: 3.10 or higher.
3. **Node.js**: 18.0 or higher with npm.

---

## Quickstart Guide

### 1. Start the Backend
You can launch the backend using the included convenience script or manually:

```bash
# Option A: One-click launcher script
./start_backend.sh

# Option B: Manual setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8888 --reload
```

The backend server starts on `http://localhost:8888`. Verify readiness at `http://localhost:8888/health`.

### 2. Start the Frontend
In a second terminal window:

```bash
# Option A: One-click launcher script
./start_frontend.sh

# Option B: Manual setup
cd frontend
npm install
npm run dev
```

Open your browser at **`http://localhost:3000`**.

---

## CSV Portfolio Format

The application includes a sample portfolio at `backend/data/sample_portfolio.csv`. You can import your own portfolio via the UI or by dropping a CSV matching this format:

```csv
ticker,shares,buy_price,buy_date,account_type,notes
NVDA,20,118.50,2024-06-12,Taxable,AI Growth Tranche 1
NVDA,10,128.00,2024-08-20,Taxable,Dip purchase
AAPL,25,182.20,2023-11-05,Roth IRA,Long term hold
MSFT,15,410.00,2024-03-15,Taxable,Cloud enterprise exposure
AMZN,18,175.40,2024-04-10,Taxable,E-commerce and AWS
JNJ,10,152.00,2023-09-18,Roth IRA,Healthcare defensive
SPY,15,510.00,2024-05-01,Taxable,S&P 500 core ETF
```

*Column headers are case-insensitive and support standard aliases (`ticker`/`symbol`, `shares`/`qty`, `buy_price`/`cost`/`price`).*

---

## Example Inquiries You Can Ask the Assistant

* **Portfolio Health & P&L:**
  > *"What is my current portfolio valuation and how much profit or loss do I have?"*
* **Diversification Audit:**
  > *"Analyze my portfolio diversification and highlight any risks or sector imbalances."*
* **Forward-Looking Rebalancing:**
  > *"I have $3,000 cash to deploy. What high-quality stocks should I buy next to balance my portfolio and reduce tech risk?"*
* **Single Stock Deep Dive:**
  > *"What is NVDA's current price, PEG ratio, and Wall Street target upside?"*
* **Stock Comparison:**
  > *"Compare AMD and Nvidia using valuation ratios and analyst consensus."*
* **Record New Purchases:**
  > *"I just bought 12 shares of Costco (COST) at $880 on my Taxable account. Please add it to my portfolio."*

---

## Switching Between Local Ollama and Thesys GenUI

If you ever wish to test Thesys GenUI cloud models instead of local Ollama, simply update `backend/.env`:

```env
LLM_PROVIDER=thesys
OPENAI_BASE_URL=https://api.thesys.dev/v1/embed/
OPENAI_API_KEY=your_thesys_api_key_from_thesys_dev
MODEL_NAME=c1/openai/gpt-5/v-20250930
```

---

## License
MIT
