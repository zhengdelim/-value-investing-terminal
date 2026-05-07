from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.stock import Stock, Financial
from ..services.scores import swot_moat_analysis, market_research, valuation_review
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


def _stock_dict(stock: Stock) -> dict:
    return {
        "ticker": stock.ticker, "name": stock.name, "sector": stock.sector,
        "industry": stock.industry, "roe": stock.roe, "roic": stock.roic,
        "roa": stock.roa, "gross_margin": stock.gross_margin,
        "operating_margin": stock.operating_margin, "profit_margin": stock.profit_margin,
        "de_ratio": stock.de_ratio, "current_ratio": stock.current_ratio,
        "altman_z": stock.altman_z, "piotroski_score": stock.piotroski_score,
        "revenue_growth": stock.revenue_growth, "eps_growth": stock.eps_growth,
        "fcf_growth": stock.fcf_growth, "beta": stock.beta, "pe_ratio": stock.pe_ratio,
        "pb_ratio": stock.pb_ratio, "pfcf_ratio": stock.pfcf_ratio,
        "ev_ebitda": stock.ev_ebitda, "dividend_yield": stock.dividend_yield,
        "market_cap": stock.market_cap, "guru_score": stock.guru_score,
        "guru_value": stock.guru_value, "guru_quality": stock.guru_quality,
        "current_price": stock.current_price, "shares_outstanding": stock.shares_outstanding,
        "dcf_upside": stock.dcf_upside, "interest_coverage": stock.interest_coverage,
    }


@router.get("/{ticker}/research")
async def get_research(ticker: str, db: Session = Depends(get_db)):
    t = ticker.upper()
    cache_key = cache.make_key("research", ticker=t)
    cached = cache.cache_get(cache_key)
    if cached:
        return cached

    stock = db.query(Stock).filter(Stock.ticker == t).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {t} not found.")

    result = market_research(_stock_dict(stock))
    result["ticker"] = t
    cache.cache_set(cache_key, result, ttl=3600)
    return result


@router.get("/{ticker}/valuation-review")
async def get_valuation_review(ticker: str, db: Session = Depends(get_db)):
    t = ticker.upper()
    cache_key = cache.make_key("valuation-review", ticker=t)
    cached = cache.cache_get(cache_key)
    if cached:
        return cached

    stock = db.query(Stock).filter(Stock.ticker == t).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {t} not found.")

    latest_fin = (
        db.query(Financial)
        .filter(Financial.ticker == t, Financial.period == "annual")
        .order_by(Financial.date.desc())
        .first()
    )
    fin_dict = None
    if latest_fin:
        fin_dict = {
            "eps": latest_fin.eps_diluted or latest_fin.eps,
            "total_equity": latest_fin.total_equity,
            "shares_outstanding": latest_fin.shares_outstanding,
            "fcf": latest_fin.fcf,
            "ebitda": latest_fin.ebitda,
            "total_debt": latest_fin.total_debt,
            "cash": latest_fin.cash,
        }

    result = valuation_review(_stock_dict(stock), fin_dict)
    result["ticker"] = t
    cache.cache_set(cache_key, result, ttl=3600)
    return result
