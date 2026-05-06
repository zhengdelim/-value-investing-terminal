"""yfinance fallback data provider — used when FMP quota is exhausted."""
import asyncio
import functools
from typing import Any, Optional
from urllib.parse import urlparse
import pandas as pd
import yfinance as yf


def _run_sync(fn, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, functools.partial(fn, *args, **kwargs))


def _ticker_info(symbol: str) -> dict:
    return yf.Ticker(symbol).info or {}


def _row(df, *keys):
    """Get first matching key from a DataFrame index."""
    for k in keys:
        if k in df.index:
            return df.loc[k]
    return {}


def _income(symbol: str) -> list[dict]:
    t = yf.Ticker(symbol)
    df = t.financials
    if df is None or df.empty:
        return []
    rev_row = _row(df, "Total Revenue", "Operating Revenue")
    gp_row  = _row(df, "Gross Profit")
    ni_row  = _row(df, "Net Income", "Net Income Common Stockholders")
    oi_row  = _row(df, "Operating Income", "Total Operating Income As Reported")
    eb_row  = _row(df, "EBITDA", "Normalized EBITDA")
    eps_row = _row(df, "Diluted EPS")
    shr_row = _row(df, "Diluted Average Shares")
    dps_row = _row(df, "Cash Dividends Paid")  # yfinance uses this; convert to per-share below
    result = []
    for col in df.columns[:10]:
        shr = _safe(shr_row.get(col))
        div_paid = _safe(dps_row.get(col))
        # div_paid is negative (cash outflow); divide by shares to get per-share amount
        dps = abs(div_paid / shr) if (div_paid and shr and shr > 0) else None
        result.append({
            "date": str(col)[:10],
            "revenue": _safe(rev_row.get(col)),
            "grossProfit": _safe(gp_row.get(col)),
            "netIncome": _safe(ni_row.get(col)),
            "operatingIncome": _safe(oi_row.get(col)),
            "ebitda": _safe(eb_row.get(col)),
            "eps": _safe(eps_row.get(col)),
            "epsDiluted": _safe(eps_row.get(col)),
            "weightedAverageShsOutDil": shr,
            "dividendPerShare": dps,
            "fiscalYear": str(col)[:4],
        })
    return result


def _balance(symbol: str) -> list[dict]:
    t = yf.Ticker(symbol)
    df = t.balance_sheet
    if df is None or df.empty:
        return []
    ta_row  = _row(df, "Total Assets")
    tl_row  = _row(df, "Total Liabilities Net Minority Interest")
    eq_row  = _row(df, "Stockholders Equity", "Common Stock Equity")
    td_row  = _row(df, "Total Debt")
    ca_row  = _row(df, "Current Assets")
    cl_row  = _row(df, "Current Liabilities")
    re_row  = _row(df, "Retained Earnings")
    ltd_row = _row(df, "Long Term Debt", "Long Term Debt And Capital Lease Obligation")
    std_row = _row(df, "Current Debt", "Current Debt And Capital Lease Obligation")
    nd_row  = _row(df, "Net Debt")
    cash_row= _row(df, "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments")
    inv_row = _row(df, "Inventory")
    ppe_row = _row(df, "Net PPE", "Properties")
    result = []
    for col in df.columns[:10]:
        result.append({
            "date": str(col)[:10],
            "totalAssets": _safe(ta_row.get(col)),
            "totalLiabilities": _safe(tl_row.get(col)),
            "totalStockholdersEquity": _safe(eq_row.get(col)),
            "totalEquity": _safe(eq_row.get(col)),
            "totalDebt": _safe(td_row.get(col)),
            "cashAndCashEquivalents": _safe(cash_row.get(col)),
            "totalCurrentAssets": _safe(ca_row.get(col)),
            "totalCurrentLiabilities": _safe(cl_row.get(col)),
            "retainedEarnings": _safe(re_row.get(col)),
            "longTermDebt": _safe(ltd_row.get(col)),
            "shortTermDebt": _safe(std_row.get(col)),
            "netDebt": _safe(nd_row.get(col)),
            "inventory": _safe(inv_row.get(col)),
            "propertyPlantEquipmentNet": _safe(ppe_row.get(col)),
        })
    return result


