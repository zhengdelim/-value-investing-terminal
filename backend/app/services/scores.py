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
