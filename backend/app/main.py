import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .routers import stocks, financials, dcf, insiders, analysis, news, sp500, watchlist

settings = get_settings()

app = FastAPI(
    title="ValueScreen API",
    description="GuruFocus-style value investing terminal",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(financials.router, prefix="/api/stocks", tags=["financials"])
app.include_router(dcf.router, prefix="/api/stocks", tags=["dcf"])
app.include_router(insiders.router, prefix="/api/stocks", tags=["insiders"])
app.include_router(analysis.router, prefix="/api/stocks", tags=["analysis"])
app.include_router(news.router,      prefix="/api",           tags=["news"])
app.include_router(sp500.router,     prefix="/api/sp500",     tags=["sp500"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/debug/fmp")
async def debug_fmp():
    key = settings.fmp_api_key or ""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"https://financialmodelingprep.com/stable/profile?symbol=AAPL&apikey={key}"
            r = await client.get(url)
            return {
                "key_length": len(key),
                "key_prefix": key[:6] if key else "",
                "status_code": r.status_code,
                "response": r.json(),
            }
    except Exception as exc:
        return {"key_length": len(key), "key_prefix": key[:6] if key else "", "error": str(exc)}
