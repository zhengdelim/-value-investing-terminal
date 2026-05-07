"""US stocks bulk seed — uses FMP /stock-screener to populate all NYSE+NASDAQ+AMEX stocks with basic data."""
import asyncio
import logging
from fastapi import APIRouter, BackgroundTasks
from sqlalchemy.exc import IntegrityError

from ..database import SessionLocal
from ..models.stock import Stock
from ..services import fmp
from ..services.cache import cache_get, cache_set

router = APIRouter()
_log = logging.getLogger(__name__)
_PROGRESS_KEY = "us_stocks_seed_progress"


def _sf(v) -> float | None:
    try:
        f = float(v)
        return f if f == f else None  # NaN guard
    except (TypeError, ValueError):
        return None


def _set_progress(**kwargs):
    cache_set(_PROGRESS_KEY, kwargs, ttl=3600 * 3)


async def _seed_all_us_stocks():
    _set_progress(running=True, done=0, total=8000, added=0, skipped=0, pct=0)
    offset = 0
    limit = 1000
    total_added = 0
    total_skipped = 0
    total_seen = 0

    while True:
        batch = await fmp.get_us_screener_page(offset=offset, limit=limit)
        if not batch:
            break

        db = SessionLocal()
        try:
            for row in batch:
                ticker = (row.get("symbol") or "").strip().upper()
                if not ticker or len(ticker) > 10:
                    continue

                total_seen += 1
                existing = db.query(Stock).filter(Stock.ticker == ticker).first()

                # Don't overwrite stocks that have already been deep-refreshed (last_updated is set)
                if existing and existing.last_updated is not None:
                    total_skipped += 1
                    continue

                price = _sf(row.get("price"))
                last_div = _sf(row.get("lastAnnualDividend"))
                div_yield = (last_div / price) if last_div and price and price > 0 else None

                if existing:
                    # Already basic-seeded: refresh price and market cap only
                    existing.current_price = price
                    existing.market_cap = _sf(row.get("marketCap"))
                    total_skipped += 1
                else:
                    db.add(Stock(
                        ticker=ticker,
                        name=row.get("companyName"),
                        exchange=row.get("exchange") or row.get("exchangeShortName"),
                        sector=row.get("sector"),
                        industry=row.get("industry"),
                        current_price=price,
                        market_cap=_sf(row.get("marketCap")),
                        beta=_sf(row.get("beta")),
                        dividend_yield=div_yield,
                        currency="USD",
                        last_updated=None,  # None = basic seed only, not deep-refreshed
                    ))
                    total_added += 1

            db.commit()
        except IntegrityError:
            db.rollback()
            _log.warning("Integrity error in batch at offset %d — skipped", offset)
        except Exception as exc:
            db.rollback()
            _log.error("Screener batch error at offset %d: %s", offset, exc)
        finally:
            db.close()

        total_done = offset + len(batch)
        _set_progress(
            running=True,
            done=total_done,
            total=max(total_done, 8000),
            added=total_added,
            skipped=total_skipped,
            pct=round(total_done / max(total_done, 8000) * 100, 1),
        )

        if len(batch) < limit:
            break  # last page
        offset += limit
        await asyncio.sleep(0.3)  # stay within rate limits

    _set_progress(
        running=False, done=total_seen, total=total_seen,
        added=total_added, skipped=total_skipped, pct=100.0,
    )
    _log.info("US stocks bulk seed done: %d added, %d skipped.", total_added, total_skipped)


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
