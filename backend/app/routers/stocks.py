import asyncio
import functools
import logging
from collections import defaultdict
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
from ..services.dcf_calculator import run_dcf
from .financials import _build_record

router = APIRouter()
_log = logging.getLogger(__name__)


def _yoy(cur, prev):
    """Year-over-year growth rate; returns None when inputs are missing or prev is zero."""
    if cur is not None and prev and prev != 0:
        return (cur - prev) / abs(prev)
    return None


def _derive_missing_metrics(
    *,
    revenue=None, gross_profit=None, op_income=None, net_income=None, ebitda=None,
    equity=None, assets=None, debt=None, ca=None, cl=None, inv=0.0, ltd=None,
    cash=0.0, fcf=None, int_exp=None,
    price=None, mktcap=None, shares=None, eps=None,
    rev_prev=None, eps_prev=None, fcf_prev=None,
) -> dict:
    """Compute financial metrics from raw float values.
    Returns a dict containing only keys where the result is computable.
    Used as a fallback when FMP /ratios or /key-metrics are unavailable.
    """
    out = {}
    inv = inv or 0.0
    cash = cash or 0.0

    if gross_profit and revenue and revenue > 0:
        out["gross_margin"] = gross_profit / revenue
    if op_income and revenue and revenue > 0:
        out["operating_margin"] = op_income / revenue
    if net_income is not None and revenue and revenue > 0:
        out["profit_margin"] = net_income / revenue
    if net_income is not None and equity and equity > 0:
        out["roe"] = net_income / equity
    if net_income is not None and assets and assets > 0:
        out["roa"] = net_income / assets
    if net_income is not None and equity and ltd is not None:
        invested = (equity or 0) + (ltd or 0)
        if invested > 0:
            out["roic"] = net_income / invested
    if debt is not None and equity and equity > 0:
        out["de_ratio"] = debt / abs(equity)
    if ca and cl and cl > 0:
        out["current_ratio"] = ca / cl
    if ca is not None and cl and cl > 0:
        out["quick_ratio"] = (ca - inv) / cl
    if op_income and int_exp and int_exp != 0:
        out["interest_coverage"] = op_income / abs(int_exp)

    if price and shares and shares > 0:
        _eps = net_income / shares if net_income is not None else eps
        bvps = equity / shares if equity else None
        fcf_ps = fcf / shares if fcf is not None else None
        if _eps and _eps > 0:
            out["pe_ratio"] = price / _eps
        if bvps and bvps > 0:
            out["pb_ratio"] = price / bvps
        if revenue and revenue > 0:
            out["ps_ratio"] = (price * shares) / revenue
        if fcf_ps and fcf_ps > 0:
            out["pfcf_ratio"] = price / fcf_ps

    if mktcap and ebitda and ebitda > 0:
        ev = mktcap + (debt or 0) - cash
        out["ev_ebitda"] = ev / ebitda

    if (g := _yoy(revenue, rev_prev)) is not None:
        out["revenue_growth"] = g
    if (g := _yoy(eps, eps_prev)) is not None:
        out["eps_growth"] = g
    if (g := _yoy(fcf, fcf_prev)) is not None:
        out["fcf_growth"] = g

    return out

# Curated list for seeding — fetched on demand via POST /api/stocks/seed
SEED_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "BRK-B", "JPM", "V", "JNJ",
    "UNH", "XOM", "PG", "MA", "HD", "CVX", "ABBV", "MRK", "LLY", "PEP",
    "KO", "AVGO", "COST", "WMT", "TMO", "BAC", "CSCO", "ACN", "MCD", "ADBE",
    "ORCL", "CRM", "INTC", "NFLX", "DIS", "VZ", "CMCSA", "WFC", "BMY", "AMGN",
]


