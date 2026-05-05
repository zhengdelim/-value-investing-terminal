"""
Watchlist router — simple named lists of tickers, keyed by a browser UUID.
- POST /api/watchlist              — create a new watchlist
- GET  /api/watchlist/{wid}        — get a watchlist
- PUT  /api/watchlist/{wid}        — overwrite tickers list
- POST /api/watchlist/{wid}/add    — add ticker(s)
- POST /api/watchlist/{wid}/remove — remove ticker(s)
- GET  /api/watchlist/{wid}/stocks — return full StockSummary for each ticker in list
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from ..database import get_db
from ..models.stock import Stock
from ..schemas.stock import StockSummary
from ..services.cache import cache_get, cache_set, make_key

router = APIRouter()

_TTL = 3600 * 24 * 365  # watchlists persist 1 year in Redis


# ── Schemas ───────────────────────────────────────────────────────────────────

class WatchlistCreate(BaseModel):
    id: str          # UUID generated in browser
    name: str = "My Watchlist"
    tickers: list[str] = []


class WatchlistUpdate(BaseModel):
    name: Optional[str] = None
    tickers: Optional[list[str]] = None


class TickerPayload(BaseModel):
    tickers: list[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wkey(wid: str) -> str:
    return make_key("watchlist", id=wid)


def _load(wid: str) -> dict:
    data = cache_get(_wkey(wid))
    if not data:
        raise HTTPException(status_code=404, detail="Watchlist not found.")
    return data


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_watchlist(body: WatchlistCreate):
    existing = cache_get(_wkey(body.id))
    if existing:
        return existing  # idempotent — return existing if same ID
    data = {
        "id":         body.id,
        "name":       body.name,
        "tickers":    [t.upper() for t in body.tickers],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    cache_set(_wkey(body.id), data, ttl=_TTL)
    return data


@router.get("/{wid}")
async def get_watchlist(wid: str):
    return _load(wid)


@router.put("/{wid}")
async def update_watchlist(wid: str, body: WatchlistUpdate):
    data = _load(wid)
    if body.name is not None:
        data["name"] = body.name
    if body.tickers is not None:
        data["tickers"] = list(dict.fromkeys(t.upper() for t in body.tickers))
    data["updated_at"] = datetime.utcnow().isoformat()
    cache_set(_wkey(wid), data, ttl=_TTL)
    return data


@router.post("/{wid}/add")
async def add_to_watchlist(wid: str, body: TickerPayload):
    data = _load(wid)
    existing = set(data["tickers"])
    for t in body.tickers:
        existing.add(t.upper())
    data["tickers"]    = list(existing)
    data["updated_at"] = datetime.utcnow().isoformat()
    cache_set(_wkey(wid), data, ttl=_TTL)
    return data


@router.post("/{wid}/remove")
async def remove_from_watchlist(wid: str, body: TickerPayload):
    data = _load(wid)
    remove = {t.upper() for t in body.tickers}
    data["tickers"]    = [t for t in data["tickers"] if t not in remove]
    data["updated_at"] = datetime.utcnow().isoformat()
    cache_set(_wkey(wid), data, ttl=_TTL)
    return data


@router.get("/{wid}/stocks", response_model=list[StockSummary])
async def watchlist_stocks(wid: str, db: Session = Depends(get_db)):
    data   = _load(wid)
    tickers = data["tickers"]
    if not tickers:
        return []
    stocks = (
        db.query(Stock)
        .filter(Stock.ticker.in_(tickers))
        .order_by(Stock.guru_score.desc().nullslast())
        .all()
    )
    # Preserve watchlist order for tickers not yet in DB
    in_db  = {s.ticker: s for s in stocks}
    result = [StockSummary.model_validate(in_db[t]) for t in tickers if t in in_db]
    return result
