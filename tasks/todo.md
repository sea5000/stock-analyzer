# Task Breakdown: AI Stock Analysis & Portfolio Assistant (Local AI + Ollama)

## Phase 1: Backend Foundation & Virtual Environment

### Task 1.1: Project Directory & Python Virtual Environment Setup
- **Description:** Set up `backend/` and `frontend/` folders, configure Python `requirements.txt`, and configure `.env` pointing to local Ollama (`qwen3.8:27b`).
- **Subtasks:**
  - [x] 1.1.1 Scaffold project directories: `backend/`, `backend/tools/`, `backend/portfolio/`, `backend/data/`, and `frontend/`.
  - [x] 1.1.2 Create `backend/requirements.txt` (`fastapi`, `uvicorn`, `pydantic`, `langchain`, `langchain-openai`, `langgraph`, `yfinance`, `python-dotenv`, `pandas`).
  - [x] 1.1.3 Create `backend/.env.example` pre-configured for local Ollama (`LLM_PROVIDER=ollama`, `OPENAI_BASE_URL=http://localhost:11434/v1`, `OPENAI_API_KEY=ollama`, `MODEL_NAME=qwen3.8:27b`, `PORT=8888`).
- **Acceptance Criteria:**
  - Standard Python virtual environment instructions ready (`python3 -m venv .venv`).
  - Clean directory structure created.
- **Verification:**
  - Dependency list verified without version conflicts.
- **Dependencies:** None
- **Files touched:**
  - `backend/requirements.txt`
  - `backend/.env.example`
- **Estimated scope:** Small (2 files)

### Task 1.2: FastAPI Application & CORS Configuration
- **Description:** Implement base FastAPI app with CORS middleware, configuration management, and health check endpoint.
- **Subtasks:**
  - [x] 1.2.1 Create `backend/config.py` loading `.env` variables with defaults for local Ollama.
  - [x] 1.2.2 Create `backend/main.py` initializing FastAPI with `CORSMiddleware` (allowing `http://localhost:3000`).
  - [x] 1.2.3 Add `GET /health` endpoint verifying backend status and checking connectivity to Ollama (`http://localhost:11434`).
- **Acceptance Criteria:**
  - Server starts on `0.0.0.0:8888`.
  - `/health` returns `{ "status": "ok", "provider": "ollama", "model": "qwen3.8:27b", "ollama_connected": true/false }`.
- **Verification:**
  - Health check endpoint test succeeds.
- **Dependencies:** Task 1.1
- **Files touched:**
  - `backend/config.py`
  - `backend/main.py`
- **Estimated scope:** Small (2 files)

---

## Checkpoint 1: Backend Foundation Verified
- [x] Dependencies documented and installable.
- [x] Base server runs and responds to health checks with Ollama status.

---

## Phase 2: Financial Market Data Tools (`yfinance`)

### Task 2.1: Market Intelligence Tools Suite
- **Description:** Implement 7 financial analysis tools in `backend/tools/financial_tools.py` with robust DataFrame serialization.
- **Subtasks:**
  - [x] 2.1.1 Implement `get_stock_price(ticker: str)`: current/last close price, handles invalid symbols.
  - [x] 2.1.2 Implement `get_historical_stock_price(ticker: str, start_date: str, end_date: str)`: historical closing prices and dates serialized to JSON dict.
  - [x] 2.1.3 Implement `get_balance_sheet(ticker: str)`: company balance sheet serialized to JSON-safe structure.
  - [x] 2.1.4 Implement `get_stock_news(ticker: str)`: recent headlines, summary, links.
  - [x] 2.1.5 Implement `get_key_ratios(ticker: str)`: Trailing/Forward P/E, PEG, Price-to-Book, Debt-to-Equity, Profit Margins, ROE, Free Cash Flow.
  - [x] 2.1.6 Implement `get_analyst_recommendations(ticker: str)`: consensus rating and target price range (mean, high, low).
  - [x] 2.1.7 Implement `get_company_profile(ticker: str)`: sector, industry, market cap, business description.
- **Acceptance Criteria:**
  - All tools decorated with `@tool` and detailed docstrings for Ollama function-calling.
  - Returns JSON-serializable primitives (dicts, lists, numbers).
- **Verification:**
  - Unit tests or scratch test verifying tools on `AAPL`, `NVDA`, `MSFT`.
- **Dependencies:** Task 1.2
- **Files touched:**
  - `backend/tools/financial_tools.py`
  - `backend/tools/__init__.py`
- **Estimated scope:** Medium (1-2 files)

---

## Checkpoint 2: Market Tools Suite Verified
- [x] All 7 tools functional with real financial data from `yfinance`.
- [x] Edge cases (invalid tickers, missing metrics) handled cleanly.

---

## Phase 3: Portfolio & Bought Lots Engine