async def _refresh_stock(ticker: str, db: Session) -> Stock:
    t = ticker.upper()

    # Fetch all primary data in parallel; use limit=10 for ratios so multiples-history can reuse them
    profile, ratios, growth, metrics, income, balance, cashflow = await asyncio.gather(
        fmp.get_profile(t),
        fmp.get_ratios(t, limit=10),
        fmp.get_financial_growth(t, limit=1),
        fmp.get_key_metrics(t, limit=1),
        fmp.get_income_statement(t, limit=5),
        fmp.get_balance_sheet(t, limit=5),
        fmp.get_cash_flow(t, limit=5),
    )

    # Cache raw ratios so the multiples-history endpoint can reuse them without an extra FMP call
    if ratios:
        cache.cache_set(cache.make_key("ratios_raw", ticker=t), ratios, ttl=86400)

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
    eps_growth = sf(g.get("epsGrowth") or g.get("epsgrowth") or g.get("epsDilutedGrowth"))
    fcf_growth = sf(g.get("freeCashFlowGrowth"))

    shares = sf(inc.get("weightedAverageShsOutDil") or inc.get("weightedAverageShsOut"))

    # Match cashflow rows by date to avoid index misalignment between independent API lists
    cf_by_date = {r.get("date"): r for r in cashflow}
    cf_prev = cf_by_date.get(inc_prev.get("date"), {}) if inc_prev else {}

    fb = _derive_missing_metrics(
        revenue=sf(inc.get("revenue")),
        gross_profit=sf(inc.get("grossProfit")),
        op_income=sf(inc.get("operatingIncome")),
        net_income=sf(inc.get("netIncome")),
        ebitda=sf(inc.get("ebitda")),
        equity=sf(bal.get("totalStockholdersEquity") or bal.get("totalEquity")),
        assets=sf(bal.get("totalAssets")),
        debt=sf(bal.get("totalDebt")),
        ca=sf(bal.get("totalCurrentAssets")),
        cl=sf(bal.get("totalCurrentLiabilities")),
        inv=sf(bal.get("inventory")) or 0,
        ltd=sf(bal.get("longTermDebt")),
        cash=sf(bal.get("cashAndCashEquivalents")) or 0,
        fcf=sf(cf.get("freeCashFlow")),
        int_exp=sf(inc.get("interestExpense")),
        price=sf(profile.get("price")),
        mktcap=mktcap_v,
        shares=shares,
        eps=sf(inc.get("eps") or inc.get("epsDiluted")),
        rev_prev=sf(inc_prev.get("revenue")) if inc_prev else None,
        eps_prev=sf(inc_prev.get("eps") or inc_prev.get("epsDiluted")) if inc_prev else None,
        fcf_prev=sf(cf_prev.get("freeCashFlow")),
    )

    # Apply fallback values only where primary sources returned None
    if gm_v is None:        gm_v        = fb.get("gross_margin")
    if om_v is None:        om_v        = fb.get("operating_margin")
    if pm_v is None:        pm_v        = fb.get("profit_margin")
    if roe_v is None:       roe_v       = fb.get("roe")
    if roa_v is None:       roa_v       = fb.get("roa")
    if roic_v is None:      roic_v      = fb.get("roic")
    if de_v is None:        de_v        = fb.get("de_ratio")
    if cr_v is None:        cr_v        = fb.get("current_ratio")
    if qr_v is None:        qr_v        = fb.get("quick_ratio")
    if ic_v is None:        ic_v        = fb.get("interest_coverage")
    if pe_v is None:        pe_v        = fb.get("pe_ratio")
    if pb_v is None:        pb_v        = fb.get("pb_ratio")
    if ps_v is None:        ps_v        = fb.get("ps_ratio")
    if pfcf_v is None:      pfcf_v      = fb.get("pfcf_ratio")
    if ev_ebitda_v is None: ev_ebitda_v = fb.get("ev_ebitda")
    if rev_growth is None:  rev_growth  = fb.get("revenue_growth")
    if eps_growth is None:  eps_growth  = fb.get("eps_growth")
    if fcf_growth is None:  fcf_growth  = fb.get("fcf_growth")

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

    # Compute default DCF upside (10% growth, 10% discount, 3% terminal, 10yr) and cache on stock
    try:
        base_fcf = sf(cf.get("freeCashFlow"))
        if base_fcf and shares and shares > 0 and sf(profile.get("price")):
            dcf_result = run_dcf(
                ticker=t,
                base_fcf=base_fcf,
                current_price=sf(profile.get("price")),
                shares_outstanding=shares,
                growth_rate=0.10,
                terminal_growth=0.03,
                discount_rate=0.10,
                years=10,
            )
            stock.dcf_upside = dcf_result.upside_downside
        else:
            stock.dcf_upside = None
    except Exception:
        stock.dcf_upside = None

    stock.last_updated = datetime.utcnow()

    db.commit()
    db.refresh(stock)

    # Populate Financial table so charts and DCF work without a separate API call

    def _seed_financials(period_label, inc_rows, bal_rows, cf_rows):
        bal_by_date = {r.get("date"): r for r in bal_rows}
        bal_by_year = {r.get("date", "")[:4]: r for r in reversed(bal_rows) if r.get("date")}
        cf_by_date  = {r.get("date"): r for r in cf_rows}
        cf_by_year  = {r.get("date", "")[:4]: r for r in reversed(cf_rows) if r.get("date")}
        db.query(Financial).filter(Financial.ticker == t, Financial.period == period_label).delete()
        for inc in inc_rows:
            d = inc.get("date") or ""
            b = bal_by_date.get(d) or bal_by_year.get(d[:4], {})
            c = cf_by_date.get(d)  or cf_by_year.get(d[:4], {})
            db.add(_build_record(t, period_label, inc, b, c))
        db.commit()

    try:
        _seed_financials("annual", income, balance, cashflow)
    except Exception as exc:
        _log.warning("Annual financial seed failed for %s: %s", t, exc)

    try:
        inc_q, bal_q, cf_q = await asyncio.gather(
            fmp.get_income_statement(t, limit=20, period="quarter"),
            fmp.get_balance_sheet(t,     limit=20, period="quarter"),
            fmp.get_cash_flow(t,          limit=20, period="quarter"),
        )
        _seed_financials("quarter", inc_q, bal_q, cf_q)
    except Exception as exc:
        _log.warning("Quarterly financial seed failed for %s: %s", t, exc)

    return stock


