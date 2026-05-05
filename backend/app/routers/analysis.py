from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.stock import Stock
from ..services.scores import swot_moat_analysis
from ..services import cache

router = APIRouter()


@router.get("/{ticker}/analysis")
async def get_analysis(ticker: str, db: Session = Depends(get_db)):
    t = ticker.upper()
    cache_key = cache.make_key("analysis", ticker=t)
    cached = cache.cache_get(cache_key)
    if cached:
        return cached

    stock = db.query(Stock).filter(Stock.ticker == t).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {t} not found. Fetch detail first.")

    stock_dict = {
        "ticker": stock.ticker,
        "name": stock.name,
        "sector": stock.sector,
        "industry": stock.industry,
        "roe": stock.roe,
        "roic": stock.roic,
        "roa": stock.roa,
        "gross_margin": stock.gross_margin,
        "operating_margin": stock.operating_margin,
        "profit_margin": stock.profit_margin,
        "de_ratio": stock.de_ratio,
        "current_ratio": stock.current_ratio,
        "altman_z": stock.altman_z,
        "piotroski_score": stock.piotroski_score,
        "revenue_growth": stock.revenue_growth,
        "eps_growth": stock.eps_growth,
        "fcf_growth": stock.fcf_growth,
        "beta": stock.beta,
        "pe_ratio": stock.pe_ratio,
        "pb_ratio": stock.pb_ratio,
        "pfcf_ratio": stock.pfcf_ratio,
        "ev_ebitda": stock.ev_ebitda,
        "dividend_yield": stock.dividend_yield,
        "market_cap": stock.market_cap,
        "guru_score": stock.guru_score,
        "guru_value": stock.guru_value,
        "guru_quality": stock.guru_quality,
    }

    result = swot_moat_analysis(stock_dict)
    result["ticker"] = t
    result["name"] = stock.name

    cache.cache_set(cache_key, result, ttl=3600)
    return result
