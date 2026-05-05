import asyncio
import functools
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional
from datetime import datetime, timedelta
import yfinance as yf

from ..database import get_db
from ..models.stock import Stock, Financial
from ..schemas.stock import StockSummary, StockDetail
from ..services import fmp, cache
from ..services import scores as score_svc

router = APIRouter()

# Curated list for seeding — fetched on demand via POST /api/stocks/seed
SEED_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "BRK-B", "JPM", "V", "JNJ",
    "UNH", "XOM", "PG", "MA", "HD", "CVX", "ABBV", "MRK", "LLY", "PEP",
    "KO", "AVGO", "COST", "WMT", "TMO", "BAC", "CSCO", "ACN", "MCD", "ADBE",
    "ORCL", "CRM", "INTC", "NFLX", "DIS", "VZ", "CMCSA", "WFC", "BMY", "AMGN",
]


async def _refresh_stock(ticker: str, db: Session) -> Stock:
    t = ticker.upper()

    profile, ratios, growth, metrics, income, balance, cashflow = (
        await fmp.get_profile(t),
        await fmp.get_ratios(t, limit=2),
        await fmp.get_financial_growth(t, limit=1),
        await fmp.get_key_metrics(t, limit=1),
        await fmp.get_income_statement(t, limit=2),
        await fmp.get_balance_sheet(t, limit=2),
        await fmp.get_cash_flow(t, limit=2),
    )

    if not profile:
        raise HTTPException(status_code=404, detail=f"Ticker {t} not found on FMP.")

    r = ratios[0] if ratios else {}
    g = growth[0] if growth else {}
    m = metrics[0] if metrics else {}
    inc = income[0] if income else {}
    inc_prev = income[1] if len(income) > 1 else {}
    bal = balance[0] if balance else {}
    bal_prev = balance[1] if len(balance) > 1 else {}
    cf = cashflow[0] if cashflow else {}

    sf = fmp.safe_float

    # --- Field mappings for new stable API ---
    pe_v = sf(r.get("priceToEarningsRatio"))
    pb_v = sf(r.get("priceToBookRatio"))
    pfcf_v = sf(r.get("priceToFreeCashFlowRatio"))
    ev_ebitda_v = sf(m.get("evToEBITDA"))
    roe_v = sf(m.get("returnOnEquity"))
    roic_v = sf(m.get("returnOnInvestedCapital"))
    roa_v = sf(m.get("returnOnAssets"))
    gm_v = sf(r.get("grossProfitMargin"))
    om_v = sf(r.get("operatingProfitMargin"))
    pm_v = sf(r.get("netProfitMargin"))
    de_v = sf(r.get("debtToEquityRatio"))
    cr_v = sf(r.get("currentRatio"))
    qr_v = sf(r.get("quickRatio"))
    ic_v = sf(r.get("interestCoverageRatio"))
    dy_v = sf(r.get("dividendYield"))
    pr_v = sf(r.get("dividendPayoutRatio"))
    ps_v = sf(r.get("priceToSalesRatio"))
    peg_v = sf(r.get("priceToEarningsGrowthRatio"))
    beta_v = sf(profile.get("beta"))
    mktcap_v = sf(profile.get("marketCap"))

    rev_growth = sf(g.get("revenueGrowth"))
    eps_growth = sf(g.get("epsgrowth"))
    fcf_growth = sf(g.get("freeCashFlowGrowth"))

    shares = sf(inc.get("weightedAverageShsOutDil") or inc.get("weightedAverageShsOut"))

    # Piotroski
    pio = score_svc.piotroski_f_score(
        net_income=sf(inc.get("netIncome")),
        total_assets=sf(bal.get("totalAssets")),
        operating_cash_flow=sf(cf.get("operatingCashFlow")),
        long_term_debt=sf(bal.get("longTermDebt")),
        current_assets=sf(bal.get("totalCurrentAssets")),
        current_liabilities=sf(bal.get("totalCurrentLiabilities")),
        shares_outstanding=shares,
        gross_profit=sf(inc.get("grossProfit")),
        revenue=sf(inc.get("revenue")),
        net_income_prev=sf(inc_prev.get("netIncome")),
        total_assets_prev=sf(bal_prev.get("totalAssets")),
        long_term_debt_prev=sf(bal_prev.get("longTermDebt")),
        current_assets_prev=sf(bal_prev.get("totalCurrentAssets")),
        current_liabilities_prev=sf(bal_prev.get("totalCurrentLiabilities")),
        shares_outstanding_prev=sf(inc_prev.get("weightedAverageShsOutDil")),
        gross_profit_prev=sf(inc_prev.get("grossProfit")),
        revenue_prev=sf(inc_prev.get("revenue")),
    )

    # Altman Z
    az = score_svc.altman_z_score(
        current_assets=sf(bal.get("totalCurrentAssets")),
        current_liabilities=sf(bal.get("totalCurrentLiabilities")),
        total_assets=sf(bal.get("totalAssets")),
        retained_earnings=sf(bal.get("retainedEarnings")),
        ebit=sf(inc.get("operatingIncome")),
        market_cap=mktcap_v,
        total_liabilities=sf(bal.get("totalLiabilities")),
        revenue=sf(inc.get("revenue")),
    )

    scores = score_svc.guru_score(
        pe_ratio=pe_v, pb_ratio=pb_v, pfcf_ratio=pfcf_v, ev_ebitda=ev_ebitda_v,
        roe=roe_v, roic=roic_v, gross_margin=gm_v, piotroski=pio,
        revenue_growth=rev_growth, eps_growth=eps_growth, fcf_growth=fcf_growth,
        de_ratio=de_v, current_ratio=cr_v, altman_z=az, beta=beta_v,
    )

    stock = db.query(Stock).filter(Stock.ticker == t).first()
    if not stock:
        stock = Stock(ticker=t)
        db.add(stock)

    stock.name = profile.get("companyName", t)
    stock.sector = profile.get("sector")
    stock.industry = profile.get("industry")
    stock.description = profile.get("description")
    stock.exchange = profile.get("exchange")
    stock.country = profile.get("country")
    stock.city = profile.get("city")
    stock.state = profile.get("state")
    stock.employees = profile.get("employees")
    stock.currency = profile.get("currency", "USD")
    stock.website = profile.get("website")
    stock.image = profile.get("image")
    stock.current_price = sf(profile.get("price"))
    stock.market_cap = mktcap_v
    stock.beta = beta_v
    stock.shares_outstanding = shares
    stock.pe_ratio = pe_v
    stock.pb_ratio = pb_v
    stock.pfcf_ratio = pfcf_v
    stock.ev_ebitda = ev_ebitda_v
    stock.ps_ratio = ps_v
    stock.peg_ratio = peg_v
    stock.roe = roe_v
    stock.roic = roic_v
    stock.roa = roa_v
    stock.gross_margin = gm_v
    stock.operating_margin = om_v
    stock.profit_margin = pm_v
    stock.revenue_growth = rev_growth
    stock.eps_growth = eps_growth
    stock.fcf_growth = fcf_growth
    stock.de_ratio = de_v
    stock.current_ratio = cr_v
    stock.quick_ratio = qr_v
    stock.interest_coverage = ic_v
    stock.dividend_yield = dy_v
    stock.payout_ratio = pr_v
    stock.insider_ownership = None
    stock.institutional_ownership = None
    stock.piotroski_score = pio
    stock.altman_z = az
    stock.guru_score = scores["guru_score"]
    stock.guru_value = scores["guru_value"]
    stock.guru_quality = scores["guru_quality"]
    stock.guru_growth = scores["guru_growth"]
    stock.guru_strength = scores["guru_strength"]
    stock.guru_risk = scores["guru_risk"]
    stock.last_updated = datetime.utcnow()

    db.commit()
    db.refresh(stock)
    return stock


