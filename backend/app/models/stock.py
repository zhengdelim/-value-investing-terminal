from sqlalchemy import Column, String, Float, Integer, DateTime, Date, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..database import Base


class Stock(Base):
    __tablename__ = "stocks"

    ticker = Column(String, primary_key=True, index=True)
    name = Column(String)
    sector = Column(String)
    industry = Column(String)
    description = Column(String)
    exchange = Column(String)
    country = Column(String)
    city = Column(String)
    state = Column(String)
    employees = Column(Integer)
    currency = Column(String, default="USD")
    website = Column(String)
    image = Column(String)

    current_price = Column(Float)
    market_cap = Column(Float)
    beta = Column(Float)
    shares_outstanding = Column(Float)

    # Valuation
    pe_ratio = Column(Float)
    pb_ratio = Column(Float)
    pfcf_ratio = Column(Float)
    ev_ebitda = Column(Float)
    ps_ratio = Column(Float)
    peg_ratio = Column(Float)

    # Quality
    roe = Column(Float)
    roic = Column(Float)
    roa = Column(Float)
    gross_margin = Column(Float)
    operating_margin = Column(Float)
    profit_margin = Column(Float)

    # Growth
    revenue_growth = Column(Float)
    eps_growth = Column(Float)
    fcf_growth = Column(Float)

    # Financial strength
    de_ratio = Column(Float)
    current_ratio = Column(Float)
    quick_ratio = Column(Float)
    interest_coverage = Column(Float)

    # Dividends
    dividend_yield = Column(Float)
    payout_ratio = Column(Float)

    # Insider
    insider_ownership = Column(Float)
    institutional_ownership = Column(Float)

    # Scores
    piotroski_score = Column(Integer)
    altman_z = Column(Float)
    guru_score = Column(Float)
    guru_value = Column(Float)
    guru_quality = Column(Float)
    guru_growth = Column(Float)
    guru_strength = Column(Float)
    guru_risk = Column(Float)

    last_updated = Column(DateTime, default=datetime.utcnow)

    financials = relationship("Financial", back_populates="stock", cascade="all, delete-orphan")
    dcf_results = relationship("DCFResult", back_populates="stock", cascade="all, delete-orphan")
    insider_transactions = relationship("InsiderTransaction", back_populates="stock", cascade="all, delete-orphan")


class Financial(Base):
    __tablename__ = "financials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, ForeignKey("stocks.ticker", ondelete="CASCADE"), index=True)
    period = Column(String)  # 'annual' or 'quarter'
    date = Column(Date)
    calendar_year = Column(Integer)

    # Income
    revenue = Column(Float)
    gross_profit = Column(Float)
    operating_income = Column(Float)
    net_income = Column(Float)
    ebitda = Column(Float)
    eps = Column(Float)
    eps_diluted = Column(Float)

    # Cash flow
    operating_cash_flow = Column(Float)
    capex = Column(Float)
    fcf = Column(Float)

    # Balance sheet
    total_assets = Column(Float)
    total_liabilities = Column(Float)
    total_equity = Column(Float)
    total_debt = Column(Float)
    net_debt = Column(Float)
    cash = Column(Float)
    current_assets = Column(Float)
    current_liabilities = Column(Float)
    retained_earnings = Column(Float)
    shares_outstanding = Column(Float)

    # Debt breakdown
    long_term_debt = Column(Float)
    short_term_debt = Column(Float)

    # Asset details
    inventory = Column(Float)
    ppe = Column(Float)  # property, plant & equipment

    # Per-share
    dividend_per_share = Column(Float)

    # Margins
    gross_margin = Column(Float)
    operating_margin = Column(Float)
    net_margin = Column(Float)

    stock = relationship("Stock", back_populates="financials")


class DCFResult(Base):
    __tablename__ = "dcf_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, ForeignKey("stocks.ticker", ondelete="CASCADE"), index=True)
    growth_rate = Column(Float)
    terminal_growth = Column(Float)
    discount_rate = Column(Float)
    years = Column(Integer)
    base_fcf = Column(Float)
    intrinsic_value = Column(Float)
    current_price = Column(Float)
    upside_downside = Column(Float)
    margin_of_safety = Column(Float)
    projections = Column(String)  # JSON string
    calculated_at = Column(DateTime, default=datetime.utcnow)

    stock = relationship("Stock", back_populates="dcf_results")


class InsiderTransaction(Base):
    __tablename__ = "insider_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, ForeignKey("stocks.ticker", ondelete="CASCADE"), index=True)
    name = Column(String)
    position = Column(String)
    transaction_type = Column(String)  # 'P-Purchase', 'S-Sale'
    shares = Column(Float)
    price = Column(Float)
    value = Column(Float)
    date = Column(Date)
    filing_date = Column(Date)

    stock = relationship("Stock", back_populates="insider_transactions")
