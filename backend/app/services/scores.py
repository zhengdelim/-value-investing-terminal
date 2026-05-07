from typing import Optional


def piotroski_f_score(
    net_income=None, total_assets=None, operating_cash_flow=None,
    long_term_debt=None, current_assets=None, current_liabilities=None,
    shares_outstanding=None, gross_profit=None, revenue=None,
    net_income_prev=None, total_assets_prev=None, long_term_debt_prev=None,
    current_assets_prev=None, current_liabilities_prev=None,
    shares_outstanding_prev=None, gross_profit_prev=None, revenue_prev=None,
) -> int:
    score = 0

    if net_income is not None and total_assets and total_assets > 0:
        if net_income / total_assets > 0:
            score += 1
    if operating_cash_flow is not None and operating_cash_flow > 0:
        score += 1
    if all(v is not None for v in [net_income, total_assets, net_income_prev, total_assets_prev]):
        if (net_income / total_assets) > (net_income_prev / total_assets_prev):
            score += 1
    if all(v is not None for v in [operating_cash_flow, net_income, total_assets]) and total_assets:
        if (operating_cash_flow / total_assets) > (net_income / total_assets):
            score += 1
    if all(v is not None for v in [long_term_debt, total_assets, long_term_debt_prev, total_assets_prev]):
        lev = long_term_debt / total_assets if total_assets else 0
        lev_p = long_term_debt_prev / total_assets_prev if total_assets_prev else 0
        if lev < lev_p:
            score += 1
    if all(v is not None for v in [current_assets, current_liabilities, current_assets_prev, current_liabilities_prev]):
        cr = current_assets / current_liabilities if current_liabilities else 0
        cr_p = current_assets_prev / current_liabilities_prev if current_liabilities_prev else 0
        if cr > cr_p:
            score += 1
    if shares_outstanding is not None and shares_outstanding_prev is not None:
        if shares_outstanding <= shares_outstanding_prev:
            score += 1
    if all(v is not None for v in [gross_profit, revenue, gross_profit_prev, revenue_prev]):
        gm = gross_profit / revenue if revenue else 0
        gm_p = gross_profit_prev / revenue_prev if revenue_prev else 0
        if gm > gm_p:
            score += 1
    if all(v is not None for v in [revenue, total_assets, revenue_prev, total_assets_prev]):
        at = revenue / total_assets if total_assets else 0
        at_p = revenue_prev / total_assets_prev if total_assets_prev else 0
        if at > at_p:
            score += 1

    return score


def altman_z_score(
    current_assets=None, current_liabilities=None, total_assets=None,
    retained_earnings=None, ebit=None, market_cap=None,
    total_liabilities=None, revenue=None,
) -> Optional[float]:
    if not total_assets or total_assets == 0 or not total_liabilities or total_liabilities == 0:
        return None
    x1 = ((current_assets or 0) - (current_liabilities or 0)) / total_assets
    x2 = (retained_earnings or 0) / total_assets
    x3 = (ebit or 0) / total_assets
    x4 = (market_cap or 0) / total_liabilities
    x5 = (revenue or 0) / total_assets
    return 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def _score(value: Optional[float], good: float, bad: float, invert: bool = False) -> float:
    """Map a metric to 0–100. invert=True when lower value is better."""
    if value is None:
        return 50.0
    v = -value if invert else value
    g = -good if invert else good
    b = -bad if invert else bad
    if g == b:
        return 50.0
    return _clamp((v - b) / (g - b) * 100)


def guru_score(
    pe_ratio=None, pb_ratio=None, pfcf_ratio=None, ev_ebitda=None,
    roe=None, roic=None, gross_margin=None, piotroski=None,
    revenue_growth=None, eps_growth=None, fcf_growth=None,
    de_ratio=None, current_ratio=None, altman_z=None, beta=None,
) -> dict[str, float]:
    """
    Weights: Quality 40% | Growth 25% | Financial Strength 25% | Value 10%

    Thresholds calibrated for large-cap equities so that high-quality compounders
    (MSFT, AAPL, V, etc.) score in the 75-95 range.
    """

    # --- Quality (40%) ---
    # ROE: anything above 20% is good; cap gains at 25%+
    q_roe = _score(min(roe or 0, 0.50), good=0.20, bad=0.0)
    # ROIC: 15%+ is excellent
    q_roic = _score(min(roic or 0, 0.50), good=0.15, bad=0.0)
    # Gross margin: 50%+ = wide moat
    q_gm = _score(gross_margin, good=0.50, bad=0.10)
    # Piotroski: 7–9 strong
    q_pio = _score(piotroski, good=9, bad=0) if piotroski is not None else 50.0
    quality = (q_roe + q_roic + q_gm + q_pio) / 4

    # --- Growth (25%) — EPS weighted most, FCF least ---
    g_rev = _score(revenue_growth, good=0.15, bad=-0.05)
    g_eps = _score(eps_growth, good=0.15, bad=-0.10)
    g_fcf = _score(fcf_growth, good=0.15, bad=-0.10)
    growth = g_rev * 0.30 + g_eps * 0.50 + g_fcf * 0.20

    # --- Financial Strength (25%) — Altman Z leads ---
    s_az = _score(altman_z, good=3.0, bad=1.0)           # 50% weight
    # Handle negative-equity buyback companies: cap D/E penalty
    _de = min(de_ratio or 0, 5.0)
    s_de = _score(_de, good=0.5, bad=2.5, invert=True)   # 30% weight
    s_cr = _score(current_ratio, good=1.2, bad=0.5)       # 20% weight
    strength = s_az * 0.50 + s_de * 0.30 + s_cr * 0.20

    # --- Value (10%) — generous thresholds for growth companies ---
    v_pe = _score(pe_ratio, good=25, bad=60, invert=True)
    v_pfcf = _score(pfcf_ratio, good=25, bad=60, invert=True)
    v_ev = _score(ev_ebitda, good=15, bad=35, invert=True)
    value = (v_pe + v_pfcf + v_ev) / 3

    total = quality * 0.40 + growth * 0.25 + strength * 0.25 + value * 0.10

    return {
        "guru_score": round(total, 1),
        "guru_value": round(value, 1),
        "guru_quality": round(quality, 1),
        "guru_growth": round(growth, 1),
        "guru_strength": round(strength, 1),
        "guru_risk": round(_score(beta, good=0.5, bad=2.0, invert=True), 1),
    }