# Secondary class → primary class; drop secondary when primary is also present
_SHADOW_TO_PRIMARY: dict[str, str] = {
    "GOOG":  "GOOGL",   # Alphabet C (no vote) → A (voting)
    "BRK.A": "BRK.B",   # Berkshire A → B (more accessible)
    "FOX":   "FOXA",    # Fox C → A
    "NWS":   "NWSA",    # News Corp B → A
    "LEN.B": "LEN",     # Lennar B → A
    "PARAA": "PARA",    # Paramount A → B
    "CMCSK": "CMCSA",   # Comcast K → A
    "LSXMB": "LSXMA",
    "LSXMK": "LSXMA",
    "BATRK": "BATRA",
}


def _dedup(stocks: list) -> list:
    tickers_in_result = {s.ticker for s in stocks}
    return [
        s for s in stocks
        if s.ticker not in _SHADOW_TO_PRIMARY
        or _SHADOW_TO_PRIMARY[s.ticker] not in tickers_in_result
    ]


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
    return _dedup([StockSummary.model_validate(s) for s in stocks])


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

    # 2. FMP search — reliable, covers virtually all listed equities
    try:
        fmp_results = await fmp.search(q.strip(), limit=10)
        for hit in fmp_results:
            if hit["symbol"] not in local_symbols:
                local.append(hit)
                local_symbols.add(hit["symbol"])
    except Exception:
        pass

    # 3. yfinance Search — extra fallback for any remaining gaps
    if len(local) < 5:
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

    # Reuse ratios already fetched during stock refresh (saves 1 FMP call)
    ratios_cache_key = cache.make_key("ratios_raw", ticker=t)
    ratios = cache.cache_get(ratios_cache_key)
    if not ratios:
        ratios = await fmp.get_ratios(t, limit=10)
        if ratios:
            cache.cache_set(ratios_cache_key, ratios, ttl=86400)

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


