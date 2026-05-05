"""Add missing columns

Revision ID: 002
Revises: 001
Create Date: 2026-05-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stocks", sa.Column("city", sa.String(), nullable=True))
    op.add_column("stocks", sa.Column("state", sa.String(), nullable=True))
    op.add_column("stocks", sa.Column("employees", sa.Integer(), nullable=True))

    op.add_column("financials", sa.Column("long_term_debt", sa.Float(), nullable=True))
    op.add_column("financials", sa.Column("short_term_debt", sa.Float(), nullable=True))
    op.add_column("financials", sa.Column("inventory", sa.Float(), nullable=True))
    op.add_column("financials", sa.Column("ppe", sa.Float(), nullable=True))
    op.add_column("financials", sa.Column("dividend_per_share", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("stocks", "city")
    op.drop_column("stocks", "state")
    op.drop_column("stocks", "employees")
    op.drop_column("financials", "long_term_debt")
    op.drop_column("financials", "short_term_debt")
    op.drop_column("financials", "inventory")
    op.drop_column("financials", "ppe")
    op.drop_column("financials", "dividend_per_share")
