"""Polygon.io data provider — free tier fallback for financial statements."""
import httpx
import logging
from typing import Any, Optional

_log = logging.getLogger(__name__)
BASE = "https://api.polygon.io"


async def _get(path: str, api_key: str, **kwargs) -> Any:
    async with httpx.AsyncClient(timeout=15.0) as client:
        params = {"apiKey": api_key, **kwargs}
        r = await client.get(f"{BASE}{path}", params=params)
        r.raise_for_status()
        return r.json()


def _val(obj: dict, key: str) -> Optional[float]:
    v = obj.get(key)
    if isinstance(v, dict):
        return v.get("value")
    return None


async def get_profile(ticker: str, api_key: str) -> dict:
    try:
        details = await _get(f"/v3/reference/tickers/{ticker.upper()}", api_key)
        r = details.get("results", {})
        if not r.get("name"):
            return {}
        # Snapshot is best-effort — price may be missing on free tier
        price = None
        try:
            snap_data = await _get(
                f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker.upper()}", api_key
            )
            snap = snap_data.get("ticker", {})
            price = snap.get("day", {}).get("c") or snap.get("lastTrade", {}).get("p")
        except Exception:
            pass
        return {
            "companyName":  r.get("name", ""),
            "sector":       r.get("sic_description", ""),
            "industry":     r.get("sic_description", ""),
            "description":  r.get("description", ""),
            "exchange":     r.get("primary_exchange", ""),
            "country":      (r.get("locale") or "us").upper(),
            "city":         (r.get("address") or {}).get("city"),
            "state":        (r.get("address") or {}).get("state"),
            "employees":    r.get("total_employees"),
            "currency":     (r.get("currency_name") or "usd").upper(),
            "website":      r.get("homepage_url"),
            "image":        (r.get("branding") or {}).get("icon_url"),
            "price":        price,
            "marketCap":    r.get("market_cap"),
            "beta":         None,
        }
    except Exception as exc:
        _log.warning("Polygon profile failed for %s: %s", ticker, exc)
        return {}


async def _get_financials(ticker: str, api_key: str, limit: int = 5, period: str = "annual") -> list[dict]:
    timeframe = "annual" if period == "annual" else "quarterly"
    try:
        data = await _get(
            "/vX/reference/financials",
            api_key,
            ticker=ticker.upper(),
            timeframe=timeframe,
            limit=limit,
            order="desc",
        )
        return data.get("results", [])
    except Exception as exc:
        _log.warning("Polygon financials failed for %s: %s", ticker, exc)
        return []


async def get_income_statement(ticker: str, api_key: str, limit: int = 5, period: str = "annual") -> list[dict]:
    rows = await _get_financials(ticker, api_key, limit=limit, period=period)
    result = []
    for row in rows:
        inc = row.get("financials", {}).get("income_statement", {})
        bal = row.get("financials", {}).get("balance_sheet", {})
        rev   = _val(inc, "revenues")
        gp    = _val(inc, "gross_profit")
        ni    = _val(inc, "net_income_loss")
        oi    = _val(inc, "operating_income_loss")
        ebitda= _val(inc, "ebitda")
        eps   = _val(inc, "diluted_earnings_per_share") or _val(inc, "basic_earnings_per_share")
        shr   = _val(inc, "diluted_average_shares") or _val(inc, "basic_average_shares")
        result.append({
            "date":                       row.get("end_date", ""),
            "fiscalYear":                 str(row.get("fiscal_year", ""))[:4],
            "revenue":                    rev,
            "grossProfit":                gp,
            "netIncome":                  ni,
            "operatingIncome":            oi,
            "ebitda":                     ebitda,
            "eps":                        eps,
            "epsDiluted":                 eps,
            "weightedAverageShsOutDil":   shr,
            "dividendPerShare":           None,
        })
    return result


async def get_balance_sheet(ticker: str, api_key: str, limit: int = 5, period: str = "annual") -> list[dict]:
    rows = await _get_financials(ticker, api_key, limit=limit, period=period)
    result = []
    for row in rows:
        bal = row.get("financials", {}).get("balance_sheet", {})
        result.append({
            "date":                        row.get("end_date", ""),
            "totalAssets":                 _val(bal, "assets"),
            "totalLiabilities":            _val(bal, "liabilities"),
            "totalStockholdersEquity":     _val(bal, "equity"),
            "totalEquity":                 _val(bal, "equity"),
            "totalDebt":                   _val(bal, "long_term_debt"),
            "cashAndCashEquivalents":      _val(bal, "cash"),
            "totalCurrentAssets":          _val(bal, "current_assets"),
            "totalCurrentLiabilities":     _val(bal, "current_liabilities"),
            "retainedEarnings":            _val(bal, "retained_earnings"),
            "longTermDebt":                _val(bal, "long_term_debt"),
            "shortTermDebt":               _val(bal, "current_liabilities"),
            "netDebt":                     None,
            "inventory":                   _val(bal, "inventory"),
            "propertyPlantEquipmentNet":   _val(bal, "fixed_assets"),
        })
    return result


async def get_cash_flow(ticker: str, api_key: str, limit: int = 5, period: str = "annual") -> list[dict]:
    rows = await _get_financials(ticker, api_key, limit=limit, period=period)
    result = []
    for row in rows:
        cf = row.get("financials", {}).get("cash_flow_statement", {})
        ocf   = _val(cf, "net_cash_flow_from_operating_activities")
        capex = _val(cf, "capital_expenditure") or _val(cf, "net_cash_flow_from_investing_activities")
        fcf   = _val(cf, "free_cash_flow")
        if fcf is None and ocf is not None and capex is not None:
            fcf = ocf + capex
        result.append({
            "date":                row.get("end_date", ""),
            "operatingCashFlow":   ocf,
            "capitalExpenditure":  capex,
            "freeCashFlow":        fcf,
        })
    return result


async def get_ratios(ticker: str, api_key: str, limit: int = 5) -> list[dict]:
    """Basic ratios from Polygon snapshot (current) — historical not available on free tier."""
    try:
        snap_data = await _get(
            f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker.upper()}", api_key
        )
        snap = snap_data.get("ticker", {})
        price = snap.get("day", {}).get("c") or snap.get("lastTrade", {}).get("p")
        if not price:
            return []
        # Polygon free tier doesn't provide fundamental ratios directly —
        # return empty so yfinance/FMP handle it
        return []
    except Exception:
        return []


async def get_key_metrics(ticker: str, api_key: str, limit: int = 1) -> list[dict]:
    return []


async def get_financial_growth(ticker: str, api_key: str, limit: int = 1) -> list[dict]:
    return []