def _cashflow(symbol: str) -> list[dict]:
    t = yf.Ticker(symbol)
    df = t.cashflow
    if df is None or df.empty:
        return []
    ocf_row  = _row(df, "Operating Cash Flow", "Cash Flow From Continuing Operating Activities")
    cap_row  = _row(df, "Capital Expenditure", "Purchase Of PPE")
    fcf_row  = _row(df, "Free Cash Flow")
    result = []
    for col in df.columns[:10]:
        ocf = _safe(ocf_row.get(col))
        capex = _safe(cap_row.get(col))
        fcf = _safe(fcf_row.get(col))
        if fcf is None and ocf is not None and capex is not None:
            fcf = ocf + capex  # capex is already negative
        result.append({
            "date": str(col)[:10],
            "operatingCashFlow": ocf,
            "capitalExpenditure": capex,
            "freeCashFlow": fcf,
        })
    return result


def _safe(v) -> Optional[float]:
    try:
        f = float(v)
        return None if (f != f) else f  # NaN check
    except Exception:
        return None


async def get_profile(ticker: str) -> dict:
    info = await _run_sync(_ticker_info, ticker.upper())
    return _map_profile(info)


def _historical_ratios(symbol: str) -> list[dict]:
    t = yf.Ticker(symbol)
    inc_df = t.financials
    bal_df = t.balance_sheet

    if inc_df is None or inc_df.empty:
        return []

    try:
        tz = None
        hist = t.history(period="10y")
        if not hist.empty:
            tz = hist.index.tz
    except Exception:
        hist = pd.DataFrame()
        tz = None

    eps_row = _row(inc_df, "Diluted EPS")
    rev_row = _row(inc_df, "Total Revenue", "Operating Revenue")
    shr_row = _row(inc_df, "Diluted Average Shares")
    eq_row  = _row(bal_df, "Stockholders Equity", "Common Stock Equity") if bal_df is not None and not bal_df.empty else {}

    result = []
    for col in inc_df.columns[:10]:
        date_str = str(col)[:10]
        price = None
        if not hist.empty:
            try:
                ts = pd.Timestamp(date_str)
                if tz:
                    ts = ts.tz_localize(tz)
                mask = hist.index <= ts
                if mask.any():
                    price = float(hist[mask]["Close"].iloc[-1])
            except Exception:
                pass

        eps    = _safe(eps_row.get(col)) if isinstance(eps_row, pd.Series) else None
        rev    = _safe(rev_row.get(col)) if isinstance(rev_row, pd.Series) else None
        shares = _safe(shr_row.get(col)) if isinstance(shr_row, pd.Series) else None
        equity = _safe(eq_row.get(col))  if isinstance(eq_row,  pd.Series) else None

        pe   = round(price / eps,    2) if price and eps    and eps    > 0 else None
        bvps = equity / shares             if equity and shares and shares > 0 else None
        pb   = round(price / bvps,   2) if price and bvps and bvps > 0 else None
        ps_v = round((price * shares) / rev, 2) if price and shares and rev and rev > 0 else None

        result.append({
            "date": date_str,
            "priceToEarningsRatio":        pe,
            "priceToBookRatio":            pb,
            "priceToFreeCashFlowRatio":    None,
            "enterpriseValueMultiple":     None,
            "priceToSalesRatio":           ps_v,
        })
    return result


async def get_ratios(ticker: str, limit: int = 5) -> list[dict]:
    try:
        rows = await _run_sync(_historical_ratios, ticker.upper())
        if rows:
            return rows[:limit]
    except Exception:
        pass
    try:
        info = await _run_sync(_ticker_info, ticker.upper())
        r = _map_ratios(info)
        return [r] if r else []
    except Exception:
        return []