def swot_moat_analysis(stock: dict) -> dict:
    """Rule-based SWOT + Moat from stock metrics."""
    sf = lambda k: stock.get(k)

    roe = sf("roe") or 0
    roic = sf("roic") or 0
    gm = sf("gross_margin") or 0
    pm = sf("profit_margin") or 0
    de = sf("de_ratio") or 0
    cr = sf("current_ratio") or 0
    az = sf("altman_z") or 0
    pio = sf("piotroski_score")
    rev_g = sf("revenue_growth") or 0
    eps_g = sf("eps_growth") or 0
    fcf_g = sf("fcf_growth") or 0
    beta = sf("beta") or 1.0
    pe = sf("pe_ratio") or 0
    guru = sf("guru_score") or 0
    sector = sf("sector") or ""
    mktcap = sf("market_cap") or 0

    strengths, weaknesses, opportunities, threats = [], [], [], []

    # --- Strengths ---
    if roe > 0.20:
        strengths.append(f"Exceptional ROE of {roe*100:.1f}% — strong shareholder value creation")
    elif roe > 0.12:
        strengths.append(f"Solid ROE of {roe*100:.1f}% — above-average capital efficiency")
    if roic > 0.15:
        strengths.append(f"ROIC of {roic*100:.1f}% comfortably exceeds cost of capital — durable competitive advantages")
    if gm > 0.50:
        strengths.append(f"Wide gross margins ({gm*100:.1f}%) — significant pricing power or structural cost advantage")
    elif gm > 0.35:
        strengths.append(f"Healthy gross margins ({gm*100:.1f}%) — decent brand or scale advantages")
    if pio is not None and pio >= 7:
        strengths.append(f"Piotroski F-Score of {pio}/9 — profitability, leverage, and efficiency all improving")
    if az > 2.99:
        strengths.append(f"Altman Z-Score of {az:.2f} — low bankruptcy risk, financially sound")
    if pm > 0.20:
        strengths.append(f"Net margin of {pm*100:.1f}% — disciplined cost structure and pricing")
    if rev_g > 0.10:
        strengths.append(f"Revenue growing at {rev_g*100:.1f}% — demand remains strong")
    if eps_g > 0.15:
        strengths.append(f"EPS growth of {eps_g*100:.1f}% — earnings power expanding")

    # --- Weaknesses ---
    if roe < 0.08 and roe > 0:
        weaknesses.append(f"Below-average ROE ({roe*100:.1f}%) — capital not generating strong returns")
    if de > 2.0:
        weaknesses.append(f"D/E ratio of {de:.2f}x — elevated leverage adds financial risk")
    if cr < 1.0:
        weaknesses.append(f"Current ratio of {cr:.2f}x — more current liabilities than assets; monitor liquidity")
    if pio is not None and pio <= 3:
        weaknesses.append(f"Weak Piotroski F-Score ({pio}/9) — fundamentals deteriorating on multiple dimensions")
    if az < 1.81 and az > 0:
        weaknesses.append(f"Altman Z-Score of {az:.2f} — in financial distress zone; credit risk elevated")
    elif az < 2.99 and az > 0:
        weaknesses.append(f"Altman Z-Score of {az:.2f} — grey zone; requires monitoring")
    if pm < 0.05 and pm > 0:
        weaknesses.append(f"Thin net margins ({pm*100:.1f}%) — vulnerable to cost inflation or pricing pressure")
    if fcf_g < -0.10:
        weaknesses.append(f"Free cash flow declined {fcf_g*100:.1f}% — cash generation under pressure")
    if pe > 50:
        weaknesses.append(f"P/E of {pe:.1f}x — premium valuation leaves little room for disappointment")

    # --- Opportunities ---
    if rev_g > 0.08:
        opportunities.append(f"Revenue momentum ({rev_g*100:.1f}% growth) can compound shareholder value over time")
    if fcf_g > 0.10:
        opportunities.append(f"Growing FCF ({fcf_g*100:.1f}%) enables buybacks, dividends, and strategic reinvestment")
    if guru > 70 and pe < 25:
        opportunities.append("Potential undervaluation — quality score is high relative to current multiples")
    if roic > 0.15 and rev_g > 0.05:
        opportunities.append("High-ROIC business with growth — each reinvested dollar creates substantial value")
    if de < 0.5:
        opportunities.append("Clean balance sheet provides flexibility for acquisitions or capital returns")
    if sector in ("Technology", "Healthcare", "Financial Services"):
        opportunities.append(f"{sector} sector tailwinds — structural growth trends support long-term expansion")

    # --- Threats ---
    if fcf_g < -0.05:
        threats.append(f"Declining FCF ({fcf_g*100:.1f}%) could constrain dividend growth and buybacks")
    if rev_g < 0:
        threats.append(f"Negative revenue growth ({rev_g*100:.1f}%) — potential market share loss or demand weakness")
    if de > 1.5:
        threats.append(f"Leverage ({de:.2f}x D/E) creates vulnerability in rising rate environments")
    if beta > 1.3:
        threats.append(f"Beta of {beta:.2f} — amplified drawdowns during market corrections")
    if pio is not None and pio <= 4:
        threats.append("Piotroski score signals operational deterioration across multiple signals")
    if pe > 40:
        threats.append(f"High valuation multiple (P/E {pe:.1f}x) — significant re-rating risk if growth disappoints")

    # --- Moat Analysis ---
    moat_score = 0
    moat_signals = []
    name = stock.get("name") or stock.get("ticker") or "the company"

    if gm > 0.60:
        moat_score += 25
        moat_signals.append({
            "source": "Pricing Power", "strength": "Wide",
            "detail": f"Gross margin {gm*100:.1f}% — exceptional ability to price well above cost",
            "smart": {
                "specific": f"{name} earns {gm*100:.1f}¢ of gross profit on every $1 of revenue — well above the ~40% typical for its sector.",
                "measurable": f"Gross margin {gm*100:.1f}% vs. ~35–45% sector average. A 10 pp improvement in margin at this scale has outsized impact on free cash flow.",
                "assessment": "This level of pricing power usually reflects brand premium, proprietary IP, or a product with no close substitute — customers accept the price because value delivered far exceeds cost.",
                "risk": "Margin compression from commodity input costs, aggressive price competition, or loss of brand premium could quickly erode this advantage.",
                "timeframe": "Wide-moat pricing power typically persists 10+ years if supported by brand investment and continued product differentiation.",
            }
        })
    elif gm > 0.40:
        moat_score += 15
        moat_signals.append({
            "source": "Pricing Power", "strength": "Narrow",
            "detail": f"Gross margin {gm*100:.1f}% — moderate pricing advantage over peers",
            "smart": {
                "specific": f"{name} retains {gm*100:.1f}% gross margin, indicating it can price above pure commodity levels but faces some competitive pressure on price.",
                "measurable": f"At {gm*100:.1f}% gross margin, each $1B of revenue generates ${gm:.2f}B gross profit — a meaningful but not exceptional spread over cost of goods.",
                "assessment": "Moderate pricing power often comes from brand differentiation, switching costs, or niche market positioning rather than a dominant category monopoly.",
                "risk": "New entrants offering 'good enough' substitutes at lower prices, or private-label competition, are the primary margin threats at this tier.",
                "timeframe": "Narrow pricing advantages are defensible over 3–5 years but require sustained R&D or brand spend to prevent erosion.",
            }
        })

    if roic > 0.20:
        moat_score += 25
        moat_signals.append({
            "source": "Capital Returns", "strength": "Wide",
            "detail": f"ROIC {roic*100:.1f}% — far exceeds cost of capital; value is consistently being created",
            "smart": {
                "specific": f"{name} generates {roic*100:.1f}% return on invested capital — roughly {roic/0.09:.1f}x the typical 8–10% weighted average cost of capital (WACC).",
                "measurable": f"Every $1 of capital reinvested creates ${roic:.2f} of operating profit. At a WACC of ~9%, this implies economic profit of ~{(roic-0.09)*100:.1f}¢ per dollar deployed.",
                "assessment": "Consistently high ROIC is the single strongest evidence of a durable moat — it means competitors cannot easily replicate the business model and erode returns.",
                "risk": "Capital-heavy growth, regulatory capital requirements, or a period of heavy reinvestment can temporarily suppress ROIC without signalling permanent moat erosion.",
                "timeframe": "Businesses sustaining ROIC >20% for 10+ years are rare — this is a strong signal of a wide moat if the trend holds.",
            }
        })
    elif roic > 0.12:
        moat_score += 15
        moat_signals.append({
            "source": "Capital Returns", "strength": "Narrow",
            "detail": f"ROIC {roic*100:.1f}% — exceeds typical 8–10% cost of capital",
            "smart": {
                "specific": f"{name} earns {roic*100:.1f}% ROIC, which clears the typical 8–10% cost of capital hurdle and creates shareholder value.",
                "measurable": f"Economic value add (EVA) is approximately {(roic-0.09)*100:.1f}¢ per dollar of capital — positive, but not yet the wide-moat territory of 20%+.",
                "assessment": "Adequate returns suggest operational efficiency or a modest competitive edge, but returns are not so exceptional that they would deter well-capitalised competitors from entering.",
                "risk": "Industry-wide margin pressure, rising interest rates increasing the cost of capital, or new technology disrupting the business model.",
                "timeframe": "Narrow capital return advantages require continuous operational improvement to sustain over a 5-year horizon.",
            }
        })

    switching_sectors = ("Technology", "Software", "Communication Services", "Healthcare")
    if sector in switching_sectors and gm > 0.50:
        moat_score += 20
        moat_signals.append({
            "source": "Switching Costs", "strength": "Likely",
            "detail": f"High-margin {sector} business — customers face meaningful friction switching away",
            "smart": {
                "specific": f"{name} operates in {sector} with {gm*100:.1f}% gross margins — a combination that typically indicates customers are locked in via contracts, integrations, or workflows.",
                "measurable": f"High margins ({gm*100:.1f}%) persist despite competitive markets, which is only possible if customers face real costs — financial, operational, or reputational — when switching.",
                "assessment": "Switching costs create a 'sticky' revenue base: once embedded, customers renew rather than endure migration pain. This gives pricing power on renewals and cross-sell opportunities.",
                "risk": "Open-source alternatives, API commoditisation, or a competitor offering seamless migration tools can dramatically reduce switching friction over time.",
                "timeframe": "Switching cost moats in enterprise software/tech tend to be durable (5–15 years) but can be disrupted rapidly if a generation-defining technology shift occurs (e.g., cloud, AI).",
            }
        })

    if sector in ("Technology", "Communication Services") and mktcap and mktcap > 100e9:
        moat_score += 15
        moat_signals.append({
            "source": "Network Effects", "strength": "Likely",
            "detail": f"Large-scale platform (${mktcap/1e9:.0f}B market cap) — product value scales with user base",
            "smart": {
                "specific": f"{name}'s platform scale (${mktcap/1e9:.0f}B market cap) suggests a large installed user or ecosystem base where each additional participant makes the network more valuable.",
                "measurable": "Network effect moats are difficult to quantify directly, but scale is a proxy: at $100B+ market cap, the user base is large enough that no new entrant can replicate the network value without years of subsidised growth.",
                "assessment": "Direct network effects (more users → more value per user) and indirect effects (more users → more third-party developers/integrators) create a reinforcing flywheel that raises the barrier to entry.",
                "risk": "Multi-homing (users on multiple networks simultaneously) weakens network moats. A superior competing network with lower switching costs can cascade rapidly — see MySpace → Facebook.",
                "timeframe": "Network effects are among the most durable moats (10–20+ years) once critical mass is achieved, but they can collapse quickly if a better network emerges.",
            }
        })

    if pm and pm > 0.20 and gm > 0.30:
        opex_efficiency = (gm - pm) / gm if gm > 0 else 1
        if opex_efficiency < 0.55:
            moat_score += 15
            moat_signals.append({
                "source": "Cost Advantage", "strength": "Narrow",
                "detail": f"Lean operations — converts {(1-opex_efficiency)*100:.0f}% of gross profit to net income",
                "smart": {
                    "specific": f"{name} converts {(1-opex_efficiency)*100:.0f}% of gross profit into net income, meaning opex (SG&A + R&D + other) consumes only {opex_efficiency*100:.0f}% of gross profit — a highly efficient operating structure.",
                    "measurable": f"Net margin {pm*100:.1f}% vs. gross margin {gm*100:.1f}% — the gap of {(gm-pm)*100:.1f}pp is below the sector average, implying scale economies or process efficiency advantages.",
                    "assessment": "Cost advantages arise from scale (fixed costs spread over more units), proprietary processes, favourable supplier relationships, or geographic/regulatory advantages unavailable to competitors.",
                    "risk": "Cost advantages can erode if a competitor achieves greater scale, automates a previously human-intensive process, or gains access to cheaper inputs.",
                    "timeframe": "Process and scale-based cost advantages are durable (5–10 years) but require continuous investment in operations to stay ahead as competitors improve.",
                }
            })

    moat_score = min(moat_score, 100)
    moat_width = "Wide" if moat_score >= 65 else "Narrow" if moat_score >= 35 else "None / Uncertain"

    return {
        "swot": {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "opportunities": opportunities,
            "threats": threats,
        },
        "moat": {
            "score": moat_score,
            "width": moat_width,
            "signals": moat_signals,
        },
    }


