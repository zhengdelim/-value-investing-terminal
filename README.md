# ValueScreen — Value Investing Terminal

A full-stack GuruFocus-style value investing dashboard powered by Financial Modeling Prep (FMP).

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 18 + Vite + Tailwind CSS + Recharts |
| Backend | FastAPI + Python 3.11 |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Migrations | Alembic |
| Container | Docker Compose |

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env and set your FMP_API_KEY
# Get a free key at https://financialmodelingprep.com/developer/docs
```

### 2. Run with Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 3. Local development (without Docker)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env       # set FMP_API_KEY, point DB/Redis to local instances
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/stocks` | Screener with filter params |
| GET | `/api/stocks/{ticker}` | Full stock detail |
| GET | `/api/stocks/{ticker}/financials` | Historical financials |
| GET | `/api/stocks/{ticker}/dcf` | DCF valuation |
| GET | `/api/stocks/{ticker}/insiders` | Insider transactions |

### Screener query params

```
pe_max, roe_min, de_max, market_cap_min, market_cap_max,
pfcf_max, roic_min, profit_margin_min, fcf_growth_min,
revenue_growth_min, eps_growth_min, dividend_yield_min,
insider_ownership_min, piotroski_min, altman_z_min, limit, offset
```

### DCF params

```
growth_rate (default 0.10), terminal_growth (default 0.03),
discount_rate (default 0.10), years (default 10)
```

## Scoring

### Piotroski F-Score (0–9)
Signals across profitability (4), leverage/liquidity (3), and operating efficiency (2).
- 8–9: Strong
- 5–7: Neutral
- 0–4: Weak

### Altman Z-Score
- > 2.99: Safe
- 1.81–2.99: Grey zone
- < 1.81: Distress

### GuruScore (0–100)
Composite score across five pillars:
| Pillar | Weight |
|---|---|
| Value | 25% |
| Quality | 25% |
| Growth | 20% |
| Financial Strength | 20% |
| Risk | 10% |

## Database Migrations

```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

## Environment Variables

| Variable | Description |
|---|---|
| `FMP_API_KEY` | Financial Modeling Prep API key |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `CACHE_TTL` | Cache TTL in seconds (default 3600) |
| `CORS_ORIGINS` | Comma-separated allowed origins |
