import { useState, useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import clsx from "clsx";
import { useStockDetail, useFinancials, useInsiders, useRefreshStock, useMultiplesHistory, useSegments, useDCF } from "../hooks/useStockDetail";
import GuruScoreRing, { ScorePillar } from "../components/GuruScoreRing";
import { MetricBadge } from "../components/Badge";
import DCFCalculator from "../components/DCFCalculator";
import SwotMoat from "../components/SwotMoat";
import { RevenueChart, EPSChart, NetIncomeChart, FCFChart, DebtChart } from "../components/Charts";
import { ProductSegmentCharts, GeoSegmentCharts } from "../components/SegmentCharts";

const TABS = ["Valuation", "Profitability", "Growth", "Cash Flow", "Balance Sheet", "Analysis", "Insiders", "DCF"];

function Row({ label, value }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-bg-border last:border-0">
      <span className="text-sm text-muted">{label}</span>
      <span className="font-mono text-sm text-gray-200">{value ?? "—"}</span>
    </div>
  );
}

function fmt(v, pct = false, prefix = "") {
  if (v == null) return "—";
  return pct ? `${(v * 100).toFixed(1)}%` : `${prefix}${v.toFixed(2)}`;
}

function fmtB(v) {
  if (v == null) return "—";
  const b = v / 1e9;
  return b >= 1000 ? `$${(b / 1000).toFixed(2)}T` : `$${b.toFixed(2)}B`;
}

function AltmanBand({ z }) {
  if (z == null) return <span className="text-subtle">—</span>;
  const [color, label] = z > 2.99 ? ["text-green", "Safe"] : z > 1.81 ? ["text-yellow", "Grey Zone"] : ["text-red", "Distress"];
  return <span className={clsx("font-mono", color)}>{z.toFixed(2)} <span className="text-xs opacity-70">({label})</span></span>;
}

function PiotroskiBand({ score }) {
  if (score == null) return <span className="text-subtle">—</span>;
  const [color, label] = score >= 7 ? ["text-green", "Strong"] : score >= 4 ? ["text-yellow", "Neutral"] : ["text-red", "Weak"];
  return <span className={clsx("font-mono", color)}>{score}/9 <span className="text-xs opacity-70">({label})</span></span>;
}

