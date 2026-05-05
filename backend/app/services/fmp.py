import httpx
import logging
from typing import Any, Optional
from ..config import get_settings
from . import yf_service as yf
from . import polygon_service as polygon

settings = get_settings()
BASE = "https://financialmodelingprep.com/stable"
_log = logging.getLogger(__name__)


def _params(**kwargs) -> dict:
    p = {"apikey": settings.fmp_api_key}
    p.update({k: v for k, v in kwargs.items() if v is not None})
    return p


def _is_quota_error(exc: httpx.HTTPStatusError) -> bool:
    if exc.response.status_code in (429, 402, 403):
        return True
    try:
        body = exc.response.json()
        if isinstance(body, dict) and "Error Message" in body:
            return True
    except Exception:
        pass
    return False


async def _get(path: str, **kwargs) -> Any:
    url = f"{BASE}{path}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, params=_params(**kwargs))
        r.raise_for_status()
        data = r.json()
        # FMP returns {"Error Message": "..."} as 200 sometimes
        if isinstance(data, dict) and "Error Message" in data:
            raise RuntimeError(f"FMP API error: {data['Error Message']}")
        return data


async def get_profile(ticker: str) -> dict:
    try:
        data = await _get("/profile", symbol=ticker.upper())
        if data:
            return data[0]
    except Exception as exc:
        _log.warning("FMP profile failed for %s: %s — trying yfinance", ticker, exc)
    try:
        result = await yf.get_profile(ticker)
        if result:
            return result
    except Exception as exc:
        _log.warning("yfinance profile failed for %s: %s — trying polygon", ticker, exc)
    if settings.polygon_api_key:
        try:
            return await polygon.get_profile(ticker, settings.polygon_api_key)
        except Exception as exc:
            _log.warning("polygon profile also failed for %s: %s", ticker, exc)
    return {}


async def get_key_metrics(ticker: str, limit: int = 5) -> list[dict]:
    try:
        data = await _get("/key-metrics", symbol=ticker.upper(), limit=limit)
        if data:
            return data
    except Exception as exc:
        _log.warning("FMP key-metrics failed for %s: %s — trying yfinance", ticker, exc)
    try:
        return await yf.get_key_metrics(ticker, limit=limit)
    except Exception as exc:
        _log.warning("yfinance key-metrics also failed for %s: %s", ticker, exc)
        return []


async def get_ratios(ticker: str, limit: int = 5) -> list[dict]:
    try:
        data = await _get("/ratios", symbol=ticker.upper(), limit=limit)
        if data:
            return data
    except Exception as exc:
        _log.warning("FMP ratios failed for %s: %s — trying yfinance", ticker, exc)
    try:
        return await yf.get_ratios(ticker, limit=limit)
    except Exception as exc:
        _log.warning("yfinance ratios also failed for %s: %s", ticker, exc)
        return []


async def get_income_statement(ticker: str, limit: int = 5, period: str = "annual") -> list[dict]:
    try:
        data = await _get("/income-statement", symbol=ticker.upper(), limit=limit, period=period)
        if data:
            return data
    except Exception as exc:
        _log.warning("FMP income failed for %s: %s — trying yfinance", ticker, exc)
    try:
        result = await yf.get_income_statement(ticker, limit=limit, period=period)
        if result:
            return result
    except Exception as exc:
        _log.warning("yfinance income failed for %s: %s — trying polygon", ticker, exc)
    if settings.polygon_api_key:
        try:
            return await polygon.get_income_statement(ticker, settings.polygon_api_key, limit=limit, period=period)
        except Exception as exc:
            _log.warning("polygon income also failed for %s: %s", ticker, exc)
    return []


async def get_balance_sheet(ticker: str, limit: int = 5, period: str = "annual") -> list[dict]:
    try:
        data = await _get("/balance-sheet-statement", symbol=ticker.upper(), limit=limit, period=period)
        if data:
            return data
    except Exception as exc:
        _log.warning("FMP balance failed for %s: %s — trying yfinance", ticker, exc)
    try:
        result = await yf.get_balance_sheet(ticker, limit=limit, period=period)
        if result:
            return result
    except Exception as exc:
        _log.warning("yfinance balance failed for %s: %s — trying polygon", ticker, exc)
    if settings.polygon_api_key:
        try:
            return await polygon.get_balance_sheet(ticker, settings.polygon_api_key, limit=limit, period=period)
        except Exception as exc:
            _log.warning("polygon balance also failed for %s: %s", ticker, exc)
    return []


async def get_cash_flow(ticker: str, limit: int = 5, period: str = "annual") -> list[dict]:
    try:
        data = await _get("/cash-flow-statement", symbol=ticker.upper(), limit=limit, period=period)
        if data:
            return data
    except Exception as exc:
        _log.warning("FMP cashflow failed for %s: %s — trying yfinance", ticker, exc)
    try:
        result = await yf.get_cash_flow(ticker, limit=limit, period=period)
        if result:
            return result
    except Exception as exc:
        _log.warning("yfinance cashflow failed for %s: %s — trying polygon", ticker, exc)
    if settings.polygon_api_key:
        try:
            return await polygon.get_cash_flow(ticker, settings.polygon_api_key, limit=limit, period=period)
        except Exception as exc:
            _log.warning("polygon cashflow also failed for %s: %s", ticker, exc)
    return []


async def get_financial_growth(ticker: str, limit: int = 5) -> list[dict]:
    try:
        data = await _get("/financial-growth", symbol=ticker.upper(), limit=limit)
        if data:
            return data
    except Exception as exc:
        _log.warning("FMP growth failed for %s: %s — trying yfinance", ticker, exc)
    try:
        return await yf.get_financial_growth(ticker, limit=limit)
    except Exception as exc:
        _log.warning("yfinance growth also failed for %s: %s", ticker, exc)
        return []


async def get_product_segments(ticker: str) -> list:
    try:
        data = await _get("/revenue-product-segmentation", symbol=ticker.upper())
        return data if isinstance(data, list) else []
    except Exception as exc:
        _log.warning("FMP product segments failed for %s (%s)", ticker, exc)
        return []


async def get_geographic_segments(ticker: str) -> list:
    try:
        data = await _get("/revenue-geographic-segmentation", symbol=ticker.upper())
        return data if isinstance(data, list) else []
    except Exception as exc:
        _log.warning("FMP geographic segments failed for %s (%s)", ticker, exc)
        return []


async def get_dcf(ticker: str) -> dict:
    try:
        data = await _get("/discounted-cash-flow", symbol=ticker.upper())
        return data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) else {})
    except Exception:
        return {}


def safe_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def safe_int(val: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        return int(val) if val is not None else default
    except (TypeError, ValueError):
        return default
