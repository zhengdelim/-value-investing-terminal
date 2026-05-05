"""
S&P 500 bulk seed router.
- GET  /api/sp500/tickers   — returns the 503-ticker list
- POST /api/sp500/seed      — starts background seed (yfinance-based, no quota)
- GET  /api/sp500/progress  — poll for live progress
"""

import asyncio
import functools
import logging
import re
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session
import httpx

from ..database import SessionLocal, get_db
from ..routers.stocks import _refresh_stock
from ..services.cache import cache_get, cache_set, make_key

router = APIRouter()
_log = logging.getLogger(__name__)

_PROGRESS_KEY = "sp500_seed_progress"
_TICKERS_KEY  = "sp500_tickers_v1"

_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
_HEADERS  = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


# ── Ticker fetching ───────────────────────────────────────────────────────────

class _TickerParser:
    """Minimal HTML parser to extract first-column tickers from the wikitable."""
    def __init__(self):
        self.tickers: list[str] = []
        self._in_td1 = False
        self._td_n   = 0
        self._buf    = ""
        self._in_table = False

    def feed(self, html: str):
        import html as _html_mod
        from html.parser import HTMLParser

        class _P(HTMLParser):
            def __init__(p_self):
                super().__init__()
                p_self.out: list[str] = []
                p_self._in_table = False
                p_self._td_n = 0
                p_self._in_td1 = False
                p_self._buf = ""

            def handle_starttag(p_self, tag, attrs):
                d = dict(attrs)
                if tag == "table" and "wikitable" in d.get("class", ""):
                    p_self._in_table = True
                if p_self._in_table and tag == "tr":
                    p_self._td_n = 0
                if p_self._in_table and tag == "td":
                    p_self._td_n += 1
                    p_self._in_td1 = p_self._td_n == 1
                    p_self._buf = ""

            def handle_endtag(p_self, tag):
                if p_self._in_table and tag == "td" and p_self._in_td1:
                    t = p_self._buf.strip()
                    if t and 1 <= len(t) <= 5:
                        p_self.out.append(t.replace(".", "-"))
                    p_self._in_td1 = False

            def handle_data(p_self, data):
                if p_self._in_td1:
                    p_self._buf += data

        p = _P()
        p.feed(html)
        self.tickers = list(dict.fromkeys(p.out))  # deduplicate, preserve order


async def _get_sp500_tickers() -> list[str]:
    cached = cache_get(_TICKERS_KEY)
    if cached:
        return cached
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=_HEADERS) as c:
            r = await c.get(_WIKI_URL)
            r.raise_for_status()
        parser = _TickerParser()
        parser.feed(r.text)
        tickers = parser.tickers
        if tickers:
            cache_set(_TICKERS_KEY, tickers, ttl=3600 * 24)  # cache 1 day
        return tickers
    except Exception as exc:
        _log.error("Failed to fetch S&P 500 tickers: %s", exc)
        return []


# ── Background seeding ────────────────────────────────────────────────────────

def _reset_progress(total: int):
    cache_set(_PROGRESS_KEY, {
        "running": True, "total": total, "done": 0,
        "success": [], "failed": [], "pct": 0,
    }, ttl=3600 * 2)


def _update_progress(ticker: str, ok: bool):
    p = cache_get(_PROGRESS_KEY) or {}
    done = p.get("done", 0) + 1
    total = p.get("total", 1)
    if ok:
        p.setdefault("success", []).append(ticker)
    else:
        p.setdefault("failed", []).append(ticker)
    p["done"] = done
    p["pct"]  = round(done / total * 100, 1)
    cache_set(_PROGRESS_KEY, p, ttl=3600 * 2)


def _finish_progress():
    p = cache_get(_PROGRESS_KEY) or {}
    p["running"] = False
    cache_set(_PROGRESS_KEY, p, ttl=3600 * 2)


async def _seed_all(tickers: list[str]):
    _reset_progress(len(tickers))
    # Process one at a time with delay to stay within FMP free plan limits
    batch = 1
    for i in range(0, len(tickers), batch):
        chunk = tickers[i:i + batch]
        db = SessionLocal()
        try:
            tasks = [_seed_one(t, db) for t in chunk]
            await asyncio.gather(*tasks)
        finally:
            db.close()
        await asyncio.sleep(2)  # 2s delay = ~30 stocks/min, well within 300 req/min
    _finish_progress()
    _log.info("S&P 500 seed complete.")


async def _seed_one(ticker: str, db: Session):
    try:
        await _refresh_stock(ticker, db)
        _update_progress(ticker, ok=True)
    except Exception as exc:
        _log.warning("Seed failed for %s: %s", ticker, exc)
        _update_progress(ticker, ok=False)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/tickers")
async def get_sp500_tickers():
    tickers = await _get_sp500_tickers()
    return {"count": len(tickers), "tickers": tickers}


@router.post("/seed")
async def seed_sp500(background_tasks: BackgroundTasks):
    existing = cache_get(_PROGRESS_KEY)
    if existing and existing.get("running"):
        return {"status": "already_running", "progress": existing}

    tickers = await _get_sp500_tickers()
    if not tickers:
        return {"status": "error", "message": "Could not fetch S&P 500 ticker list."}

    background_tasks.add_task(_seed_all, tickers)
    return {"status": "started", "total": len(tickers)}


@router.get("/progress")
async def get_seed_progress():
    p = cache_get(_PROGRESS_KEY)
    if not p:
        return {"running": False, "done": 0, "total": 0, "pct": 0,
                "success": [], "failed": []}
    return p


@router.post("/reset")
async def reset_seed():
    cache_set(_PROGRESS_KEY, {"running": False, "done": 0, "total": 0,
                               "pct": 0, "success": [], "failed": []}, ttl=60)
    return {"status": "reset"}
