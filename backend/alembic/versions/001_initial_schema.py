"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stocks",
        sa.Column("ticker", sa.String(), primary_key=True, index=True),
        sa.Column("name", sa.String()),
        sa.Column("sector", sa.String()),
        sa.Column("industry", sa.String()),
        sa.Column("description", sa.String()),
        sa.Column("exchange", sa.String()),
        sa.Column("country", sa.String()),
        sa.Column("currency", sa.String(), default="USD"),
        sa.Column("website", sa.String()),
        sa.Column("image", sa.String()),
        sa.Column("current_price", sa.Float()),
        sa.Column("market_cap", sa.Float()),
        sa.Column("beta", sa.Float()),
        sa.Column("shares_outstanding", sa.Float()),
        sa.Column("pe_ratio", sa.Float()),
        sa.Column("pb_ratio", sa.Float()),
        sa.Column("pfcf_ratio", sa.Float()),
        sa.Column("ev_ebitda", sa.Float()),
        sa.Column("ps_ratio", sa.Float()),
        sa.Column("peg_ratio", sa.Float()),
        sa.Column("roe", sa.Float()),
        sa.Column("roic", sa.Float()),
        sa.Column("roa", sa.Float()),
        sa.Column("gross_margin", sa.Float()),
        sa.Column("operating_margin", sa.Float()),
        sa.Column("profit_margin", sa.Float()),
        sa.Column("revenue_growth", sa.Float()),
        sa.Column("eps_growth", sa.Float()),
        sa.Column("fcf_growth", sa.Float()),
        sa.Column("de_ratio", sa.Float()),
        sa.Column("current_ratio", sa.Float()),
        sa.Column("quick_ratio", sa.Float()),
        sa.Column("interest_coverage", sa.Float()),
        sa.Column("dividend_yield", sa.Float()),
        sa.Column("payout_ratio", sa.Float()),
        sa.Column("insider_ownership", sa.Float()),
        sa.Column("institutional_ownership", sa.Float()),
        sa.Column("piotroski_score", sa.Integer()),
        sa.Column("altman_z", sa.Float()),
        sa.Column("guru_score", sa.Float()),
        sa.Column("guru_value", sa.Float()),
        sa.Column("guru_quality", sa.Float()),
        sa.Column("guru_growth", sa.Float()),
        sa.Column("guru_strength", sa.Float()),
        sa.Column("guru_risk", sa.Float()),
        sa.Column("last_updated", sa.DateTime()),
    )

    op.create_table(
        "financials",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(), sa.ForeignKey("stocks.ticker", ondelete="CASCADE"), index=True),
        sa.Column("period", sa.String()),
        sa.Column("date", sa.Date()),
        sa.Column("calendar_year", sa.Integer()),
        sa.Column("revenue", sa.Float()),
        sa.Column("gross_profit", sa.Float()),
        sa.Column("operating_income", sa.Float()),
        sa.Column("net_income", sa.Float()),
        sa.Column("ebitda", sa.Float()),
        sa.Column("eps", sa.Float()),
        sa.Column("eps_diluted", sa.Float()),
        sa.Column("operating_cash_flow", sa.Float()),
        sa.Column("capex", sa.Float()),
        sa.Column("fcf", sa.Float()),
        sa.Column("total_assets", sa.Float()),
        sa.Column("total_liabilities", sa.Float()),
        sa.Column("total_equity", sa.Float()),
        sa.Column("total_debt", sa.Float()),
        sa.Column("net_debt", sa.Float()),
        sa.Column("cash", sa.Float()),
        sa.Column("current_assets", sa.Float()),
        sa.Column("current_liabilities", sa.Float()),
        sa.Column("retained_earnings", sa.Float()),
        sa.Column("shares_outstanding", sa.Float()),
        sa.Column("gross_margin", sa.Float()),
        sa.Column("operating_margin", sa.Float()),
        sa.Column("net_margin", sa.Float()),
    )

    op.create_table(
        "dcf_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(), sa.ForeignKey("stocks.ticker", ondelete="CASCADE"), index=True),
        sa.Column("growth_rate", sa.Float()),
        sa.Column("terminal_growth", sa.Float()),
        sa.Column("discount_rate", sa.Float()),
        sa.Column("years", sa.Integer()),
        sa.Column("base_fcf", sa.Float()),
        sa.Column("intrinsic_value", sa.Float()),
        sa.Column("current_price", sa.Float()),
        sa.Column("upside_downside", sa.Float()),
        sa.Column("margin_of_safety", sa.Float()),
        sa.Column("projections", sa.String()),
        sa.Column("calculated_at", sa.DateTime()),
    )

    op.create_table(
        "insider_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(), sa.ForeignKey("stocks.ticker", ondelete="CASCADE"), index=True),
        sa.Column("name", sa.String()),
        sa.Column("position", sa.String()),
        sa.Column("transaction_type", sa.String()),
        sa.Column("shares", sa.Float()),
        sa.Column("price", sa.Float()),
        sa.Column("value", sa.Float()),
        sa.Column("date", sa.Date()),
        sa.Column("filing_date", sa.Date()),
    )


def downgrade() -> None:
    op.drop_table("insider_transactions")
    op.drop_table("dcf_results")
    op.drop_table("financials")
    op.drop_table("stocks")