### Task 3.1: Portfolio Data Model & Storage
- **Description:** Implement the bought lots data structure, JSON persistence, and CSV import parser.
- **Subtasks:**
  - [x] 3.1.1 Define `PortfolioLot` and `PortfolioHoldings` Pydantic models in `backend/portfolio/models.py`.
  - [x] 3.1.2 Create `backend/portfolio/storage.py` for persistent JSON storage in `backend/data/portfolio.json`.
  - [x] 3.1.3 Create CSV import parser handling standard broker formats (`ticker`, `shares`, `buy_price`, `buy_date`, `account_type`, `notes`).
  - [x] 3.1.4 Create sample portfolio CSV template (`backend/data/sample_portfolio.csv`) for quick testing.
- **Acceptance Criteria:**
  - Lots can be imported from CSV or added programmatically, persisted cleanly to disk.
- **Verification:**
  - Importing sample CSV loads expected holdings and lots.
- **Dependencies:** Task 1.2
- **Files touched:**
  - `backend/portfolio/models.py`
  - `backend/portfolio/storage.py`
  - `backend/data/sample_portfolio.csv`
- **Estimated scope:** Medium (3 files)

### Task 3.2: Portfolio Analytics & Forward-Looking Tools
- **Description:** Implement portfolio performance metrics, sector diversification analysis, and forward-looking rebalancing tools.
- **Subtasks:**
  - [x] 3.2.1 Implement `get_portfolio_summary()` tool: calculates total invested cost basis, current live portfolio value, total unrealized P&L ($ and %), and breakdown per position.
  - [x] 3.2.2 Implement `analyze_portfolio_diversification()` tool: categorizes holdings by sector & industry, calculates percentage allocations, and scores concentration risk (e.g. over 50% in tech).
  - [x] 3.2.3 Implement `recommend_next_buys(budget: float, focus: str)` tool: forward-looking rebalancing engine that evaluates underweight sectors, screens candidate stocks via analyst upside and valuation ratios, and provides prioritized recommendations on what to buy next or add more of.
  - [x] 3.2.4 Implement `add_or_import_lots(ticker: str, shares: float, buy_price: float, buy_date: str)` tool so the assistant can record bought lots directly via conversation.
- **Acceptance Criteria:**
  - Tools compute live metrics using `yfinance` market prices combined with user's bought lots.
  - Forward-looking rebalancing suggests actionable diversification ideas based on user's current allocation gaps.
- **Verification:**
  - Analytics test verifies P&L and sector breakdown on sample portfolio.
- **Dependencies:** Tasks 2.1, 3.1
- **Files touched:**
  - `backend/portfolio/analytics.py`
  - `backend/tools/portfolio_tools.py`
  - `backend/tools/__init__.py`
- **Estimated scope:** Medium (2 files)

---

## Checkpoint 3: Portfolio Engine Verified
- [x] Portfolio lots load and compute real-time P&L correctly.
- [x] Sector diversification and "what to buy next" tools produce intelligent rebalancing plans.

---

## Phase 4: LangGraph Agent & Chat Streaming Endpoint

### Task 4.1: Ollama Model & Checkpointer Setup
- **Description:** Assemble the LangGraph agent powered by local Ollama `qwen3.8:27b` equipped with all 11 tools (7 market tools + 4 portfolio tools) and memory.
- **Subtasks:**
  - [x] 4.1.1 Initialize `ChatOpenAI` targeting `http://localhost:11434/v1` with model `qwen3.8:27b`.
  - [x] 4.1.2 Set up `InMemorySaver` checkpointer for multi-turn thread retention.
  - [x] 4.1.3 Assemble LangGraph agent with all tools and prompt engineering tailored to Qwen 2.5 / 3.8.
- **Acceptance Criteria:**
  - Agent compiles cleanly and executes tool calls against local Ollama.
- **Verification:**
  - Agent answers test questions using tool calling.
- **Dependencies:** Tasks 2.1, 3.2
- **Files touched:**
  - `backend/agent.py`
- **Estimated scope:** Small (1 file)

### Task 4.2: Streaming Chat Route & Portfolio REST Endpoints
- **Description:** Implement `POST /api/chat` SSE streaming route and REST endpoints for portfolio CSV upload and inspection.
- **Subtasks:**
  - [x] 4.2.1 Implement `POST /api/chat` accepting `RequestObject` and streaming tokens via SSE (`text/event-stream`).
  - [x] 4.2.2 Add `POST /api/portfolio/upload` to upload portfolio CSV files directly from the UI.
  - [x] 4.2.3 Add `GET /api/portfolio` to fetch current holdings and lots for the frontend portfolio dashboard.
  - [x] 4.2.4 Formulate system prompt instructing the assistant on portfolio analysis, financial metrics, and forward-looking diversification recommendations.
- **Acceptance Criteria:**
  - Chat streams responses token-by-token.
  - Portfolio REST endpoints allow seamless CSV import and status retrieval.
- **Verification:**
  - `curl` test verifies SSE stream and portfolio upload.
- **Dependencies:** Task 4.1
- **Files touched:**
  - `backend/main.py`
- **Estimated scope:** Small (1-2 files)

---

