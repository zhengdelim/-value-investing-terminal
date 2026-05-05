"""
News + AI market analysis router.
- GET /api/news              — raw aggregated headlines (15-min cache)
- GET /api/market-analysis   — AI-structured 5-section briefing (30-min cache)

AI analysis uses Claude claude-haiku-4-5 when ANTHROPIC_API_KEY is set.
Falls back to rule-based categorisation when no key is provided.
"""

import asyncio
import functools
import httpx
import json
import logging
import re
import xml.etree.ElementTree as ET
from fastapi import APIRouter
import yfinance as yf
from ..services.cache import cache_get, cache_set, make_key
from ..config import get_settings

router = APIRouter()
_log = logging.getLogger(__name__)
settings = get_settings()

# ── RSS sources ───────────────────────────────────────────────────────────────
_FEEDS = [
    ("Yahoo Finance",   "https://finance.yahoo.com/rss/topstories",           "Markets"),
    ("CNBC",            "https://www.cnbc.com/id/100003114/device/rss/rss.html", "Markets"),
    ("MarketWatch",     "https://www.marketwatch.com/rss/topstories",          "Markets"),
    ("Investing.com",   "https://www.investing.com/rss/news_25.rss",           "Macro"),
]

_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _parse_rss(xml_text: str, source: str, category: str) -> list[dict]:
    try:
        root = ET.fromstring(xml_text)
        items = []
        for item in root.findall(".//item")[:12]:
            title   = _strip_html(item.findtext("title", "")).strip()
            link    = (item.findtext("link") or "").strip()
            pub     = (item.findtext("pubDate") or "").strip()
            desc    = _strip_html(item.findtext("description") or "")[:250]
            src_tag = _strip_html(item.findtext("source") or source)
            thumb   = None
            enc = item.find("enclosure")
            if enc is not None and "image" in enc.get("type", ""):
                thumb = enc.get("url")
            if title and link:
                items.append({
                    "title":     title,
                    "url":       link,
                    "published": pub,
                    "source":    src_tag or source,
                    "summary":   desc,
                    "image":     thumb,
                    "category":  category,
                })
        return items
    except Exception as exc:
        _log.warning("RSS parse error (%s): %s", source, exc)
        return []


async def _fetch_all_rss() -> list[dict]:
    all_items: list[dict] = []
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=_HEADERS) as client:
        for source, url, category in _FEEDS:
            try:
                r = await client.get(url)
                if r.status_code == 200:
                    all_items.extend(_parse_rss(r.text, source, category))
            except Exception as exc:
                _log.warning("RSS fetch failed (%s): %s", source, exc)

    # deduplicate by lowercased title prefix
    seen, unique = set(), []
    for item in all_items:
        key = item["title"].lower()[:55]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


# ── AI analysis ───────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a senior financial markets analyst. You will be given a list of news headlines \
and summaries from major financial sources. Produce a concise, structured market briefing \
in JSON format with exactly these five keys:

"breaking_news"      — list of objects: {headline, impact, sentiment}
                       (sentiment: "bullish" | "bearish" | "neutral")
"market_moves"       — list of objects: {asset, move, note}
                       Highlight stocks, indices, crypto, commodities with notable price action.
"macro_themes"       — list of objects: {theme, detail, sentiment}
                       Cover rates, inflation, geopolitics, central banks.
"key_narratives"     — list of objects: {title, bull_case, bear_case, consensus}
                       Surface 2–3 major bull vs bear debates.
"actionable_insights"— list of objects: {insight, watch, timeframe}
                       What traders and investors should monitor next.

