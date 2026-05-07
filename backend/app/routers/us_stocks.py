"""US stocks bulk seed — uses SEC EDGAR company_tickers_exchange.json (free, no quota).
Populates all NYSE + Nasdaq stocks as stub records; deep data loads on first click.
"""
import asyncio
import logging
import httpx
from fastapi import APIRouter, BackgroundTasks
from sqlalchemy.exc import IntegrityError

from ..database import SessionLocal
from ..models.stock import Stock
from ..services.cache import cache_get, cache_set

router = APIRouter()
_log = logging.getLogger(__name__)
_PROGRESS_KEY = "us_stocks_seed_progress"

_SEC_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
_HEADERS = {"User-Agent": "ValueScreen info@valuescreen.com", "Accept-Encoding": "gzip"}
_KEEP_EXCHANGES = {"NYSE", "Nasdaq", "CBOE"}


def _set_progress(**kwargs):
    cache_set(_PROGRESS_KEY, kwargs, ttl=3600 * 3)


async def _fetch_sec_tickers() -> list[dict]:
    """Fetch all US exchange-listed stocks from SEC EDGAR (free, 1 HTTP call)."""
    async with httpx.AsyncClient(timeout=30, headers=_HEADERS, follow_redirects=True) as client:
        r = await client.get(_SEC_URL)
        r.raise_for_status()
        d = r.json()

    fields = d.get("fields", [])
    rows = d.get("data", [])
    idx = {f: i for i, f in enumerate(fields)}

    return [
        {
            "ticker": row[idx["ticker"]],
            "name":   row[idx["name"]],
            "exchange": row[idx["exchange"]],
        }
        for row in rows
        if row[idx.get("exchange", -1)] in _KEEP_EXCHANGES
        and row[idx.get("ticker", -1)]
    ]


async def _seed_all_us_stocks():
    _set_progress(running=True, done=0, total=0, added=0, skipped=0, pct=0, phase="Fetching ticker list…")

    try:
        stocks = await _fetch_sec_tickers()
    except Exception as exc:
        _log.error("Failed to fetch SEC tickers: %s", exc)
        _set_progress(running=False, done=0, total=0, added=0, skipped=0, pct=0, error=str(exc))
        return

    total = len(stocks)
    _set_progress(running=True, done=0, total=total, added=0, skipped=0, pct=0, phase="Seeding database…")

    BATCH = 500
    total_added = 0
    total_skipped = 0

    for i in range(0, total, BATCH):
        chunk = stocks[i:i + BATCH]
        db = SessionLocal()
        try:
            for row in chunk:
                ticker = row["ticker"].strip().upper()
                if not ticker or len(ticker) > 15:
                    continue

                existing = db.query(Stock).filter(Stock.ticker == ticker).first()
                if existing:
                    total_skipped += 1
                    continue

                db.add(Stock(
                    ticker=ticker,
                    name=row["name"],
                    exchange=row["exchange"],
                    currency="USD",
                    last_updated=None,  # marks as stub — not yet deep-refreshed
                ))
                total_added += 1

            db.commit()
        except IntegrityError:
            db.rollback()
        except Exception as exc:
            db.rollback()
            _log.error("Batch error at offset %d: %s", i, exc)
        finally:
            db.close()

        done = min(i + BATCH, total)
        _set_progress(
            running=True, done=done, total=total,
            added=total_added, skipped=total_skipped,
            pct=round(done / total * 100, 1),
            phase="Seeding database…",
        )
        await asyncio.sleep(0)  # yield to event loop

    _set_progress(
        running=False, done=total, total=total,
        added=total_added, skipped=total_skipped, pct=100.0,
        phase="Complete",
    )
    _log.info("US stocks seed done: %d added, %d already existed.", total_added, total_skipped)


@router.post("/seed", status_code=202)
async def seed_us_stocks(background_tasks: BackgroundTasks):
    existing = cache_get(_PROGRESS_KEY)
    if existing and existing.get("running"):
        return {"status": "already_running", "progress": existing}
    background_tasks.add_task(_seed_all_us_stocks)
    return {"status": "started"}


@router.get("/progress")
async def get_us_stocks_progress():
    p = cache_get(_PROGRESS_KEY)
    if not p:
        return {"running": False, "done": 0, "total": 0, "pct": 0, "added": 0, "skipped": 0}
    return p


@router.post("/reset")
async def reset_us_stocks_seed():
    cache_set(_PROGRESS_KEY, {"running": False, "done": 0, "total": 0, "pct": 0, "added": 0, "skipped": 0}, ttl=60)
    return {"status": "reset"}