@router.post("/rescore", status_code=200)
async def rescore_all_stocks(db: Session = Depends(get_db)):
    """Recompute GuruScore for every stock using existing DB data — no FMP calls.
    Fills in missing metrics from the Financial table, then bulk-clears Redis caches.
    """
    stocks = db.query(Stock).all()

    # Bulk-load all annual Financial rows (1 query instead of N)
    all_ann = (
        db.query(Financial)
        .filter(Financial.period == "annual")
        .order_by(Financial.ticker, Financial.date.desc())
        .all()
    )
    fin_by_ticker: dict[str, list[Financial]] = defaultdict(list)
    for f in all_ann:
        if len(fin_by_ticker[f.ticker]) < 2:
            fin_by_ticker[f.ticker].append(f)

    for stock in stocks:
        t = stock.ticker
        ann  = fin_by_ticker.get(t, [])
        cur  = ann[0] if ann else None
        prev = ann[1] if len(ann) >= 2 else None

        fb = _derive_missing_metrics(
            revenue=cur.revenue if cur else None,
            gross_profit=cur.gross_profit if cur else None,
            op_income=cur.operating_income if cur else None,
            net_income=cur.net_income if cur else None,
            ebitda=cur.ebitda if cur else None,
            equity=cur.total_equity if cur else None,
            assets=cur.total_assets if cur else None,
            debt=cur.total_debt if cur else None,
            ca=cur.current_assets if cur else None,
            cl=cur.current_liabilities if cur else None,
            inv=cur.inventory or 0 if cur else 0,
            ltd=cur.long_term_debt if cur else None,
            cash=cur.cash or 0 if cur else 0,
            fcf=cur.fcf if cur else None,
            price=stock.current_price,
            mktcap=stock.market_cap,
            shares=cur.shares_outstanding if cur else None,
            eps=cur.eps if cur else None,
            rev_prev=prev.revenue if prev else None,
            eps_prev=prev.eps if prev else None,
            fcf_prev=prev.fcf if prev else None,
        )

        # Apply fallback values only where existing data is missing
        stock.pe_ratio         = stock.pe_ratio         or fb.get("pe_ratio")
        stock.pb_ratio         = stock.pb_ratio         or fb.get("pb_ratio")
        stock.pfcf_ratio       = stock.pfcf_ratio       or fb.get("pfcf_ratio")
        stock.ps_ratio         = stock.ps_ratio         or fb.get("ps_ratio")
        stock.ev_ebitda        = stock.ev_ebitda        or fb.get("ev_ebitda")
        stock.roe              = stock.roe              or fb.get("roe")
        stock.roic             = stock.roic             or fb.get("roic")
        stock.roa              = stock.roa              or fb.get("roa")
        stock.gross_margin     = stock.gross_margin     or fb.get("gross_margin")
        stock.operating_margin = stock.operating_margin or fb.get("operating_margin")
        stock.profit_margin    = stock.profit_margin    or fb.get("profit_margin")
        stock.de_ratio         = stock.de_ratio         or fb.get("de_ratio")
        stock.current_ratio    = stock.current_ratio    or fb.get("current_ratio")
        stock.quick_ratio      = stock.quick_ratio      or fb.get("quick_ratio")
        stock.interest_coverage= stock.interest_coverage or fb.get("interest_coverage")
        stock.revenue_growth   = stock.revenue_growth   or fb.get("revenue_growth")
        stock.eps_growth       = stock.eps_growth       or fb.get("eps_growth")
        stock.fcf_growth       = stock.fcf_growth       or fb.get("fcf_growth")

        scores = score_svc.guru_score(
            pe_ratio=stock.pe_ratio, pb_ratio=stock.pb_ratio,
            pfcf_ratio=stock.pfcf_ratio, ev_ebitda=stock.ev_ebitda,
            roe=stock.roe, roic=stock.roic, gross_margin=stock.gross_margin,
            piotroski=stock.piotroski_score,
            revenue_growth=stock.revenue_growth, eps_growth=stock.eps_growth,
            fcf_growth=stock.fcf_growth, de_ratio=stock.de_ratio,
            current_ratio=stock.current_ratio, altman_z=stock.altman_z,
            beta=stock.beta,
        )
        stock.guru_score    = scores["guru_score"]
        stock.guru_value    = scores["guru_value"]
        stock.guru_quality  = scores["guru_quality"]
        stock.guru_growth   = scores["guru_growth"]
        stock.guru_strength = scores["guru_strength"]
        stock.guru_risk     = scores["guru_risk"]

    db.commit()

    # Bulk-delete all cache keys in a single Redis call
    cache_keys = [
        cache.make_key(pfx, ticker=s.ticker)
        for s in stocks
        for pfx in ("stock_detail", "analysis", "multiples_hist")
    ] + [
        cache.make_key("financials", ticker=s.ticker, period=p)
        for s in stocks
        for p in ("annual", "quarter")
    ]
    cache.cache_delete_many(*cache_keys)

    return {"updated": len(stocks), "message": f"Rescored {len(stocks)} stocks and cleared their caches."}