Rules:
- Be concise; every bullet should be actionable or informative
- Prioritise cause→effect relationships
- Max 6 items per section; quality over quantity
- Return ONLY valid JSON, no markdown fences, no extra text\
"""


async def _ai_analysis(headlines: list[dict]) -> dict | None:
    if not settings.anthropic_api_key:
        return None

    # Build compact input — title + summary for each article
    articles_text = "\n".join(
        f"{i+1}. [{a['source']}] {a['title']}"
        + (f" — {a['summary'][:120]}" if a.get("summary") else "")
        for i, a in enumerate(headlines[:30])
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":         settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json",
                },
                json={
                    "model":      "claude-haiku-4-5",
                    "max_tokens": 2048,
                    "system":     _SYSTEM_PROMPT,
                    "messages":   [{"role": "user", "content": articles_text}],
                },
            )
            r.raise_for_status()
            content = r.json()["content"][0]["text"]
            return json.loads(content)
    except json.JSONDecodeError as exc:
        _log.warning("AI response was not valid JSON: %s", exc)
        return None
    except Exception as exc:
        _log.warning("AI analysis call failed: %s", exc)
        return None


# ── Rule-based fallback ───────────────────────────────────────────────────────

_BEARISH_KW = {"fall", "drop", "slump", "crash", "decline", "loss", "down", "cut", "warn",
               "miss", "weak", "recession", "layoff", "default", "debt", "inflation", "tariff"}
_BULLISH_KW = {"rise", "gain", "surge", "rally", "beat", "record", "high", "growth",
               "buy", "upgrade", "profit", "strong", "boom", "hire"}


def _sentiment_from_title(title: str) -> str:
    low = title.lower()
    b_hits = sum(1 for w in _BULLISH_KW if w in low)
    n_hits = sum(1 for w in _BEARISH_KW if w in low)
    if b_hits > n_hits:   return "bullish"
    if n_hits > b_hits:   return "bearish"
    return "neutral"


_MACRO_KW = {"fed", "rate", "inflation", "gdp", "jobs", "employment", "treasury",
             "geopolit", "china", "ukraine", "opec", "oil", "tariff", "trade"}
_MOVE_KW  = {"nasdaq", "s&p", "dow", "bitcoin", "gold", "oil", "crude", "apple",
             "nvidia", "tesla", "microsoft", "amazon", "meta"}


def _rule_based_analysis(items: list[dict]) -> dict:
    breaking, moves, macro, narratives, insights = [], [], [], [], []

    for a in items[:30]:
        title   = a.get("title", "")
        summary = a.get("summary", "")
        low     = title.lower()
        sent    = _sentiment_from_title(title)

        if any(k in low for k in _MACRO_KW):
            macro.append({"theme": title, "detail": summary or "See article.", "sentiment": sent})
        elif any(k in low for k in _MOVE_KW):
            moves.append({"asset": a.get("source", ""), "move": title, "note": summary or ""})
        else:
            breaking.append({"headline": title, "impact": summary or "Monitor for follow-on impact.", "sentiment": sent})

    # Build a simple narrative from sentiment distribution
    bull_count = sum(1 for i in breaking + macro if i.get("sentiment") == "bullish")
    bear_count = sum(1 for i in breaking + macro if i.get("sentiment") == "bearish")
    if bull_count or bear_count:
        narratives.append({
            "title":     "Market Sentiment Balance",
            "bull_case": f"{bull_count} bullish headlines suggesting positive risk appetite.",
            "bear_case": f"{bear_count} bearish signals that could pressure equities.",
            "consensus": "Mixed — wait for macro data confirmation before directional bets.",
        })

    insights.append({
        "insight":   "Monitor earnings guidance revisions across mega-cap tech.",
        "watch":     "Forward P/E compression if guidance disappoints.",
        "timeframe": "This week",
    })
    insights.append({
        "insight":   "Fed speakers and CPI print are the key macro catalysts.",
        "watch":     "10-year Treasury yield reaction to any inflation surprise.",
        "timeframe": "Next 7 days",
    })

    return {
        "breaking_news":       breaking[:6],
        "market_moves":        moves[:6],
        "macro_themes":        macro[:6],
        "key_narratives":      narratives[:3],
        "actionable_insights": insights[:5],
        "ai_powered":          False,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/news")
async def get_news():
    key = make_key("market_news_v2")
    if cached := cache_get(key):
        return cached
    items = await _fetch_all_rss()
    cache_set(key, items, ttl=900)
    return items


@router.get("/market-analysis")
async def get_market_analysis():
    key = make_key("market_analysis_v2")
    if cached := cache_get(key):
        return cached

    items = await _fetch_all_rss()
    if not items:
        return {"error": "Could not fetch any news sources."}

    result = await _ai_analysis(items)
    if result is None:
        result = _rule_based_analysis(items)
        result["ai_powered"] = False
    else:
        result["ai_powered"] = True

    result["article_count"] = len(items)
    result["sources"] = list({a["source"] for a in items})

    # 30-minute cache — frequent enough for trading hours
    cache_set(key, result, ttl=1800)
    return result


# ── Market Indices ────────────────────────────────────────────────────────────

_INDICES = [
    {"key": "sp500",  "symbol": "%5EGSPC",   "fmp_symbol": "%5EGSPC",   "polygon_symbol": "I:SPX",  "label": "S&P 500", "currency": "USD"},
    {"key": "nasdaq", "symbol": "%5EIXIC",   "fmp_symbol": "%5EIXIC",   "polygon_symbol": "I:COMP", "label": "Nasdaq",  "currency": "USD"},
    {"key": "hstech", "symbol": "HSTECH.HK", "fmp_symbol": "HSTECH.HK", "polygon_symbol": None,     "label": "HS Tech", "currency": "HKD"},
    {"key": "sti",    "symbol": "%5ESTI",    "fmp_symbol": "%5ESTI",    "polygon_symbol": None,     "label": "STI",     "currency": "SGD"},
]

def _format_index(idx: dict, price, prev, chg, pct, high=None, low=None, open_=None, volume=None, active=None) -> dict:
    def r2(v): return round(v, 2) if v is not None else None
    def r3(v): return round(v, 3) if v is not None else None
    return {
        **idx,
        "price":        r2(price),
        "prev_close":   r2(prev),
        "change":       r2(chg),
        "change_pct":   r3(pct),
        "day_high":     r2(high),
        "day_low":      r2(low),
        "open":         r2(open_),
        "volume":       volume,
        "market_state": ("Open" if active else "Closed") if active is not None else "Unknown",
        "error":        None,
    }


async def _fetch_index_polygon(client: httpx.AsyncClient, idx: dict, api_key: str) -> dict | None:
    sym = idx.get("polygon_symbol")
    if not sym or not api_key:
        return None
    try:
        url = f"https://api.polygon.io/v3/snapshot?ticker.any_of={sym}&apiKey={api_key}"
        r = await client.get(url, timeout=8.0)
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            return None
        q = results[0]
        session = q.get("session", {})
        price = q.get("value") or session.get("close")
        prev  = session.get("previous_close")
        chg   = session.get("change")
        pct   = session.get("change_percent")
        return _format_index(
            idx, price, prev, chg, pct,
            high=session.get("high"), low=session.get("low"), open_=session.get("open"),
        )
    except Exception as exc:
        _log.warning("Polygon index fetch failed (%s): %s", sym, exc)
        return None


async def _fetch_index(client: httpx.AsyncClient, idx: dict, fmp_key: str, polygon_key: str) -> dict:
    # Try FMP first
    try:
        url = f"https://financialmodelingprep.com/stable/quote?symbol={idx['fmp_symbol']}&apikey={fmp_key}"
        r = await client.get(url, timeout=8.0)
        r.raise_for_status()
        data = r.json()
        if data:
            q = data[0] if isinstance(data, list) else data
            price = q.get("price")
            if price:
                return _format_index(
                    idx, price,
                    prev=q.get("previousClose") or q.get("prevClose"),
                    chg=q.get("change"),
                    pct=q.get("changesPercentage") or q.get("changePercent"),
                    high=q.get("dayHigh"), low=q.get("dayLow"), open_=q.get("open"),
                    volume=q.get("volume"), active=q.get("isActivelyTrading"),
                )
    except Exception as exc:
        _log.warning("FMP index fetch failed (%s): %s — trying Polygon", idx["symbol"], exc)

    # Fallback to Polygon
    result = await _fetch_index_polygon(client, idx, polygon_key)
    if result:
        return result

    return {**idx, "price": None, "change": None, "change_pct": None,
            "market_state": "Unknown", "error": "All sources failed"}


@router.get("/indices")
async def get_indices():
    key = make_key("market_indices_v2")
    if cached := cache_get(key):
        return cached

    fmp_key     = settings.fmp_api_key
    polygon_key = settings.polygon_api_key
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[_fetch_index(client, idx, fmp_key, polygon_key) for idx in _INDICES]
        )
    data = list(results)
    cache_set(key, data, ttl=180)
    return data
