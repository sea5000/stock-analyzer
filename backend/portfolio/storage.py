"""
File persistence and CSV parser for portfolio lots.
Stores lots in backend/data/portfolio.json.
"""

import csv
import json
import io
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.config import settings
from backend.portfolio.models import PortfolioLot

PORTFOLIO_FILE = settings.DATA_DIR / "portfolio.json"
SAMPLE_CSV_FILE = settings.DATA_DIR / "sample_portfolio.csv"


def load_lots() -> List[PortfolioLot]:
    """Load all bought lots from disk. Auto-seeds sample portfolio if empty."""
    if not PORTFOLIO_FILE.exists():
        if SAMPLE_CSV_FILE.exists():
            # Seed with sample lots
            sample_lots = import_csv_file(SAMPLE_CSV_FILE)
            save_lots(sample_lots)
            return sample_lots
        return []

    try:
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            return [PortfolioLot(**item) for item in raw_data]
    except Exception as e:
        print(f"[Storage Error] Could not load portfolio lots: {e}")
        return []


def save_lots(lots: List[PortfolioLot]) -> bool:
    """Save all bought lots to disk."""
    try:
        data = [lot.model_dump() for lot in lots]
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"[Storage Error] Could not save portfolio lots: {e}")
        return False


def add_lot(
    ticker: str,
    shares: float,
    buy_price: float,
    buy_date: Optional[str] = None,
    account_type: str = "Taxable",
    notes: str = ""
) -> PortfolioLot:
    """Add a single lot and persist it."""
    lots = load_lots()
    new_lot = PortfolioLot(
        ticker=ticker.strip().upper(),
        shares=float(shares),
        buy_price=float(buy_price),
        buy_date=buy_date or PortfolioLot.model_fields["buy_date"].default_factory(),
        account_type=account_type or "Taxable",
        notes=notes or ""
    )
    lots.append(new_lot)
    save_lots(lots)
    return new_lot


def delete_lot(lot_id: str) -> bool:
    """Delete a lot by ID."""
    lots = load_lots()
    initial_len = len(lots)
    lots = [l for l in lots if l.lot_id != lot_id]
    if len(lots) < initial_len:
        save_lots(lots)
        return True
    return False


def clear_lots() -> bool:
    """Clear all portfolio lots."""
    return save_lots([])


def parse_csv_content(csv_text: str) -> List[PortfolioLot]:
    """
    Parse a CSV string containing stock lots.
    Supports flexible column names:
      - Ticker / Symbol
      - Shares / Qty / Quantity
      - Buy_Price / Price / Cost / Cost_Basis
      - Buy_Date / Date
      - Account_Type / Account
      - Notes
    """
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    lots: List[PortfolioLot] = []

    for row in reader:
        # Normalize key names
        normalized_row = {k.strip().lower().replace(" ", "_"): v.strip() for k, v in row.items() if k}

        # Resolve ticker
        ticker = normalized_row.get("ticker") or normalized_row.get("symbol")
        if not ticker:
            continue

        # Resolve shares
        shares_str = normalized_row.get("shares") or normalized_row.get("qty") or normalized_row.get("quantity")
        if not shares_str:
            continue
        try:
            shares = float(shares_str.replace(",", "").replace("$", ""))
        except ValueError:
            continue

        # Resolve price
        price_str = (
            normalized_row.get("buy_price")
            or normalized_row.get("price")
            or normalized_row.get("cost")
            or normalized_row.get("cost_basis")
            or "0"
        )
        try:
            buy_price = float(price_str.replace(",", "").replace("$", ""))
        except ValueError:
            buy_price = 0.0

        buy_date = normalized_row.get("buy_date") or normalized_row.get("date") or "2024-01-01"
        account = normalized_row.get("account_type") or normalized_row.get("account") or "Taxable"
        notes = normalized_row.get("notes") or ""

        lot = PortfolioLot(
            ticker=ticker.strip().upper(),
            shares=shares,
            buy_price=buy_price,
            buy_date=buy_date,
            account_type=account,
            notes=notes
        )
        lots.append(lot)

    return lots


def import_csv_file(file_path: Path) -> List[PortfolioLot]:
    """Read a CSV file from disk and parse lots."""
    with open(file_path, "r", encoding="utf-8") as f:
        return parse_csv_content(f.read())