# ---------------------------------------------------------------------------
# Sector benchmark profiles used by market_research & valuation_review
# ---------------------------------------------------------------------------
_SECTOR = {
    "Technology":              {"ctx": "Technology companies command premium valuations through scalable models, network effects, and high switching costs. Gross margins above 60% and ROIC above 20% signal durable competitive advantage. Watch R&D intensity and revenue quality (recurring vs one-time).", "pe": 32, "pfcf": 25, "ev_ebitda": 20},
    "Healthcare":              {"ctx": "Healthcare benefits from inelastic demand, patent moats, and regulatory barriers. Pricing power shows in gross margins above 55%. FDA pipeline and patent-cliff exposure are key idiosyncratic risks.", "pe": 26, "pfcf": 20, "ev_ebitda": 16},
    "Consumer Discretionary":  {"ctx": "Consumer discretionary is economically sensitive. Brand strength and omnichannel presence are key moat sources. Strong FCF generation enables buybacks. Watch inventory turnover and same-store sales as leading indicators.", "pe": 22, "pfcf": 18, "ev_ebitda": 13},
    "Consumer Staples":        {"ctx": "Staples offer defensive cash flows across economic cycles. Distribution network and brand recognition create durable moats. Dividend sustainability and payout coverage are key metrics for income investors.", "pe": 21, "pfcf": 18, "ev_ebitda": 14},
    "Financials":              {"ctx": "Financials are valued on P/B and ROE rather than earnings multiples. Regulatory capital adequacy, net interest margin, and credit quality drive profitability. Trust and client relationships form the core moat.", "pe": 14, "pfcf": None, "ev_ebitda": None},
    "Industrials":             {"ctx": "Industrials generate long-term contract revenue with high customer switching costs from installed equipment. ROIC relative to WACC is the primary value driver. Backlog growth and book-to-bill ratio are key leading indicators.", "pe": 21, "pfcf": 17, "ev_ebitda": 12},
    "Energy":                  {"ctx": "Energy companies are exposed to commodity cycles. Reserve quality, breakeven production cost, and balance sheet strength determine survivability through troughs. FCF yield at mid-cycle price is the most robust valuation anchor.", "pe": 14, "pfcf": 10, "ev_ebitda": 8},
    "Materials":               {"ctx": "Materials are cyclical, driven by global demand and commodity supply/demand dynamics. Low-cost production position and vertical integration provide competitive resilience. Watch China demand and capacity additions.", "pe": 16, "pfcf": 14, "ev_ebitda": 10},
    "Real Estate":             {"ctx": "REITs are valued on FFO/AFFO multiples rather than P/E. Location quality, tenant credit, lease duration, and occupancy drive NAV. Dividend sustainability and interest rate sensitivity are paramount.", "pe": 22, "pfcf": 20, "ev_ebitda": 16},
    "Communication Services":  {"ctx": "Communication services span telecom, media, and digital platforms. Network effects, content libraries, and subscriber lock-in are key moats. Pricing power varies widely across sub-industries; watch churn and ARPU trends.", "pe": 20, "pfcf": 17, "ev_ebitda": 12},
    "Utilities":               {"ctx": "Utilities are regulated monopolies with predictable, low-growth cash flows. Rate cases and regulatory approvals determine ROE. They are prized for dividend yield and capital preservation rather than growth.", "pe": 18, "pfcf": 16, "ev_ebitda": 13},
    "_default":                {"ctx": "Evaluate this company on absolute profitability (ROE, ROIC), balance sheet health, and cash flow quality relative to peers in the same industry. Apply a moderate margin of safety given limited sector-specific context.", "pe": 20, "pfcf": 16, "ev_ebitda": 12},
}