export default function StockDetail() {
  const { ticker } = useParams();
  const navigate = useNavigate();
  const [tab, setTab] = useState("Valuation");

  const [period, setPeriod] = useState("annual");
  const [quarterLimit, setQuarterLimit] = useState(20);

  const { data: stock, isLoading, isError, refetch } = useStockDetail(ticker);
  const { data: financials, isLoading: finLoading } = useFinancials(ticker, period);
  const { data: insiders } = useInsiders(ticker);
  const { data: multiplesHistory } = useMultiplesHistory(ticker);
  const { data: segments, isLoading: segmentsLoading } = useSegments(ticker);

  const defaultGrowthRate = useMemo(() => {
    if (!financials?.length || financials.length < 2) return null;
    const n = Math.min(financials.length, 5);
    const newest = financials[0]?.revenue;
    const oldest = financials[n - 1]?.revenue;
    if (!newest || !oldest || oldest <= 0) return null;
    const cagr = Math.pow(newest / oldest, 1 / (n - 1)) - 1;
    return Math.max(-0.2, Math.min(0.5, Math.floor(cagr * 100) / 100));
  }, [financials]);

  const headerDcfParams = useMemo(() => ({
    growth_rate: defaultGrowthRate ?? 0.10,
    terminal_growth: 0.03,
    discount_rate: 0.10,
    years: 10,
  }), [defaultGrowthRate]);

  const { data: headerDcf } = useDCF(ticker, headerDcfParams);

  const refreshStock = useRefreshStock(ticker);
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try { await refreshStock(); } finally { setRefreshing(false); }
  }, [refreshStock]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen text-muted">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Loading {ticker}… (fetching from FMP)</span>
        </div>
      </div>
    );
  }

  if (isError || !stock) {
    return (
      <div className="flex items-center justify-center h-screen text-muted">
        <div className="text-center">
          <div className="text-4xl mb-3">⚠️</div>
          <p className="text-sm font-semibold text-gray-300">Could not load data for {ticker}</p>
          <p className="text-xs mt-1 text-muted">FMP free plan allows ~250 requests/day. Quota may be exhausted — try again later or click Refresh.</p>
          <div className="flex gap-3 justify-center mt-4">
            <button onClick={() => refetch()} className="text-xs text-accent-blue hover:underline">↻ Retry</button>
            <button onClick={() => navigate("/")} className="text-xs text-muted hover:text-gray-300">← Back</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="bg-bg-secondary border-b border-bg-border px-3 sm:px-6 py-3 sm:py-4">
        <div className="flex items-center justify-between mb-3">
          <button onClick={() => navigate("/")} className="text-xs text-muted hover:text-gray-300 flex items-center gap-1">
            ← Back to Screener
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className={clsx(
              "text-xs px-3 py-1.5 rounded border flex items-center gap-1.5 transition-colors",
              refreshing
                ? "border-bg-border text-muted cursor-not-allowed"
                : "border-accent-blue/40 text-accent-blue hover:bg-accent-blue/10"
            )}
          >
            {refreshing ? (
              <>
                <span className="w-3 h-3 border border-accent-blue border-t-transparent rounded-full animate-spin" />
                Refreshing…
              </>
            ) : (
              <>↻ Refresh Data</>
            )}
          </button>
        </div>
        <div className="flex flex-wrap items-start gap-3 sm:gap-6">
          {stock.image && (
            <img src={stock.image} alt={stock.name} className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg object-contain bg-white p-1" />
          )}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
              <h1 className="text-xl sm:text-2xl font-bold font-mono text-accent-blue">{stock.ticker}</h1>
              <span className="text-gray-300 text-base sm:text-lg font-medium truncate max-w-[180px] sm:max-w-none">{stock.name}</span>
              {stock.exchange && (
                <span className="text-xs bg-bg-hover border border-bg-border rounded px-2 py-0.5 text-muted">{stock.exchange}</span>
              )}
            </div>
            <div className="flex items-center gap-2 sm:gap-3 mt-1 flex-wrap text-xs text-muted">
              {stock.sector && <span>{stock.sector}</span>}
              {stock.industry && <span className="hidden sm:inline">· {stock.industry}</span>}
              {stock.country && <span>· {stock.country}</span>}
              {stock.website && (
                <a href={stock.website} target="_blank" rel="noopener noreferrer" className="text-accent-blue hover:underline hidden sm:inline">
                  {stock.website.replace(/^https?:\/\//, "")}
                </a>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3 sm:gap-6">
            <div>
              <div className="font-mono text-2xl sm:text-3xl font-bold text-gray-100">
                {stock.current_price != null ? `$${stock.current_price.toFixed(2)}` : "—"}
              </div>
              <div className="text-xs text-muted mt-0.5">{stock.currency ?? "USD"}</div>
            </div>
            <div className="flex flex-col items-center gap-1">
              <GuruScoreRing score={stock.guru_score} size={52} />
              <span className="text-xs text-muted">GuruScore</span>
            </div>
          </div>
        </div>

        {/* Score pillars */}
        <div className="flex gap-3 sm:gap-6 mt-4 pt-4 border-t border-bg-border flex-wrap">
          {[
            ["Value",    stock.guru_value],
            ["Quality",  stock.guru_quality],
            ["Growth",   stock.guru_growth],
            ["Strength", stock.guru_strength],
          ].map(([l, v]) => (
            <ScorePillar key={l} label={l} value={v}
              color={v >= 70 ? "text-green" : v >= 45 ? "text-yellow" : "text-red"} />
          ))}
          <div className="ml-4 pl-4 border-l border-bg-border flex gap-6">
            <div className="flex flex-col items-center gap-1">
              <span className="text-[10px] text-muted uppercase tracking-widest">Piotroski</span>
              <PiotroskiBand score={stock.piotroski_score} />
            </div>
            <div className="flex flex-col items-center gap-1">
              <span className="text-[10px] text-muted uppercase tracking-widest">Altman Z</span>
              <AltmanBand z={stock.altman_z} />
            </div>
          </div>
          {headerDcf?.intrinsic_value != null && (
            <div className="ml-4 pl-4 border-l border-bg-border flex flex-col items-center gap-1">
              <span className="text-[10px] text-muted uppercase tracking-widest">DCF Intrinsic</span>
              <span className={clsx(
                "font-mono font-semibold text-sm",
                stock.current_price != null && headerDcf.intrinsic_value > stock.current_price
                  ? "text-green"
                  : "text-red"
              )}>
                ${headerDcf.intrinsic_value.toFixed(2)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="px-6 pt-3 border-b border-bg-border flex gap-1 overflow-x-auto">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={clsx("tab-btn whitespace-nowrap", tab === t ? "tab-btn-active" : "tab-btn-inactive")}>
            {t}
          </button>
        ))}
      </div>

      {/* Period toggle — shown on financial data tabs */}
      {["Profitability", "Growth", "Cash Flow", "Balance Sheet"].includes(tab) && (
        <div className="px-6 py-2 border-b border-bg-border flex items-center gap-3 flex-wrap">
          <span className="text-xs text-muted">View:</span>
          {["annual", "quarter"].map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={clsx(
                "text-xs px-3 py-1 rounded border transition-colors",
                period === p
                  ? "border-accent-blue bg-accent-blue/15 text-accent-blue font-semibold"
                  : "border-bg-border text-muted hover:text-gray-300 hover:border-gray-500"
              )}
            >
              {p === "annual" ? "Annual" : "Quarterly"}
            </button>
          ))}
          {period === "quarter" && (() => {
            const available = financials?.length ?? 0;
            return (
              <>
                <span className="text-xs text-muted ml-2">Lookback:</span>
                {[4, 8, 12, 16, 20].map((q) => {
                  const disabled = q > available;
                  return (
                    <button
                      key={q}
                      onClick={() => !disabled && setQuarterLimit(q)}
                      disabled={disabled}
                      className={clsx(
                        "text-xs px-2.5 py-1 rounded border transition-colors",
                        disabled
                          ? "border-bg-border text-subtle opacity-40 cursor-not-allowed"
                          : quarterLimit === q
                          ? "border-yellow/60 bg-yellow/10 text-yellow font-semibold"
                          : "border-bg-border text-muted hover:text-gray-300 hover:border-gray-500"
                      )}
                    >
                      {q}Q
                    </button>
                  );
                })}
                <span className="text-[10px] text-subtle ml-1">
                  ({available} qtrs available)
                </span>
              </>
            );
          })()}
        </div>
      )}

      <div className="p-6">
        {/* VALUATION */}
        {tab === "Valuation" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-300 mb-4">Multiples</h3>
              <Row label="P/E Ratio" value={fmt(stock.pe_ratio)} />
              <Row label="P/B Ratio" value={fmt(stock.pb_ratio)} />
              <Row label="P/FCF" value={fmt(stock.pfcf_ratio)} />
              <Row label="P/S Ratio" value={fmt(stock.ps_ratio)} />
              <Row label="PEG Ratio" value={fmt(stock.peg_ratio)} />
              <Row label="EV/EBITDA" value={fmt(stock.ev_ebitda)} />
            </div>
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-300 mb-4">Market Data</h3>
              <Row label="Market Cap" value={fmtB(stock.market_cap)} />
              <Row label="Current Price" value={stock.current_price != null ? `$${stock.current_price.toFixed(2)}` : "—"} />
              <Row label="Shares Outstanding" value={fmtB(stock.shares_outstanding)} />
              <Row label="Beta" value={fmt(stock.beta)} />
              <Row label="Dividend Yield" value={fmt(stock.dividend_yield, true)} />
              <Row label="Payout Ratio" value={fmt(stock.payout_ratio, true)} />
            </div>
            <div className="card p-5 md:col-span-2">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">About</h3>
              {stock.description && (
                <p className="text-sm text-muted leading-relaxed mb-4">{stock.description}</p>
              )}
              <div className="grid grid-cols-2 gap-4 mt-2">
                <div className="bg-bg-hover rounded-lg p-3">
                  <div className="text-[10px] uppercase tracking-wider text-muted mb-2">Geography</div>
                  {[
                    stock.city && stock.state ? `${stock.city}, ${stock.state}` : stock.city || stock.state,
                    stock.country,
                  ].filter(Boolean).map((line, i) => (
                    <div key={i} className="text-sm text-gray-300">{line}</div>
                  ))}
                  {!stock.city && !stock.state && !stock.country && <div className="text-sm text-muted">—</div>}
                  {stock.employees && (
                    <div className="text-xs text-muted mt-1">{stock.employees.toLocaleString()} employees</div>
                  )}
                </div>
                <div className="bg-bg-hover rounded-lg p-3">
                  <div className="text-[10px] uppercase tracking-wider text-muted mb-2">Classification</div>
                  {stock.sector && <div className="text-sm text-gray-300">{stock.sector}</div>}
                  {stock.industry && <div className="text-xs text-muted mt-0.5">{stock.industry}</div>}
                  {!stock.sector && !stock.industry && <div className="text-sm text-muted">—</div>}
                </div>
              </div>
            </div>
            {/* Historical Multiples */}
            <div className="card p-5 md:col-span-2">
              <h3 className="text-sm font-semibold text-gray-300 mb-4">Valuation Multiples History</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-[10px] uppercase tracking-wider text-muted border-b border-bg-border">
                      <th className="text-left pb-2 font-medium">Metric</th>
                      <th className="text-right pb-2 font-medium">Current</th>
                      {multiplesHistory?.history?.slice(0, 5).map((h) => (
                        <th key={h.year} className="text-right pb-2 font-medium">{h.year}</th>
                      ))}
                      <th className="text-right pb-2 font-medium">5Y Avg</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { label: "P/E", current: stock.pe_ratio, key: "pe" },
                      { label: "P/B", current: stock.pb_ratio, key: "pb" },
                      { label: "P/FCF", current: stock.pfcf_ratio, key: "pfcf" },
                      { label: "EV/EBITDA", current: stock.ev_ebitda, key: "ev_ebitda" },
                      { label: "P/S", current: stock.ps_ratio, key: "ps" },
                    ].map(({ label, current, key }) => {
                      const avg5y = multiplesHistory?.avg_5y?.[key];
                      const pctDiff = current != null && avg5y != null ? (current - avg5y) / avg5y : null;
                      const currentColor = pctDiff == null ? "" : pctDiff > 0.2 ? "text-red" : pctDiff < -0.2 ? "text-green" : "text-gray-200";
                      return (
                        <tr key={label} className="border-b border-bg-border last:border-0">
                          <td className="py-2 text-muted">{label}</td>
                          <td className={clsx("py-2 text-right font-mono", currentColor)}>
                            {current != null ? current.toFixed(2) : "—"}
                          </td>
                          {multiplesHistory?.history?.slice(0, 5).map((h) => (
                            <td key={h.year} className="py-2 text-right font-mono text-muted text-xs">
                              {h[key] != null ? h[key].toFixed(2) : "—"}
                            </td>
                          ))}
                          <td className="py-2 text-right font-mono text-muted">
                            {avg5y != null ? avg5y.toFixed(2) : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <p className="text-[10px] text-muted mt-3">
                Current shown in <span className="text-green">green</span> if &gt;20% below 5Y avg (cheaper), <span className="text-red">red</span> if &gt;20% above (more expensive).
              </p>
            </div>
            <div className="md:col-span-2 flex flex-col gap-6">
              <ProductSegmentCharts data={segments} isLoading={segmentsLoading} />
              <GeoSegmentCharts data={segments} isLoading={segmentsLoading} />
            </div>
          </div>
        )}

        {/* PROFITABILITY */}
        {tab === "Profitability" && (() => {
          const f = financials?.[0];
          const ocfMargin = f?.operating_cash_flow && f?.revenue ? f.operating_cash_flow / f.revenue : null;
          const fcfMargin = f?.fcf && f?.revenue ? f.fcf / f.revenue : null;
          const fcfOnEquity = f?.fcf && f?.total_equity ? f.fcf / f.total_equity : null;
          const fcfOnAsset = f?.fcf && f?.total_assets ? f.fcf / f.total_assets : null;
          const cashToEquity = f?.cash && f?.total_equity ? f.cash / f.total_equity : null;
          const gpToAsset = f?.gross_profit && f?.total_assets ? f.gross_profit / f.total_assets : null;
          const qualityOfIncome = f?.operating_cash_flow && f?.net_income ? f.operating_cash_flow / f.net_income : null;
          const returnOnCapital = f?.operating_income && f?.total_equity && f?.total_debt
            ? f.operating_income / (f.total_equity + f.total_debt) : null;
          return (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-4">Returns</h3>
                <Row label="ROE" value={fmt(stock.roe, true)} />
                <Row label="ROIC" value={fmt(stock.roic, true)} />
                <Row label="ROA" value={fmt(stock.roa, true)} />
                <Row label="Return on Capital" value={fmt(returnOnCapital, true)} />
              </div>
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-4">Margins</h3>
                <Row label="Gross Margin" value={fmt(stock.gross_margin, true)} />
                <Row label="EBIT Margin" value={fmt(stock.operating_margin, true)} />
                <Row label="Net Profit Margin" value={fmt(stock.profit_margin, true)} />
                <Row label="Operating CF Margin" value={fmt(ocfMargin, true)} />
                <Row label="FCF Margin" value={fmt(fcfMargin, true)} />
                <Row label="Interest Coverage" value={fmt(stock.interest_coverage)} />
              </div>
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-4">Cash Flow Quality</h3>
                <Row label="FCF on Equity" value={fmt(fcfOnEquity, true)} />
                <Row label="FCF on Asset" value={fmt(fcfOnAsset, true)} />
                <Row label="Cash to Equity" value={fmt(cashToEquity, true)} />
                <Row label="Gross Profit to Asset" value={fmt(gpToAsset, true)} />
                <Row label="Quality of Income (OCF/NI)" value={qualityOfIncome != null ? qualityOfIncome.toFixed(2) : "—"} />
              </div>
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-4">Dividends</h3>
                <Row label="Dividend Yield" value={fmt(stock.dividend_yield, true)} />
                <Row label="Payout Ratio" value={fmt(stock.payout_ratio, true)} />
                <Row label="Dividend / Share" value={f?.dividend_per_share != null ? `$${f.dividend_per_share.toFixed(2)}` : "—"} />
              </div>
              <div className="md:col-span-2">
                <RevenueChart data={financials} isLoading={finLoading} period={period} quarterLimit={quarterLimit} />
              </div>
              <NetIncomeChart data={financials} isLoading={finLoading} period={period} quarterLimit={quarterLimit} />
              <EPSChart data={financials} isLoading={finLoading} period={period} quarterLimit={quarterLimit} />
            </div>
          );
        })()}

        {/* GROWTH */}
        {tab === "Growth" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-300 mb-4">Growth Rates (YoY)</h3>
              <Row label="Revenue Growth" value={fmt(stock.revenue_growth, true)} />
              <Row label="EPS Growth" value={fmt(stock.eps_growth, true)} />
              <Row label="FCF Growth" value={fmt(stock.fcf_growth, true)} />
            </div>
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-300 mb-4">Quality Signals</h3>
              <Row label="Piotroski F-Score" value={<PiotroskiBand score={stock.piotroski_score} />} />
              <Row label="Altman Z-Score" value={<AltmanBand z={stock.altman_z} />} />
              <Row label="Insider Ownership" value={fmt(stock.insider_ownership, true)} />
              <Row label="Institutional Ownership" value={fmt(stock.institutional_ownership, true)} />
            </div>
            <div className="md:col-span-2">
              <RevenueChart data={financials} isLoading={finLoading} period={period} quarterLimit={quarterLimit} />
            </div>
          </div>
        )}

        {/* CASH FLOW */}
        {tab === "Cash Flow" && (() => {
          const f = financials?.[0];
          const debtToFcf = f?.total_debt && f?.fcf && f.fcf > 0 ? f.total_debt / f.fcf : null;
          const qualityOfIncome = f?.operating_cash_flow && f?.net_income ? f.operating_cash_flow / f.net_income : null;
          return (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <FCFChart data={financials} isLoading={finLoading} period={period} quarterLimit={quarterLimit} />
              <DebtChart data={financials} isLoading={finLoading} period={period} quarterLimit={quarterLimit} />
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-4">Latest Cash Flow</h3>
                {f ? (
                  <>
                    <Row label="Operating Cash Flow" value={fmtB(f.operating_cash_flow)} />
                    <Row label="CapEx" value={fmtB(f.capex)} />
                    <Row label="Free Cash Flow" value={fmtB(f.fcf)} />
                    <Row label="FCF / Share" value={
                      f.fcf && stock.shares_outstanding
                        ? `$${(f.fcf / stock.shares_outstanding).toFixed(2)}`
                        : "—"
                    } />
                    <Row label="OCF Margin" value={f.operating_cash_flow && f.revenue ? `${(f.operating_cash_flow / f.revenue * 100).toFixed(1)}%` : "—"} />
                    <Row label="FCF Margin" value={f.fcf && f.revenue ? `${(f.fcf / f.revenue * 100).toFixed(1)}%` : "—"} />
                  </>
                ) : (
                  <p className="text-sm text-muted">No data available.</p>
                )}
              </div>
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-4">Cash Flow Quality</h3>
                {f ? (
                  <>
                    <Row label="Quality of Income (OCF/NI)" value={qualityOfIncome != null ? qualityOfIncome.toFixed(2) : "—"} />
                    <Row label="FCF on Equity" value={f.fcf && f.total_equity ? `${(f.fcf / f.total_equity * 100).toFixed(1)}%` : "—"} />
                    <Row label="FCF on Asset" value={f.fcf && f.total_assets ? `${(f.fcf / f.total_assets * 100).toFixed(1)}%` : "—"} />
                    <Row label="Debt to FCF" value={debtToFcf != null ? `${debtToFcf.toFixed(1)}x` : "—"} />
                  </>
                ) : (
                  <p className="text-sm text-muted">No data available.</p>
                )}
              </div>
            </div>
          );
        })()}

        {/* BALANCE SHEET */}
        {tab === "Balance Sheet" && (() => {
          const f = financials?.[0];
          const faToTa = f?.ppe && f?.total_assets ? f.ppe / f.total_assets : null;
          return (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-4">Liquidity & Solvency</h3>
                <Row label="Current Ratio" value={fmt(stock.current_ratio)} />
                <Row label="Quick Ratio" value={fmt(stock.quick_ratio)} />
                <Row label="Debt/Equity" value={fmt(stock.de_ratio)} />
                <Row label="Interest Coverage" value={fmt(stock.interest_coverage)} />
                <Row label="FA/TA (Fixed Asset Intensity)" value={faToTa != null ? `${(faToTa * 100).toFixed(1)}%` : "—"} />
              </div>
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-4">Assets</h3>
                {f ? (
                  <>
                    <Row label="Total Assets" value={fmtB(f.total_assets)} />
                    <Row label="Current Assets" value={fmtB(f.current_assets)} />
                    <Row label="Inventory" value={fmtB(f.inventory)} />
                    <Row label="Property, Plant & Equipment" value={fmtB(f.ppe)} />
                    <Row label="Cash" value={fmtB(f.cash)} />
                    <Row label="Retained Earnings" value={fmtB(f.retained_earnings)} />
                  </>
                ) : <p className="text-sm text-muted">No data available.</p>}
              </div>
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-4">Liabilities & Equity</h3>
                {f ? (
                  <>
                    <Row label="Total Liabilities" value={fmtB(f.total_liabilities)} />
                    <Row label="Total Equity" value={fmtB(f.total_equity)} />
                    <Row label="Total Debt" value={fmtB(f.total_debt)} />
                    <Row label="Long-Term Debt" value={fmtB(f.long_term_debt)} />
                    <Row label="Short-Term Debt" value={fmtB(f.short_term_debt)} />
                    <Row label="Net Debt" value={fmtB(f.net_debt)} />
                  </>
                ) : <p className="text-sm text-muted">No data available.</p>}
              </div>
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-gray-300 mb-4">Share Info</h3>
                <Row label="Shares Outstanding" value={f?.shares_outstanding != null ? `${(f.shares_outstanding / 1e6).toFixed(0)}M` : "—"} />
                <Row label="Market Cap" value={fmtB(stock.market_cap)} />
                <Row label="Dividend / Share" value={f?.dividend_per_share != null ? `$${f.dividend_per_share.toFixed(2)}` : "—"} />
                <Row label="Dividend Yield" value={fmt(stock.dividend_yield, true)} />
                <Row label="Payout Ratio" value={fmt(stock.payout_ratio, true)} />
              </div>
              <div className="md:col-span-2">
                <DebtChart data={financials} isLoading={finLoading} period={period} quarterLimit={quarterLimit} />
              </div>
            </div>
          );
        })()}

        {/* ANALYSIS */}
        {tab === "Analysis" && (
          <div className="flex flex-col gap-6">
            <ProductSegmentCharts data={segments} isLoading={segmentsLoading} />
            <GeoSegmentCharts data={segments} isLoading={segmentsLoading} />
            <SwotMoat ticker={ticker} />
          </div>
        )}

        {/* INSIDERS */}
        {tab === "Insiders" && (
          <div className="space-y-4">
            {/* Guru Holdings */}
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Top Guru Holdings</h3>
              {insiders?.gurus?.length > 0 ? (
                <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[500px]">
                  <thead>
                    <tr className="text-xs text-muted uppercase tracking-wider border-b border-bg-border">
                      <th className="text-left pb-2">Guru</th>
                      <th className="text-left pb-2 text-muted">Fund</th>
                      <th className="text-right pb-2">Shares</th>
                      <th className="text-right pb-2">Value</th>
                      <th className="text-right pb-2">% Out</th>
                      <th className="text-right pb-2">Reported</th>
                    </tr>
                  </thead>
                  <tbody>
                    {insiders.gurus.map((g, i) => (
                      <tr key={i} className="border-b border-bg-border/50 hover:bg-bg-hover transition-colors">
                        <td className="py-2.5 font-semibold text-accent-blue">{g.guru}</td>
                        <td className="py-2.5 text-muted text-xs">{g.holder}</td>
                        <td className="py-2.5 text-right font-mono text-xs">{g.shares != null ? g.shares.toLocaleString() : "—"}</td>
                        <td className="py-2.5 text-right font-mono text-xs">{g.value != null ? `$${(g.value / 1e6).toFixed(1)}M` : "—"}</td>
                        <td className="py-2.5 text-right font-mono text-xs">{g.pct_out != null ? `${(g.pct_out * 100).toFixed(2)}%` : "—"}</td>
                        <td className="py-2.5 text-right text-muted text-xs">{g.date_reported ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              ) : (
                <p className="text-muted text-sm">No major guru holdings found for this stock.</p>
              )}
            </div>

            {/* Insider Transactions */}
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Insider Transactions</h3>
              {insiders?.transactions?.length > 0 ? (
                <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[480px]">
                  <thead>
                    <tr className="text-xs text-muted uppercase tracking-wider border-b border-bg-border">
                      <th className="text-left pb-2">Insider</th>
                      <th className="text-left pb-2">Position</th>
                      <th className="text-left pb-2">Type</th>
                      <th className="text-right pb-2">Shares</th>
                      <th className="text-right pb-2">Value</th>
                      <th className="text-right pb-2">Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {insiders.transactions.map((t, i) => {
                      const isBuy = t.transaction_type?.toLowerCase().includes("buy") ||
                                    t.transaction_type?.toLowerCase().includes("purchase") ||
                                    t.transaction_type?.toLowerCase().includes("acquisition");
                      return (
                        <tr key={i} className="border-b border-bg-border/50 hover:bg-bg-hover transition-colors">
                          <td className="py-2.5 font-medium text-gray-200">{t.name ?? "—"}</td>
                          <td className="py-2.5 text-muted text-xs">{t.position ?? "—"}</td>
                          <td className="py-2.5">
                            <span className={clsx(
                              "text-xs px-2 py-0.5 rounded font-semibold",
                              isBuy ? "bg-green-bg text-green border border-green/20"
                                     : "bg-red-bg text-red border border-red/20"
                            )}>
                              {t.transaction_type ?? "—"}
                            </span>
                          </td>
                          <td className="py-2.5 text-right font-mono text-xs">{t.shares != null ? Number(t.shares).toLocaleString() : "—"}</td>
                          <td className="py-2.5 text-right font-mono text-xs">{t.value != null ? `$${(t.value / 1e6).toFixed(2)}M` : "—"}</td>
                          <td className="py-2.5 text-right text-muted text-xs">{t.date ?? "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                </div>
              ) : (
                <p className="text-muted text-sm">No recent insider transactions found.</p>
              )}
            </div>
          </div>
        )}

        {/* DCF */}
        {tab === "DCF" && (
          <DCFCalculator
            ticker={ticker}
            currentPrice={stock.current_price}
            stock={stock}
            financials={financials}
            multiplesHistory={multiplesHistory}
            defaultGrowthRate={defaultGrowthRate}
          />
        )}
      </div>
    </div>
  );
}
