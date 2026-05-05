from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date

from ..database import get_db
from ..models.stock import Financial
from ..schemas.stock import FinancialRecord
from ..services import fmp, cache

router = APIRouter()
_FREE_LIMIT = 10
_QUARTER_LIMIT = 20  # up to 20 quarters (~5 years)


def _build_record(ticker: str, period: str, inc: dict, bal: dict, cf: dict) -> Financial:
    sf = fmp.safe_float
    d = inc.get("date")
    revenue = sf(inc.get("revenue"))
    gross = sf(inc.get("grossProfit"))
    net = sf(inc.get("netIncome"))
    ocf = sf(cf.get("operatingCashFlow"))
    capex = sf(cf.get("capitalExpenditure"))
    fcf = sf(cf.get("freeCashFlow"))
    om_val = sf(inc.get("operatingIncome"))
    return Financial(
        ticker=ticker,
        period=period,
        date=date.fromisoformat(d) if d else None,
        calendar_year=fmp.safe_int(inc.get("fiscalYear") or (d[:4] if d else None)),
        revenue=revenue,
        gross_profit=gross,
        operating_income=om_val,
        net_income=net,
        ebitda=sf(inc.get("ebitda")),
        eps=sf(inc.get("eps")),
        eps_diluted=sf(inc.get("epsDiluted")),
        operating_cash_flow=ocf,
        capex=capex,
        fcf=fcf,
        total_assets=sf(bal.get("totalAssets")),
        total_liabilities=sf(bal.get("totalLiabilities")),
        total_equity=sf(bal.get("totalStockholdersEquity") or bal.get("totalEquity")),
        total_debt=sf(bal.get("totalDebt")),
        net_debt=sf(bal.get("netDebt")),
        cash=sf(bal.get("cashAndCashEquivalents")),
        current_assets=sf(bal.get("totalCurrentAssets")),
        current_liabilities=sf(bal.get("totalCurrentLiabilities")),
        retained_earnings=sf(bal.get("retainedEarnings")),
        long_term_debt=sf(bal.get("longTermDebt")),
        short_term_debt=sf(bal.get("shortTermDebt") or bal.get("currentPortionOfLongTermDebt")),
        inventory=sf(bal.get("inventory")),
        ppe=sf(bal.get("propertyPlantEquipmentNet")),
        dividend_per_share=sf(inc.get("dividendPerShare")),
        shares_outstanding=sf(inc.get("weightedAverageShsOutDil") or inc.get("weightedAverageShsOut")),
        gross_margin=gross / revenue if gross and revenue else None,
        operating_margin=om_val / revenue if om_val and revenue else None,
        net_margin=net / revenue if net and revenue else None,
    )


async def _upsert_financials(ticker: str, db: Session, period: str = "annual") -> None:
    t = ticker.upper()
    fmp_period = "annual" if period == "annual" else "quarter"
    limit = _FREE_LIMIT if period == "annual" else _QUARTER_LIMIT

    income = await fmp.get_income_statement(t, limit=limit, period=fmp_period)
    balance = await fmp.get_balance_sheet(t, limit=limit, period=fmp_period)
    cashflow = await fmp.get_cash_flow(t, limit=limit, period=fmp_period)

    bal_by_date = {r.get("date"): r for r in balance}
    cf_by_date = {r.get("date"): r for r in cashflow}

    db.query(Financial).filter(Financial.ticker == t, Financial.period == period).delete()

    for inc in income:
        d = inc.get("date")
        bal = bal_by_date.get(d, {})
        cf = cf_by_date.get(d, {})
        db.add(_build_record(t, period, inc, bal, cf))

    db.commit()


@router.get("/{ticker}/financials", response_model=list[FinancialRecord])
async def get_financials(
    ticker: str,
    period: str = Query(default="annual", pattern="^(annual|quarter)$"),
    db: Session = Depends(get_db),
):
    t = ticker.upper()
    cache_key = cache.make_key("financials", ticker=t, period=period)
    cached = cache.cache_get(cache_key)
    if cached:
        return cached

    limit = 5 if period == "annual" else 20
    records = (
        db.query(Financial)
        .filter(Financial.ticker == t, Financial.period == period)
        .order_by(Financial.date.desc())
        .limit(limit)
        .all()
    )

    if not records:
        try:
            await _upsert_financials(t, db, period)
            records = (
                db.query(Financial)
                .filter(Financial.ticker == t, Financial.period == period)
                .order_by(Financial.date.desc())
                .limit(limit)
                .all()
            )
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    result = [FinancialRecord.model_validate(r) for r in records]
    cache.cache_set(cache_key, [r.model_dump() for r in result], ttl=86400)
    return result
