from typing import Optional
from ..schemas.stock import DCFResponse, DCFYearProjection


def run_dcf(
    ticker: str,
    base_fcf: float,
    current_price: Optional[float],
    shares_outstanding: Optional[float],
    growth_rate: float = 0.10,
    terminal_growth: float = 0.03,
    discount_rate: float = 0.10,
    years: int = 10,
) -> DCFResponse:
    if discount_rate <= terminal_growth:
        terminal_growth = discount_rate - 0.01

    projections = []
    total_pv = 0.0
    fcf = base_fcf

    for t in range(1, years + 1):
        fcf = fcf * (1 + growth_rate)
        pv = fcf / ((1 + discount_rate) ** t)
        total_pv += pv
        projections.append(
            DCFYearProjection(
                year=t,
                fcf=round(fcf, 2),
                present_value=round(pv, 2),
                cumulative_pv=round(total_pv, 2),
            )
        )

    terminal_fcf = base_fcf * ((1 + growth_rate) ** years)
    terminal_value = terminal_fcf * (1 + terminal_growth) / (discount_rate - terminal_growth)
    terminal_value_pv = terminal_value / ((1 + discount_rate) ** years)

    equity_value = total_pv + terminal_value_pv

    intrinsic_value = None
    upside_downside = None
    margin_of_safety = None

    if shares_outstanding and shares_outstanding > 0:
        intrinsic_value = equity_value / shares_outstanding
        if current_price and current_price > 0 and intrinsic_value:
            upside_downside = (intrinsic_value - current_price) / current_price
            margin_of_safety = 1 - (current_price / intrinsic_value)

    return DCFResponse(
        ticker=ticker,
        current_price=current_price,
        base_fcf=base_fcf,
        intrinsic_value=round(intrinsic_value, 2) if intrinsic_value else None,
        upside_downside=round(upside_downside, 4) if upside_downside is not None else None,
        margin_of_safety=round(margin_of_safety, 4) if margin_of_safety is not None else None,
        growth_rate=growth_rate,
        terminal_growth=terminal_growth,
        discount_rate=discount_rate,
        years=years,
        terminal_value=round(terminal_value, 2),
        terminal_value_pv=round(terminal_value_pv, 2),
        total_pv_fcf=round(total_pv, 2),
        projections=projections,
    )
