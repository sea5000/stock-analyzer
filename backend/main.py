import uvicorn
import httpx
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import settings
from backend.agent import financial_agent, SYSTEM_PROMPT
from backend.portfolio.analytics import (
    compute_portfolio_report,
    analyze_diversification_gaps,
    invalidate_portfolio_cache,
)
from backend.portfolio.storage import (
    load_lots,
    save_lots,
    add_lot,
    delete_lot,
    clear_lots,
    parse_csv_content,
    import_csv_file,
    SAMPLE_CSV_FILE,
)
from backend.portfolio.models import PortfolioLot

app = FastAPI(
    title="AI Stock & Portfolio Analysis Assistant",
    description="AI Stock Analysis, Portfolio Valuation, and Forward-Looking Rebalancing Engine",
    version="1.0.1"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================================================
# Pydantic Request Schemas (Thesys & Custom Client Compatible)
# ========================================================

class PromptObject(BaseModel):
    content: str
    id: Optional[str] = "prompt_0"
    role: Optional[str] = "user"


class RequestObject(BaseModel):
    prompt: PromptObject
    threadId: Optional[str] = Field(default=None, alias="threadId")
    thread_id: Optional[str] = Field(default=None, alias="thread_id")
    responseId: Optional[str] = None

    class Config:
        populate_by_name = True


class AddLotRequest(BaseModel):
    ticker: str
    shares: float
    buy_price: float
    buy_date: Optional[str] = None
    account_type: Optional[str] = "Taxable"
    notes: Optional[str] = ""


# ========================================================
# System & Health Endpoints
# ========================================================

@app.get("/health")
async def health():
    """Health check endpoint that probes local Ollama status."""
    ollama_online = False
    models_available = []

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get("http://localhost:11434/api/tags")
            if res.status_code == 200:
                ollama_online = True
                data = res.json()
                models_available = [m.get("name") for m in data.get("models", [])]
    except Exception:
        ollama_online = False

    return {
        "status": "ok",
        "provider": settings.LLM_PROVIDER,
        "configured_model": settings.MODEL_NAME,
        "ollama_online": ollama_online,
        "models_available": models_available,
    }


@app.get("/api/config")
async def get_config():
    """Return runtime configuration information."""
    return {
        "status": "ok",
        "provider": settings.LLM_PROVIDER,
        "configured_model": settings.MODEL_NAME,
    }


# ========================================================
# Chat Streaming Endpoint (SSE)
# ========================================================

@app.post("/api/chat")
async def chat_endpoint(request: RequestObject):
    """
    Server-Sent Events (SSE) streaming endpoint compatible with Thesys C1Chat
    and local React chat interfaces.
    """
    thread_id = request.threadId or request.thread_id or "default_session"
    config = {"configurable": {"thread_id": thread_id}}

    user_message = request.prompt.content

    def generate_tokens():
        try:
            in_thinking = False
            announced_tools = set()

            for event in financial_agent.stream(
                {"messages": [HumanMessage(content=user_message)]},
                stream_mode="messages",
                config=config,
            ):
                token = None
                metadata = {}
                if isinstance(event, tuple):
                    token = event[0]
                    if len(event) > 1 and isinstance(event[1], dict):
                        metadata = event[1]
                elif hasattr(event, "content"):
                    token = event

                if token is None:
                    continue

                # 1. Announce tool execution if tool_calls are initiated
                tool_calls = getattr(token, "tool_calls", None)
                if tool_calls and isinstance(tool_calls, list):
                    for tc in tool_calls:
                        name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                        if name and name not in announced_tools:
                            announced_tools.add(name)
                            ticker_arg = ""
                            args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})
                            if isinstance(args, dict) and "ticker" in args:
                                ticker_arg = f" for **{args['ticker'].upper()}**"
                            yield f"> 🔍 *Fetching {name.replace('_', ' ')}{ticker_arg}...*\n\n"

                # 2. Skip events originating from the tools execution node itself
                if metadata.get("langgraph_node") == "tools":
                    continue

                # 3. Skip ToolMessage objects (carrying raw tool JSON return)
                if "tool" in token.__class__.__name__.lower():
                    continue

                # 4. Stream reasoning/thinking tokens from local reasoning models (Qwen / DeepSeek)
                add_kwargs = getattr(token, "additional_kwargs", {}) or {}
                reasoning = add_kwargs.get("reasoning_content") or add_kwargs.get("thinking")
                if reasoning and isinstance(reasoning, str):
                    if not in_thinking:
                        yield "<think>\n"
                        in_thinking = True
                    yield reasoning

                # 5. Yield text content from the AI model
                content = getattr(token, "content", None)
                if content:
                    if in_thinking:
                        yield "\n</think>\n\n"
                        in_thinking = False

                    if isinstance(content, str):
                        yield content
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and "text" in block:
                                yield block["text"]
                            elif isinstance(block, str):
                                yield block

            if in_thinking:
                yield "\n</think>\n\n"

        except Exception as e:
            import traceback
            print(f"[Chat Stream Error] {e}")
            traceback.print_exc()

            # Inspect exception chain (LangGraph Pregel / OpenAI SDK)
            err = e
            chain = [err]
            while getattr(err, "__cause__", None) or getattr(err, "__context__", None):
                err = getattr(err, "__cause__", None) or getattr(err, "__context__", None)
                chain.append(err)

            combined_err = " ".join([str(x) for x in chain])
            for item in chain:
                body = getattr(item, "body", None)
                if isinstance(body, dict):
                    err_dict = body.get("error", {})
                    if isinstance(err_dict, dict) and "message" in err_dict:
                        combined_err += f" {err_dict['message']}"

            is_thesys = settings.LLM_PROVIDER.lower() == "thesys" or "thesys" in str(settings.OPENAI_BASE_URL).lower()

            if "insufficient balance" in combined_err.lower():
                yield (
                    "\n\n> ⚠️ **Thesys Cloud API Error: Insufficient Balance (HTTP 429)**\n>\n"
                    "> Your Thesys account has run out of credits or has an insufficient balance.\n>\n"
                    "> **Options:**\n"
                    "> 1. **Switch to Local Ollama (Free & Unlimited)**: Set `LLM_PROVIDER=ollama` in `backend/.env` to run on your local RTX GPU.\n"
                    "> 2. **Refill Credits**: Add credits at [console.thesys.dev](https://console.thesys.dev)."
                )
            elif "http exception" in combined_err.lower() and is_thesys:
                yield (
                    "\n\n> ⚠️ **Thesys Cloud API Error (`Http Exception` / HTTP 429)**\n>\n"
                    "> Thesys returned an HTTP error (HTTP 429: Insufficient balance on your organization account).\n>\n"
                    "> **Options:**\n"
                    "> 1. **Switch to Local Ollama (Free & Unlimited)**: Set `LLM_PROVIDER=ollama` in `backend/.env` to run on your local RTX GPU.\n"
                    "> 2. **Refill Credits**: Add credits at [console.thesys.dev](https://console.thesys.dev)."
                )
            else:
                yield f"\n\n[Error generating response: {str(e)}]"

    return StreamingResponse(
        generate_tokens(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ========================================================
# Portfolio Management REST Endpoints
# ========================================================

@app.get("/api/portfolio")
def get_portfolio_status(force: bool = False):
    """Retrieve full calculated portfolio report with live valuation, P&L, and sector weights."""
    return compute_portfolio_report(force_refresh=force)


@app.get("/api/portfolio/lots")
def get_raw_lots():
    """Retrieve all raw bought lots."""
    lots = load_lots()
    return {"count": len(lots), "lots": [l.model_dump() for l in lots]}


@app.post("/api/portfolio/lot")
def create_lot(payload: AddLotRequest):
    """Add a new bought lot."""
    lot = add_lot(
        ticker=payload.ticker,
        shares=payload.shares,
        buy_price=payload.buy_price,
        buy_date=payload.buy_date,
        account_type=payload.account_type or "Taxable",
        notes=payload.notes or "",
    )
    invalidate_portfolio_cache()
    return {"status": "success", "lot": lot.model_dump()}


@app.delete("/api/portfolio/lot/{lot_id}")
def remove_lot(lot_id: str):
    """Delete a specific lot by ID."""
    success = delete_lot(lot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lot not found")
    invalidate_portfolio_cache()
    return {"status": "success", "deleted_lot_id": lot_id}


@app.post("/api/portfolio/upload")
async def upload_portfolio_csv(file: UploadFile = File(...)):
    """Upload and parse a CSV file of stock lots."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    content = await file.read()
    csv_text = content.decode("utf-8", errors="replace")
    lots = parse_csv_content(csv_text)

    if not lots:
        raise HTTPException(status_code=400, detail="No valid lots found in CSV. Please verify column headers.")

    save_lots(lots)
    invalidate_portfolio_cache()
    return {
        "status": "success",
        "message": f"Successfully imported {len(lots)} lots from '{file.filename}'.",
        "imported_count": len(lots),
        "report": compute_portfolio_report(lots, force_refresh=True)
    }


@app.post("/api/portfolio/reset")
def reset_sample_portfolio():
    """Reset portfolio to the default sample portfolio (NVDA, AAPL, MSFT, AMZN, JNJ, SPY)."""
    invalidate_portfolio_cache()
    if SAMPLE_CSV_FILE.exists():
        sample_lots = import_csv_file(SAMPLE_CSV_FILE)
        save_lots(sample_lots)
        return {
            "status": "success",
            "message": "Reset to sample portfolio.",
            "lots_count": len(sample_lots)
        }
    clear_lots()
    return {"status": "success", "message": "Cleared portfolio."}


@app.post("/api/portfolio/clear")
def clear_portfolio():
    """Reset / clear all portfolio lots to an empty portfolio."""
    clear_lots()
    invalidate_portfolio_cache()
    return {"status": "success", "message": "Portfolio has been reset and all lots cleared."}


# ========================================================
# Main Entry Point
# ========================================================

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