@router.get("", response_model=list[StockSummary])
async def screener(
    pe_max: Optional[float] = Query(None),
    pb_max: Optional[float] = Query(None),
    pfcf_max: Optional[float] = Query(None),
    ev_ebitda_max: Optional[float] = Query(None),
    roe_min: Optional[float] = Query(None),
    roic_min: Optional[float] = Query(None),
    de_max: Optional[float] = Query(None),
    profit_margin_min: Optional[float] = Query(None),
    fcf_growth_min: Optional[float] = Query(None),
    revenue_growth_min: Optional[float] = Query(None),
    eps_growth_min: Optional[float] = Query(None),
    market_cap_min: Optional[float] = Query(None),
    market_cap_max: Optional[float] = Query(None),
    dividend_yield_min: Optional[float] = Query(None),
    insider_ownership_min: Optional[float] = Query(None),
    piotroski_min: Optional[int] = Query(None),
    altman_z_min: Optional[float] = Query(None),
    sector: Optional[str] = Query(None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    conditions = []
    if pe_max is not None:
        conditions.append(Stock.pe_ratio <= pe_max)
    if pb_max is not None:
        conditions.append(Stock.pb_ratio <= pb_max)
    if pfcf_max is not None:
        conditions.append(Stock.pfcf_ratio <= pfcf_max)
    if ev_ebitda_max is not None:
        conditions.append(Stock.ev_ebitda <= ev_ebitda_max)
    if roe_min is not None:
        conditions.append(Stock.roe >= roe_min)
    if roic_min is not None:
        conditions.append(Stock.roic >= roic_min)
    if de_max is not None:
        conditions.append(Stock.de_ratio <= de_max)
    if profit_margin_min is not None:
        conditions.append(Stock.profit_margin >= profit_margin_min)
    if fcf_growth_min is not None:
        conditions.append(Stock.fcf_growth >= fcf_growth_min)
    if revenue_growth_min is not None:
        conditions.append(Stock.revenue_growth >= revenue_growth_min)
    if eps_growth_min is not None:
        conditions.append(Stock.eps_growth >= eps_growth_min)
    if market_cap_min is not None:
        conditions.append(Stock.market_cap >= market_cap_min)
    if market_cap_max is not None:
        conditions.append(Stock.market_cap <= market_cap_max)
    if dividend_yield_min is not None:
        conditions.append(Stock.dividend_yield >= dividend_yield_min)
    if piotroski_min is not None:
        conditions.append(Stock.piotroski_score >= piotroski_min)
    if altman_z_min is not None:
        conditions.append(Stock.altman_z >= altman_z_min)
    if sector:
        conditions.append(Stock.sector == sector)

    query = db.query(Stock)
    if conditions:
        query = query.filter(and_(*conditions))

    stocks = (
        query.order_by(Stock.guru_score.desc().nullslast())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [StockSummary.model_validate(s) for s in stocks]


@router.get("/search")
async def search_stocks(q: str = Query("", min_length=1), db: Session = Depends(get_db)):
    """Return up to 10 symbol suggestions for autocomplete."""
    if not q or len(q.strip()) < 1:
        return []

    term = q.strip().upper()
    cache_key = cache.make_key("search", q=term)
    if cached := cache.cache_get(cache_key):
        return cached

    # 1. Local DB — fast, prioritise exact ticker prefix
    db_hits = (
        db.query(Stock.ticker, Stock.name, Stock.sector, Stock.exchange)
        .filter(or_(
            Stock.ticker.ilike(f"{term}%"),
            Stock.name.ilike(f"%{term}%"),
        ))
        .order_by(Stock.guru_score.desc().nullslast())
        .limit(5)
        .all()
    )
    local = [
        {"symbol": r.ticker, "name": r.name or r.ticker,
         "exchange": r.exchange or "", "sector": r.sector or "",
         "in_db": True}
        for r in db_hits
    ]
    local_symbols = {r["symbol"] for r in local}

    # 2. yfinance Search — fills gaps not in DB
    try:
        loop = asyncio.get_event_loop()
        yf_results = await loop.run_in_executor(
            None, functools.partial(_yf_search, q.strip(), 10)
        )
        for hit in yf_results:
            if hit["symbol"] not in local_symbols:
                local.append(hit)
    except Exception:
        pass

    results = local[:10]
    cache.cache_set(cache_key, results, ttl=300)
    return results


def _yf_search(query: str, max_results: int) -> list[dict]:
    try:
        r = yf.Search(query, max_results=max_results)
        out = []
        for q in r.quotes:
            if q.get("quoteType") not in ("EQUITY", "ETF", "INDEX"):
                continue
            sym  = q.get("symbol", "")
            name = (q.get("shortname") or q.get("longname") or sym).strip()
            exch = q.get("exchange", "")
            if sym:
                out.append({"symbol": sym, "name": name,
                            "exchange": exch, "sector": "", "in_db": False})
        return out
    except Exception:
        return []


@router.get("/{ticker}/segments")
async def get_segments(ticker: str):
    """Return revenue breakdown by product segment and geography (5 years)."""
    t = ticker.upper()
    cache_key = cache.make_key("segments", ticker=t)
    cached = cache.cache_get(cache_key)
    if cached:
        return cached

    product_raw, geo_raw = await asyncio.gather(
        fmp.get_product_segments(t),
        fmp.get_geographic_segments(t),
    )

    def _normalize(raw: list, limit: int = 5) -> list:
        result = []
        for item in raw:
            # New FMP format: {"date": "YYYY-MM-DD", "data": {segment: value, ...}}
            # Old FMP format: {"YYYY-MM-DD": {segment: value, ...}}
            if isinstance(item.get("data"), dict):
                entries = [((item.get("date") or "")[:4], item["data"])]
            else:
                entries = [(k[:4], v) for k, v in item.items() if isinstance(v, dict)]
            for date_str, seg_dict in entries:
                total = sum(v for v in seg_dict.values() if isinstance(v, (int, float)))
                segments = [
                    {
                        "name": k,
                        "value": round(v / 1e9, 2),
                        "pct": round(v / total * 100, 2) if total else 0,
                    }
                    for k, v in sorted(seg_dict.items(), key=lambda x: -x[1])
                    if isinstance(v, (int, float))
                ]
                result.append({
                    "date": date_str,
                    "segments": segments,
                    "total": round(total / 1e9, 2),
                })
        result.sort(key=lambda x: x["date"], reverse=True)
        return result[:limit]

    result = {
        "product": _normalize(product_raw),
        "geographic": _normalize(geo_raw),
    }
    cache.cache_set(cache_key, result, ttl=86400)
    return result


@router.get("/{ticker}/multiples-history")
async def get_multiples_history(ticker: str):
    """Return historical valuation multiples with 5Y and 10Y averages."""
    t = ticker.upper()
    cache_key = cache.make_key("multiples_hist", ticker=t)
    cached = cache.cache_get(cache_key)
    if cached:
        return cached

    ratios = await fmp.get_ratios(t, limit=10)

    def _avg(key, records):
        vals = [fmp.safe_float(r.get(key)) for r in records]
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    history = [
        {
            "year": (r.get("date") or "")[:4],
            "pe":        fmp.safe_float(r.get("priceToEarningsRatio")),
            "pb":        fmp.safe_float(r.get("priceToBookRatio")),
            "pfcf":      fmp.safe_float(r.get("priceToFreeCashFlowRatio")),
            "ev_ebitda": fmp.safe_float(r.get("enterpriseValueMultiple")),
            "ps":        fmp.safe_float(r.get("priceToSalesRatio")),
        }
        for r in ratios
    ]

    keys = ["priceToEarningsRatio", "priceToBookRatio", "priceToFreeCashFlowRatio",
            "enterpriseValueMultiple", "priceToSalesRatio"]
    short = ["pe", "pb", "pfcf", "ev_ebitda", "ps"]

    def _avg_block(records):
        return {s: _avg(k, records) for k, s in zip(keys, short)}

    result = {
        "history": history,
        "avg_5y":  _avg_block(ratios[:5]),
        "avg_10y": _avg_block(ratios),
    }
    cache.cache_set(cache_key, result, ttl=86400)
    return result


@router.get("/{ticker}", response_model=StockDetail)
async def stock_detail(ticker: str, force: bool = Query(False), db: Session = Depends(get_db)):
    t = ticker.upper()
    cache_key = cache.make_key("stock_detail", ticker=t)

    if not force:
        cached = cache.cache_get(cache_key)
        if cached:
            return cached

    stock = db.query(Stock).filter(Stock.ticker == t).first()
    stale = (
        force
        or stock is None
        or stock.last_updated is None
        or (datetime.utcnow() - stock.last_updated) > timedelta(hours=24)
    )

    if stale:
        stock = await _refresh_stock(t, db)

    result = StockDetail.model_validate(stock)
    cache.cache_set(cache_key, result.model_dump(), ttl=86400)
    return result


@router.post("/seed", status_code=202)
async def seed_stocks(db: Session = Depends(get_db)):
    """Fetch and store a curated list of popular stocks into the local DB."""
    results = {"success": [], "failed": []}
    for ticker in SEED_TICKERS:
        try:
            await _refresh_stock(ticker, db)
            results["success"].append(ticker)
        except Exception as e:
            results["failed"].append({"ticker": ticker, "error": str(e)})
    return results