def _sf(v):
    """Safe float — returns None for NaN, None, or non-numeric."""
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Market Research
# ---------------------------------------------------------------------------
def market_research(stock: dict) -> dict:
    """
    Generate structured market research narrative from quantitative metrics.
    Returns quality/growth/fortress tiers plus thesis and risk bullets.
    """
    roe   = _sf(stock.get("roe"))
    roic  = _sf(stock.get("roic"))
    gm    = _sf(stock.get("gross_margin"))
    pm    = _sf(stock.get("profit_margin"))
    rev_g = _sf(stock.get("revenue_growth"))
    eps_g = _sf(stock.get("eps_growth"))
    fcf_g = _sf(stock.get("fcf_growth"))
    de    = _sf(stock.get("de_ratio"))
    cr    = _sf(stock.get("current_ratio"))
    az    = _sf(stock.get("altman_z"))
    pio   = stock.get("piotroski_score")
    pe    = _sf(stock.get("pe_ratio"))
    dy    = _sf(stock.get("dividend_yield"))
    mc    = _sf(stock.get("market_cap"))
    sector = stock.get("sector") or "_default"

    # ── Business Quality Tier ─────────────────────────────────────────────
    q = 0
    if roe  is not None: q += 3 if roe  > 0.20 else 2 if roe  > 0.15 else 1 if roe  > 0.08 else 0
    if roic is not None: q += 3 if roic > 0.15 else 2 if roic > 0.10 else 1 if roic > 0.05 else 0
    if gm   is not None: q += 3 if gm   > 0.50 else 2 if gm   > 0.35 else 1 if gm   > 0.20 else 0
    if pm   is not None: q += 2 if pm   > 0.15 else 1 if pm   > 0.08 else 0
    quality_tier = "Premium" if q >= 8 else "High Quality" if q >= 5 else "Average" if q >= 2 else "Below Average"

    # ── Growth Profile ────────────────────────────────────────────────────
    g_primary = rev_g if rev_g is not None else eps_g
    growth_profile = (
        "High Growth"     if g_primary is not None and g_primary > 0.20 else
        "Moderate Growth" if g_primary is not None and g_primary > 0.08 else
        "Slow Growth"     if g_primary is not None and g_primary > 0    else
        "Declining"       if g_primary is not None                       else
        "Unknown"
    )

    growth_signals = []
    if rev_g is not None:
        if   rev_g > 0.20: growth_signals.append(f"Revenue growing rapidly at {rev_g*100:.1f}% YoY — strong demand or market share gains.")
        elif rev_g > 0.08: growth_signals.append(f"Steady revenue growth of {rev_g*100:.1f}% YoY — business expanding ahead of GDP.")
        elif rev_g > 0:    growth_signals.append(f"Modest revenue growth of {rev_g*100:.1f}% — mature market or competitive pressure on top line.")
        else:              growth_signals.append(f"Revenue declining {rev_g*100:.1f}% — requires investigation of competitive dynamics.")
    if eps_g is not None and eps_g > 0 and (rev_g is None or eps_g > rev_g):
        growth_signals.append(f"EPS growing ({eps_g*100:.1f}%) faster than revenue — margin expansion and operating leverage at work.")
    if fcf_g is not None and fcf_g > 0.10:
        growth_signals.append(f"FCF growing {fcf_g*100:.1f}% — accelerating cash generation supports buybacks and reinvestment.")

    # ── Financial Fortress ────────────────────────────────────────────────
    f = 0
    if az  is not None: f += 3 if az  > 2.99 else 1 if az  > 1.81 else 0
    if pio is not None: f += 3 if pio >= 7    else 1 if pio >= 5   else 0
    if de  is not None: f += 2 if de  < 0.50  else 1 if de  < 1.0  else 0
    if cr  is not None: f += 1 if cr  > 1.50  else 0
    fortress_tier = "Fortress" if f >= 7 else "Stable" if f >= 4 else "Stretched" if f >= 2 else "Distressed"

    fortress_signals = []
    if az  is not None:
        fortress_signals.append(
            f"Altman Z {az:.2f} — {'Safe Zone, low distress risk' if az > 2.99 else 'Grey Zone, monitor balance sheet' if az > 1.81 else 'Distress Zone — assess debt sustainability'}"
        )
    if pio is not None:
        fortress_signals.append(
            f"Piotroski F-Score {pio}/9 — {'strong across all quality dimensions' if pio >= 7 else 'solid on most accounting measures' if pio >= 5 else 'several quality signals are weak'}"
        )
    if de is not None:
        fortress_signals.append(
            f"D/E {de:.2f} — {'conservative; ample capacity for strategic investment' if de < 0.5 else 'moderate; manageable debt load' if de < 1.0 else 'elevated; monitor interest coverage' if de < 2.0 else 'high leverage; significant financial risk'}"
        )
    if cr is not None:
        fortress_signals.append(
            f"Current ratio {cr:.2f} — {'strong liquidity' if cr > 2.0 else 'adequate coverage' if cr > 1.0 else 'tight — may face short-term cash pressure'}"
        )

    # ── Capital Efficiency ────────────────────────────────────────────────
    efficiency_signals = []
    if roic is not None:
        spread = roic - 0.09  # vs estimated WACC of 9%
        if   spread > 0.10: efficiency_signals.append(f"ROIC {roic*100:.1f}% — creates substantial value above cost of capital; hallmark of a high-quality compounder.")
        elif spread > 0.05: efficiency_signals.append(f"ROIC {roic*100:.1f}% — earns a meaningful premium above typical WACC (~9%).")
        elif spread > 0:    efficiency_signals.append(f"ROIC {roic*100:.1f}% — marginally above cost of capital; value creation is limited.")
        else:               efficiency_signals.append(f"ROIC {roic*100:.1f}% — below estimated cost of capital; business may be destroying value.")
    if roe is not None:
        if   roe > 0.20: efficiency_signals.append(f"ROE {roe*100:.1f}% — exceptional return on shareholder equity.")
        elif roe > 0.15: efficiency_signals.append(f"ROE {roe*100:.1f}% — above-average profitability relative to equity base.")
        elif roe > 0.10: efficiency_signals.append(f"ROE {roe*100:.1f}% — moderate return on equity.")
    if gm is not None and gm > 0.40:
        efficiency_signals.append(f"Gross margin {gm*100:.1f}% — high margins signal pricing power and a differentiated product or service.")

    # ── Investment Thesis ─────────────────────────────────────────────────
    thesis = []
    if quality_tier in ("Premium", "High Quality"):
        parts = []
        if roe:  parts.append(f"ROE {roe*100:.1f}%")
        if roic: parts.append(f"ROIC {roic*100:.1f}%")
        thesis.append(f"High-quality business with durable profitability ({', '.join(parts)}) — strong signal of competitive advantage.")
    if g_primary and g_primary > 0.08:
        thesis.append(f"{growth_profile} at {g_primary*100:.1f}% — expanding market presence supports long-term compounding.")
    if gm and gm > 0.40:
        thesis.append(f"High gross margins ({gm*100:.1f}%) demonstrate pricing power and differentiated positioning.")
    if fortress_tier in ("Fortress", "Stable"):
        thesis.append(f"{fortress_tier} balance sheet provides strategic flexibility for M&A, buybacks, and organic investment.")
    if dy and dy > 0.02:
        thesis.append(f"Dividend yield {dy*100:.1f}% provides income support; sustainable payout enhances total return.")
    if mc:
        size = "large-cap" if mc > 10e9 else "mid-cap" if mc > 2e9 else "small-cap"
        thesis.append(f"${mc/1e9:.1f}B {size} — sufficient scale and liquidity for institutional investment.")
    if not thesis:
        thesis.append("Insufficient data to build a complete investment thesis. Refresh stock data to populate metrics.")

    # ── Key Risks ─────────────────────────────────────────────────────────
    risks = []
    if rev_g is not None and rev_g < 0:
        risks.append(f"Revenue declining {abs(rev_g)*100:.1f}% — top-line contraction raises competitive and market share concerns.")
    if de is not None and de > 1.5:
        risks.append(f"High leverage (D/E {de:.2f}) increases vulnerability to rate rises and earnings shortfalls.")
    if pe is not None and pe > 40:
        risks.append(f"Premium P/E of {pe:.1f}x leaves little room for execution mistakes; growth must be sustained.")
    if pm is not None and 0 < pm < 0.05:
        risks.append(f"Thin net margins ({pm*100:.1f}%) — any cost pressure or pricing erosion quickly hits profitability.")
    if pm is not None and pm < 0:
        risks.append("Loss-making at the net level — monitor cash burn runway and path to profitability.")
    if pio is not None and pio <= 2:
        risks.append("Low Piotroski F-Score — deterioration across multiple accounting quality dimensions; elevated short-selling risk.")
    if az is not None and az < 1.81:
        risks.append(f"Altman Z {az:.2f} — in distress zone; assess refinancing capacity and liquidity.")
    if not risks:
        risks.append("No significant quantitative risk flags identified. Conduct qualitative review of competitive dynamics and management track record.")

    sp = _SECTOR.get(sector) or _SECTOR["_default"]
    return {
        "quality_tier": quality_tier,
        "growth_profile": growth_profile,
        "fortress_tier": fortress_tier,
        "efficiency_signals": efficiency_signals,
        "growth_signals": growth_signals,
        "fortress_signals": fortress_signals,
        "investment_thesis": thesis,
        "key_risks": risks,
        "sector_context": sp["ctx"],
    }


