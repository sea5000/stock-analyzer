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
    description="Local AI Stock Analysis, Portfolio Valuation, and Forward-Looking Rebalancing Engine",
    version="1.0.0"
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

                # 1. Skip events originating from the tools execution node
                if metadata.get("langgraph_node") == "tools":
                    continue

                # 2. Skip ToolMessage objects (which carry the tool JSON output)
                if "tool" in token.__class__.__name__.lower():
                    continue

                # 3. Yield text content from the AI model
                content = getattr(token, "content", None)
                if content and isinstance(content, str):
                    yield content
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and "text" in block:
                            yield block["text"]
                        elif isinstance(block, str):
                            yield block
        except Exception as e:
            import traceback
            print(f"[Chat Stream Error] {e}")
            traceback.print_exc()
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


# ========================================================
# Main Entry Point
# ========================================================

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
