from pydantic import BaseModel, Field
from typing import Optional
from datetime import date as date_type, datetime


class ScoreBreakdown(BaseModel):
    guru_score: Optional[float] = None
    value: Optional[float] = None
    quality: Optional[float] = None
    growth: Optional[float] = None
    strength: Optional[float] = None
    risk: Optional[float] = None
    piotroski: Optional[int] = None
    altman_z: Optional[float] = None


class StockSummary(BaseModel):
    ticker: str
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    exchange: Optional[str] = None
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    pfcf_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    roe: Optional[float] = None
    roic: Optional[float] = None
    profit_margin: Optional[float] = None
    de_ratio: Optional[float] = None
    current_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    insider_ownership: Optional[float] = None
    revenue_growth: Optional[float] = None
    eps_growth: Optional[float] = None
    fcf_growth: Optional[float] = None
    piotroski_score: Optional[int] = None
    altman_z: Optional[float] = None
    guru_score: Optional[float] = None
    guru_value: Optional[float] = None
    guru_quality: Optional[float] = None
    guru_growth: Optional[float] = None
    guru_strength: Optional[float] = None
    guru_risk: Optional[float] = None
    last_updated: Optional[datetime] = None

    model_config = {"from_attributes": True}


class StockDetail(StockSummary):
    description: Optional[str] = None
    website: Optional[str] = None
    image: Optional[str] = None
    currency: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    employees: Optional[int] = None
    beta: Optional[float] = None
    shares_outstanding: Optional[float] = None
    roa: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    quick_ratio: Optional[float] = None
    interest_coverage: Optional[float] = None
    payout_ratio: Optional[float] = None
    institutional_ownership: Optional[float] = None
    ps_ratio: Optional[float] = None
    peg_ratio: Optional[float] = None


class ScreenerParams(BaseModel):
    pe_max: Optional[float] = None
    pb_max: Optional[float] = None
    pfcf_max: Optional[float] = None
    ev_ebitda_max: Optional[float] = None
    roe_min: Optional[float] = None
    roic_min: Optional[float] = None
    de_max: Optional[float] = None
    profit_margin_min: Optional[float] = None
    fcf_growth_min: Optional[float] = None
    revenue_growth_min: Optional[float] = None
    eps_growth_min: Optional[float] = None
    market_cap_min: Optional[float] = None
    market_cap_max: Optional[float] = None
    dividend_yield_min: Optional[float] = None
    insider_ownership_min: Optional[float] = None
    piotroski_min: Optional[int] = None
    altman_z_min: Optional[float] = None
    sector: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class FinancialRecord(BaseModel):
    ticker: str
    period: Optional[str] = None
    date: Optional[date_type] = None
    calendar_year: Optional[int] = None
    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    ebitda: Optional[float] = None
    eps: Optional[float] = None
    eps_diluted: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    capex: Optional[float] = None
    fcf: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    total_debt: Optional[float] = None
    net_debt: Optional[float] = None
    cash: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None
    retained_earnings: Optional[float] = None
    shares_outstanding: Optional[float] = None
    long_term_debt: Optional[float] = None
    short_term_debt: Optional[float] = None
    inventory: Optional[float] = None
    ppe: Optional[float] = None
    dividend_per_share: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None

    model_config = {"from_attributes": True}


class DCFRequest(BaseModel):
    growth_rate: float = Field(default=0.10, ge=-0.5, le=1.0)
    terminal_growth: float = Field(default=0.03, ge=0.0, le=0.10)
    discount_rate: float = Field(default=0.10, ge=0.01, le=0.5)
    years: int = Field(default=10, ge=1, le=20)


class DCFYearProjection(BaseModel):
    year: int
    fcf: float
    present_value: float
    cumulative_pv: float


class DCFResponse(BaseModel):
    ticker: str
    current_price: Optional[float] = None
    base_fcf: Optional[float] = None
    intrinsic_value: Optional[float] = None
    upside_downside: Optional[float] = None
    margin_of_safety: Optional[float] = None
    growth_rate: float
    terminal_growth: float
    discount_rate: float
    years: int
    terminal_value: Optional[float] = None
    terminal_value_pv: Optional[float] = None
    total_pv_fcf: Optional[float] = None
    projections: list[DCFYearProjection] = []


class InsiderRecord(BaseModel):
    ticker: str
    name: Optional[str] = None
    position: Optional[str] = None
    transaction_type: Optional[str] = None
    shares: Optional[float] = None
    price: Optional[float] = None
    value: Optional[float] = None
    date: Optional[date_type] = None
    filing_date: Optional[date_type] = None

    model_config = {"from_attributes": True}