## Checkpoint 4: Complete Backend Functional
- [x] Local Ollama generates responses and triggers tools.
- [x] Streaming works smoothly over SSE.
- [x] Portfolio import and summary endpoints respond correctly.

---

## Phase 5: Frontend Development (React + TypeScript + Vite)

### Task 5.1: Vite Project Scaffold & Proxy Setup
- **Description:** Scaffold Vite React TypeScript app in `frontend/` and configure reverse proxy.
- **Subtasks:**
  - [x] 5.1.1 Scaffold `frontend/` with React + TypeScript.
  - [x] 5.1.2 Configure `frontend/vite.config.ts` to proxy `/api` requests to `http://localhost:8888`.
  - [x] 5.1.3 Install dependencies: Lucide icons, theme utilities, and UI components.
- **Acceptance Criteria:**
  - Dev server runs on port 3000 and proxies API requests.
- **Verification:**
  - `npm run build` succeeds.
- **Dependencies:** None
- **Files touched:**
  - `frontend/package.json`
  - `frontend/vite.config.ts`
  - `frontend/tsconfig.json`
  - `frontend/index.html`
- **Estimated scope:** Medium (3-4 files)

### Task 5.2: Dual-Tab Dashboard (Chat & Portfolio Manager)
- **Description:** Implement a responsive dark-themed interface with two views: (1) AI Stock & Portfolio Chat, and (2) Portfolio & Lots Manager.
- **Subtasks:**
  - [x] 5.2.1 Implement Chat view with streaming message bubbles, markdown tables, and quick action prompts (e.g. *"Analyze my portfolio diversification"*, *"What should I buy next with $2,000?"*).
  - [x] 5.2.2 Implement Portfolio view: CSV file uploader, summary cards (Total Value, Total Invested, Unrealized Gain/Loss, Top Holding), and interactive lots table.
  - [x] 5.2.3 Create `frontend/src/App.css` for a sleek dark-mode glassmorphic theme.
- **Acceptance Criteria:**
  - Users can switch between Chat and Portfolio views seamlessly.
  - Uploading a CSV immediately updates the portfolio summary and informs the AI agent.
- **Verification:**
  - Browser inspection confirms clean rendering and interaction.
- **Dependencies:** Task 5.1
- **Files touched:**
  - `frontend/src/App.tsx`
  - `frontend/src/components/PortfolioView.tsx`
  - `frontend/src/components/ChatView.tsx`
  - `frontend/src/App.css`
- **Estimated scope:** Medium (4-5 files)

---

## Checkpoint 5: Frontend Interface Complete
- [x] Chat view communicates with local Ollama via backend.
- [x] Portfolio CSV import displays lots, calculations, and P&L.
- [x] Tab switching latency resolved: components kept mounted with 0ms transition.
- [x] Chat history and thread ID persisted across tab switches and browser reloads via `localStorage`.
- [x] Added "New Chat" action button to reset and start fresh sessions cleanly.

---

## Phase 6: End-to-End Verification, Documentation & Developer Experience

### Task 6.1: End-to-End Workflow Verification
- **Description:** Run full end-to-end tests covering all user scenarios.
- **Subtasks:**
  - [ ] 6.1.1 Test stock market lookups: live quotes (`NVDA`), 6-month historical chart data, financial news.
  - [ ] 6.1.2 Test portfolio CSV upload: import `sample_portfolio.csv` (tech heavy: NVDA, AAPL, MSFT, AMZN).
  - [ ] 6.1.3 Test portfolio summary query: *"What is my current portfolio performance and profit/loss?"*
  - [ ] 6.1.4 Test diversification analysis query: *"Analyze my portfolio diversification and highlight any risks."*
  - [ ] 6.1.5 Test forward-looking rebalancing query: *"I have $3,000 cash to invest. What should I buy next to diversify and grow?"*
- **Acceptance Criteria:**
  - Assistant analyzes user's specific lots, identifies concentration in tech, and suggests diversified buys in underweight sectors using real financial data.
- **Verification:**
  - End-to-end test run passes.
- **Dependencies:** Tasks 4.2, 5.2
- **Files touched:**
  - System-wide verification
- **Estimated scope:** Small

### Task 6.2: Launch Scripts & Documentation
- **Description:** Provide setup scripts, sample CSV, and comprehensive documentation.
- **Subtasks:**
  - [x] 6.2.1 Create root `README.md` explaining local Ollama setup (`qwen3.8:27b`), portfolio import format, and usage guide.
  - [x] 6.2.2 Create `start_backend.sh` and `start_frontend.sh` convenience scripts.
  - [x] 6.2.3 Ensure comprehensive `.gitignore` (`.venv`, `node_modules`, `.env`, `dist`).
- **Acceptance Criteria:**
  - Any developer can clone, run `./start_backend.sh` and `./start_frontend.sh`, and begin analyzing their portfolio.
- **Verification:**
  - Repository structure clean and documented.
- **Dependencies:** Task 6.1
- **Files touched:**
  - `README.md`
  - `start_backend.sh`
  - `start_frontend.sh`
  - `.gitignore`
- **Estimated scope:** Small (4 files)