async def get_key_metrics(ticker: str, limit: int = 1) -> list[dict]:
    try:
        info = await _run_sync(_ticker_info, ticker.upper())
        m = _map_metrics(info)
        return [m] if m else []
    except Exception:
        return []


async def get_financial_growth(ticker: str, limit: int = 1) -> list[dict]:
    try:
        info = await _run_sync(_ticker_info, ticker.upper())
        g = _map_growth(info)
        return [g] if g else []
    except Exception:
        return []


def _income_quarterly(symbol: str) -> list[dict]:
    t = yf.Ticker(symbol)
    df = t.quarterly_financials
    if df is None or df.empty:
        return []
    rev_row = _row(df, "Total Revenue", "Operating Revenue")
    gp_row  = _row(df, "Gross Profit")
    ni_row  = _row(df, "Net Income", "Net Income Common Stockholders")
    oi_row  = _row(df, "Operating Income", "Total Operating Income As Reported")
    eb_row  = _row(df, "EBITDA", "Normalized EBITDA")
    eps_row = _row(df, "Diluted EPS")
    shr_row = _row(df, "Diluted Average Shares")
    result = []
    for col in df.columns[:20]:
        shr = _safe(shr_row.get(col))
        result.append({
            "date": str(col)[:10],
            "revenue": _safe(rev_row.get(col)),
            "grossProfit": _safe(gp_row.get(col)),
            "netIncome": _safe(ni_row.get(col)),
            "operatingIncome": _safe(oi_row.get(col)),
            "ebitda": _safe(eb_row.get(col)),
            "eps": _safe(eps_row.get(col)),
            "epsDiluted": _safe(eps_row.get(col)),
            "weightedAverageShsOutDil": shr,
            "dividendPerShare": None,
            "fiscalYear": str(col)[:4],
        })
    return result


def _balance_quarterly(symbol: str) -> list[dict]:
    t = yf.Ticker(symbol)
    df = t.quarterly_balance_sheet
    if df is None or df.empty:
        return []
    ta_row  = _row(df, "Total Assets")
    tl_row  = _row(df, "Total Liabilities Net Minority Interest")
    eq_row  = _row(df, "Stockholders Equity", "Common Stock Equity")
    td_row  = _row(df, "Total Debt")
    ca_row  = _row(df, "Current Assets")
    cl_row  = _row(df, "Current Liabilities")
    re_row  = _row(df, "Retained Earnings")
    ltd_row = _row(df, "Long Term Debt", "Long Term Debt And Capital Lease Obligation")
    std_row = _row(df, "Current Debt", "Current Debt And Capital Lease Obligation")
    nd_row  = _row(df, "Net Debt")
    cash_row= _row(df, "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments")
    inv_row = _row(df, "Inventory")
    ppe_row = _row(df, "Net PPE", "Properties")
    result = []
    for col in df.columns[:20]:
        result.append({
            "date": str(col)[:10],
            "totalAssets": _safe(ta_row.get(col)),
            "totalLiabilities": _safe(tl_row.get(col)),
            "totalStockholdersEquity": _safe(eq_row.get(col)),
            "totalEquity": _safe(eq_row.get(col)),
            "totalDebt": _safe(td_row.get(col)),
            "cashAndCashEquivalents": _safe(cash_row.get(col)),
            "totalCurrentAssets": _safe(ca_row.get(col)),
            "totalCurrentLiabilities": _safe(cl_row.get(col)),
            "retainedEarnings": _safe(re_row.get(col)),
            "longTermDebt": _safe(ltd_row.get(col)),
            "shortTermDebt": _safe(std_row.get(col)),
            "netDebt": _safe(nd_row.get(col)),
            "inventory": _safe(inv_row.get(col)),
            "propertyPlantEquipmentNet": _safe(ppe_row.get(col)),
        })
    return result