# ---------------------------------------------------------------------------
# Valuation Review
# ---------------------------------------------------------------------------
def valuation_review(stock: dict, fin: Optional[dict] = None) -> dict:
    """
    Multi-method fair value analysis with verdict and margin of safety.
    fin: most recent annual Financial record (dict) for EPS, BVPS, FCF/share.
    """
    price     = _sf(stock.get("current_price"))
    pe        = _sf(stock.get("pe_ratio"))
    pb        = _sf(stock.get("pb_ratio"))
    pfcf      = _sf(stock.get("pfcf_ratio"))
    roe       = _sf(stock.get("roe"))
    roic      = _sf(stock.get("roic"))
    rev_g     = _sf(stock.get("revenue_growth"))
    eps_g     = _sf(stock.get("eps_growth"))
    dy        = _sf(stock.get("dividend_yield"))
    dcf_up    = _sf(stock.get("dcf_upside"))
    sector    = stock.get("sector") or "_default"

    # From Financial record
    eps = bvps = fcf_ps = ebitda_ps = net_cash_ps = None
    if fin:
        shares = _sf(fin.get("shares_outstanding"))
        eps    = _sf(fin.get("eps_diluted")) or _sf(fin.get("eps"))
        equity = _sf(fin.get("total_equity"))
        fcf    = _sf(fin.get("fcf"))
        ebitda = _sf(fin.get("ebitda"))
        cash   = _sf(fin.get("cash")) or 0
        debt   = _sf(fin.get("total_debt")) or 0
        if equity and shares and shares > 0:
            bvps = equity / shares
        if fcf and shares and shares > 0:
            fcf_ps = fcf / shares
        if ebitda and shares and shares > 0:
            ebitda_ps = ebitda / shares
        if shares and shares > 0:
            net_cash_ps = (cash - debt) / shares

    sp = _SECTOR.get(sector) or _SECTOR["_default"]
    fair_pe, fair_pfcf, fair_ev = sp["pe"], sp["pfcf"], sp["ev_ebitda"]

    methods = []
    fair_values = []

    def _add(name, fv, confidence, notes):
        if fv is not None and fv > 0 and price:
            upside = round((fv / price - 1) * 100, 1)
            methods.append({"name": name, "fair_value": round(fv, 2), "upside": upside, "confidence": confidence, "notes": notes})
            fair_values.append(fv)

    # 1. DCF (stored during refresh)
    if dcf_up is not None and price:
        _add("DCF (10% growth · 10% discount · 3% terminal)",
             price * (1 + dcf_up), "Medium",
             "10-year DCF on last FCF with default assumptions. Sensitive to growth rate — treat as base case only.")

    # 2. Graham Number
    if eps and eps > 0 and bvps and bvps > 0:
        _add("Graham Number",
             (22.5 * eps * bvps) ** 0.5, "High",
             f"√(22.5 × EPS ${eps:.2f} × BVPS ${bvps:.2f}). Conservative intrinsic value for asset-backed businesses.")

    # 3. Graham PE Formula
    if eps and eps > 0:
        g_pct = max(0, min((rev_g or eps_g or 0.05) * 100, 25))
        _add("Graham PE (8.5 + 2g)",
             eps * (8.5 + 2 * g_pct), "Medium",
             f"EPS × (8.5 + 2×{g_pct:.1f}%). Graham's original formula for growth-adjusted earnings value.")

    # 4. Sector P/E
    if eps and eps > 0 and fair_pe:
        _add(f"Sector P/E ({fair_pe}x)",
             eps * fair_pe, "Medium",
             f"EPS × {fair_pe}x, the typical fair multiple for {sector}. Relative-valuation benchmark.")

    # 5. P/FCF
    if fcf_ps and fcf_ps > 0 and fair_pfcf:
        _add(f"P/FCF ({fair_pfcf}x)",
             fcf_ps * fair_pfcf, "High",
             f"FCF/share × {fair_pfcf}x. Less susceptible to accounting choices than earnings-based methods.")

    # 6. EV/EBITDA
    if ebitda_ps and fair_ev and net_cash_ps is not None:
        ev_fv = ebitda_ps * fair_ev + net_cash_ps
        _add(f"EV/EBITDA ({fair_ev}x)",
             ev_fv, "High",
             f"EBITDA/share × {fair_ev}x + net cash/share ${net_cash_ps:.2f}. Capital-structure-agnostic benchmark.")

    # Fair value range & verdict
    fv_range = None
    verdict = "Insufficient Data"
    mos = None

    if fair_values and price:
        fv_low  = round(min(fair_values), 2)
        fv_mid  = round(sum(fair_values) / len(fair_values), 2)
        fv_high = round(max(fair_values), 2)
        fv_range = {"low": fv_low, "mid": fv_mid, "high": fv_high}
        upside_to_mid = (fv_mid - price) / price
        mos = round((fv_mid - price) / fv_mid * 100, 1)
        verdict = (
            "Deeply Undervalued" if upside_to_mid > 0.35 else
            "Undervalued"        if upside_to_mid > 0.15 else
            "Fairly Valued"      if upside_to_mid > -0.10 else
            "Overvalued"         if upside_to_mid > -0.25 else
            "Richly Priced"
        )

    # Key observations
    obs = []
    if pe and fair_pe:
        diff = (pe - fair_pe) / fair_pe
        if   diff < -0.30: obs.append(f"P/E {pe:.1f}x — trades at a {abs(diff)*100:.0f}% discount to the {sector} sector benchmark of {fair_pe}x. May indicate undervaluation or below-sector growth expectations.")
        elif diff >  0.30: obs.append(f"P/E {pe:.1f}x — {diff*100:.0f}% premium to sector benchmark of {fair_pe}x. Sustained growth is required to justify the multiple.")
        else:              obs.append(f"P/E {pe:.1f}x — broadly in line with the {sector} sector benchmark of {fair_pe}x.")
    if pfcf and fair_pfcf:
        fcf_yield = 1 / pfcf * 100
        if pfcf < fair_pfcf * 0.80: obs.append(f"P/FCF {pfcf:.1f}x is attractive vs sector benchmark of {fair_pfcf}x — FCF yield of {fcf_yield:.1f}% offers a good return floor.")
        elif pfcf > fair_pfcf * 1.5: obs.append(f"P/FCF {pfcf:.1f}x is elevated vs benchmark of {fair_pfcf}x — FCF yield of {fcf_yield:.1f}% is thin.")
    if pb is not None and pb < 1.0:
        obs.append(f"P/B {pb:.2f}x — stock trades below book value, creating potential asset-backed margin of safety.")
    if roe and roic and roe > 0.20 and roic > 0.15:
        obs.append(f"High ROE ({roe*100:.1f}%) + ROIC ({roic*100:.1f}%) justify a premium multiple — compounders often re-rate upward over time.")
    if dy and dy > 0.03:
        obs.append(f"Dividend yield {dy*100:.1f}% reduces effective cost basis and provides income cushion while waiting for re-rating.")
    if not obs:
        obs.append("Insufficient valuation data available. Refresh stock data to populate all metrics.")

    return {
        "methods": methods,
        "fair_value_range": fv_range,
        "verdict": verdict,
        "margin_of_safety": mos,
        "current_price": price,
        "key_observations": obs,
    }
