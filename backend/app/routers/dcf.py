from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.stock import Stock, Financial
from ..schemas.stock import DCFResponse
from ..services import cache
from ..services.dcf_calculator import run_dcf

router = APIRouter()


@router.get("/{ticker}/dcf", response_model=DCFResponse)
async def get_dcf(
    ticker: str,
    growth_rate: float = Query(default=0.10, ge=-0.5, le=1.0),
    terminal_growth: float = Query(default=0.03, ge=0.0, le=0.10),
    discount_rate: float = Query(default=0.10, ge=0.01, le=0.5),
    years: int = Query(default=10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    t = ticker.upper()
    cache_key = cache.make_key(
        "dcf", ticker=t,
        gr=growth_rate, tg=terminal_growth, dr=discount_rate, y=years,
    )
    cached = cache.cache_get(cache_key)
    if cached:
        return cached

    stock = db.query(Stock).filter(Stock.ticker == t).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {t} not found. Fetch detail first.")

    latest_fin = (
        db.query(Financial)
        .filter(Financial.ticker == t, Financial.period == "annual")
        .order_by(Financial.date.desc())
        .first()
    )

    base_fcf = None
    if latest_fin:
        base_fcf = latest_fin.fcf
        if not base_fcf and latest_fin.operating_cash_flow and latest_fin.capex:
            base_fcf = latest_fin.operating_cash_flow + latest_fin.capex  # capex is negative
    if not base_fcf:
        raise HTTPException(status_code=422, detail=f"No FCF data available for {t}")

    result = run_dcf(
        ticker=t,
        base_fcf=base_fcf,
        current_price=stock.current_price,
        shares_outstanding=stock.shares_outstanding,
        growth_rate=growth_rate,
        terminal_growth=terminal_growth,
        discount_rate=discount_rate,
        years=years,
    )

    cache.cache_set(cache_key, result.model_dump(), ttl=3600)
    return result