def _cashflow_quarterly(symbol: str) -> list[dict]:
    t = yf.Ticker(symbol)
    df = t.quarterly_cashflow
    if df is None or df.empty:
        return []
    ocf_row = _row(df, "Operating Cash Flow", "Cash Flow From Continuing Operating Activities")
    cap_row = _row(df, "Capital Expenditure", "Purchase Of PPE")
    fcf_row = _row(df, "Free Cash Flow")
    result = []
    for col in df.columns[:20]:
        ocf = _safe(ocf_row.get(col))
        capex = _safe(cap_row.get(col))
        fcf = _safe(fcf_row.get(col))
        if fcf is None and ocf is not None and capex is not None:
            fcf = ocf + capex
        result.append({
            "date": str(col)[:10],
            "operatingCashFlow": ocf,
            "capitalExpenditure": capex,
            "freeCashFlow": fcf,
        })
    return result


async def get_income_statement(ticker: str, limit: int = 5, period: str = "annual") -> list[dict]:
    fn = _income_quarterly if period == "quarter" else _income
    return await _run_sync(fn, ticker.upper())


async def get_balance_sheet(ticker: str, limit: int = 5, period: str = "annual") -> list[dict]:
    fn = _balance_quarterly if period == "quarter" else _balance
    return await _run_sync(fn, ticker.upper())


async def get_cash_flow(ticker: str, limit: int = 5, period: str = "annual") -> list[dict]:
    fn = _cashflow_quarterly if period == "quarter" else _cashflow
    return await _run_sync(fn, ticker.upper())


# --- Field mapping helpers ---

def _map_profile(info: dict) -> dict:
    website = info.get("website") or ""
    domain = urlparse(website).netloc if website else None
    image = f"https://logo.clearbit.com/{domain}" if domain else None
    return {
        "companyName": info.get("longName") or info.get("shortName", ""),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "description": info.get("longBusinessSummary"),
        "exchange": info.get("exchange"),
        "country": info.get("country"),
        "city": info.get("city"),
        "state": info.get("state"),
        "employees": info.get("fullTimeEmployees"),
        "currency": info.get("currency", "USD"),
        "website": info.get("website"),
        "image": image,
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "marketCap": info.get("marketCap"),
        "beta": info.get("beta"),
    }


def _map_ratios(info: dict) -> dict:
    return {
        "priceToEarningsRatio": info.get("trailingPE") or info.get("forwardPE"),
        "priceToBookRatio": info.get("priceToBook"),
        "priceToFreeCashFlowRatio": info.get("priceToFreeCashflows"),
        "grossProfitMargin": info.get("grossMargins"),
        "operatingProfitMargin": info.get("operatingMargins"),
        "netProfitMargin": info.get("profitMargins"),
        "debtToEquityRatio": (info.get("debtToEquity") or 0) / 100 if info.get("debtToEquity") else None,
        "currentRatio": info.get("currentRatio"),
        "quickRatio": info.get("quickRatio"),
        "interestCoverageRatio": None,
        "dividendYield": info.get("dividendYield"),
        "dividendPayoutRatio": info.get("payoutRatio"),
        "priceToSalesRatio": info.get("priceToSalesTrailing12Months"),
        "priceToEarningsGrowthRatio": info.get("pegRatio"),
    }


def _map_metrics(info: dict) -> dict:
    roe = info.get("returnOnEquity")
    roa = info.get("returnOnAssets")
    # ROIC approximation: ROE / (1 + D/E) where D/E from yfinance is in percent
    roic = None
    de_raw = info.get("debtToEquity")
    if roe is not None and de_raw is not None:
        de_ratio = de_raw / 100.0
        roic = roe / (1 + de_ratio) if (1 + de_ratio) > 0 else None
    elif roa is not None:
        roic = roa  # fallback: ROA as a lower-bound proxy
    return {
        "returnOnEquity": roe,
        "returnOnAssets": roa,
        "returnOnInvestedCapital": roic,
        "evToEBITDA": info.get("enterpriseToEbitda"),
    }


def _map_growth(info: dict) -> dict:
    return {
        "revenueGrowth": info.get("revenueGrowth"),
        "epsgrowth": info.get("earningsGrowth"),
        "freeCashFlowGrowth": None,
    }


GURU_MAP = {
    "Berkshire Hathaway": "Warren Buffett",
    "Pershing Square": "Bill Ackman",
    "Baupost": "Seth Klarman",
    "Third Point": "Dan Loeb",
    "Greenlight": "David Einhorn",
    "Fairfax": "Prem Watsa",
    "Appaloosa": "David Tepper",
    "Gotham Asset": "Joel Greenblatt",
    "Sequoia Fund": "Sequoia Fund",
    "Longleaf": "Mason Hawkins",
    "Southeastern Asset": "Mason Hawkins",
    "Tweedy Browne": "Tweedy Browne",
    "Ariel Investments": "John Rogers",
    "First Eagle": "First Eagle",
    "Gabelli": "Mario Gabelli",
    "Markel": "Tom Gayner",
    "Parnassus": "Parnassus",
    "Diamond Hill": "Diamond Hill",
    "Oakmark": "Bill Nygren",
    "Dodge & Cox": "Dodge & Cox",
    "Weitz": "Wally Weitz",
    "Royce": "Chuck Royce",
    "Yacktman": "Donald Yacktman",
    "Pzena": "Richard Pzena",
    "Brandes": "Charles Brandes",
    "Smead": "Bill Smead",
    "FPA": "Steven Romick",
}


def _safe(val):
    try:
        import math
        return None if val is None or (isinstance(val, float) and math.isnan(val)) else val
    except Exception:
        return None


def _parse_tx_type(row) -> str | None:
    explicit = _safe(row.get("Transaction") or row.get("transactionType"))
    if explicit:
        return explicit
    text = str(row.get("Text") or "").lower()
    if "sale" in text or "sold" in text:
        return "Sale"
    if "purchase" in text or "bought" in text or "buy" in text:
        return "Purchase"
    if "award" in text or "grant" in text:
        return "Award/Grant"
    if "gift" in text:
        return "Gift"
    if "exercise" in text:
        return "Option Exercise"
    if "conversion" in text:
        return "Conversion"
    return None


def _fetch_insiders_sync(symbol: str) -> dict:
    t = yf.Ticker(symbol)
    transactions = []
    gurus = []

    try:
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=365)
        df = t.insider_transactions
        if df is not None and not df.empty:
            date_col = next((c for c in ["Start Date", "Date", "startDate"] if c in df.columns), None)
            if date_col:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                df = df[df[date_col] >= cutoff]
            for _, row in df.head(30).iterrows():
                date_val = row.get("Start Date") or row.get("Date") or row.get("startDate")
                transactions.append({
                    "name": _safe(row.get("Insider") or row.get("filerName")),
                    "position": _safe(row.get("Position") or row.get("filerRelation")),
                    "transaction_type": _parse_tx_type(row),
                    "shares": _safe(row.get("Shares") or row.get("shares")),
                    "value": _safe(row.get("Value") or row.get("value")),
                    "date": str(date_val)[:10] if date_val and str(date_val) != "NaT" else None,
                })
    except Exception:
        pass

    try:
        df = t.institutional_holders
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                holder = str(row.get("Holder") or row.get("holder") or "")
                for key, guru_name in GURU_MAP.items():
                    if key.lower() in holder.lower():
                        shares = _safe(row.get("Shares") or row.get("shares"))
                        value = _safe(row.get("Value") or row.get("value"))
                        pct = _safe(row.get("pctHeld") or row.get("% Out"))
                        date_rep = row.get("Date Reported") or row.get("reportDate")
                        gurus.append({
                            "holder": holder,
                            "guru": guru_name,
                            "shares": int(shares) if shares is not None else None,
                            "value": float(value) if value is not None else None,
                            "pct_out": float(pct) if pct is not None else None,
                            "date_reported": str(date_rep)[:10] if date_rep else None,
                        })
                        break
    except Exception:
        pass

    return {"transactions": transactions, "gurus": gurus}


async def get_insiders(ticker: str) -> dict:
    return await _run_sync(_fetch_insiders_sync, ticker.upper())
