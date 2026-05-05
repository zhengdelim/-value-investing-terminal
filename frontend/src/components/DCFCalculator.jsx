import { useState, useEffect } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useDCF } from "../hooks/useStockDetail";
import clsx from "clsx";

const TT = {
  contentStyle: { backgroundColor: "#181b28", border: "1px solid #242736", borderRadius: "8px", fontSize: 12, color: "#e5e7eb" },
  labelStyle: { color: "#9ca3af" },
};

const MOS_LEVELS = [
  { pct: 0,  label: "No Buffer"      },
  { pct: 10, label: "Conservative"   },
  { pct: 15, label: "Moderate"       },
  { pct: 20, label: "Standard"       },
  { pct: 25, label: "Cautious"       },
  { pct: 30, label: "Defensive"      },
  { pct: 40, label: "Deep Value"     },
  { pct: 50, label: "Ultra-Discount" },
];

// Financial-sector keywords — P/B is more appropriate for these
const FINANCIAL_SECTORS = ["financial", "bank", "insurance", "asset management", "capital markets"];

function isFinancialSector(sector) {
  if (!sector) return false;
  return FINANCIAL_SECTORS.some((k) => sector.toLowerCase().includes(k));
}

function Slider({ label, value, min, max, step, onChange, format }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between">
        <span className="text-xs text-muted uppercase tracking-wider">{label}</span>
        <span className="text-xs font-mono text-accent-blue">{format(value)}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-accent-blue" />
    </div>
  );
}

function Stat({ label, value, accent }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-muted uppercase tracking-wider">{label}</span>
      <span className={clsx("font-mono font-semibold text-lg", accent ?? "text-gray-100")}>{value}</span>
    </div>
  );
}

function updownColor(val) {
  if (val == null) return "text-gray-400";
  return val >= 0 ? "text-green" : "text-red";
}

function fmtPct(v) {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${(v * 100).toFixed(1)}%`;
}

function fmtPrice(v) {
  return v != null ? `$${v.toFixed(2)}` : "—";
}

// One row in the multiple valuation table
function MultRow({ label, avgMultiple, fairValue, mosPrice, updown, mosPct }) {
  const ud = updown != null ? (fairValue - updown) / updown : null; // updown param = currentPrice
  return (
    <tr className="border-b border-bg-border last:border-0 hover:bg-bg-hover transition-colors">
      <td className="py-2.5 px-3 text-sm text-gray-300 font-medium">{label}</td>
      <td className="py-2.5 px-3 text-right font-mono text-sm text-gray-200">
        {avgMultiple != null ? avgMultiple.toFixed(1) : "—"}
      </td>
      <td className="py-2.5 px-3 text-right font-mono text-sm text-gray-100 font-semibold">
        {fmtPrice(fairValue)}
      </td>
      <td className="py-2.5 px-3 text-right font-mono text-sm text-yellow font-semibold">
        {fmtPrice(mosPrice)}
        {mosPct != null && <span className="text-xs text-muted ml-1">(-{mosPct}%)</span>}
      </td>
      <td className={clsx("py-2.5 px-3 text-right font-mono text-sm font-semibold", updownColor(ud))}>
        {ud != null ? fmtPct(ud) : "—"}
      </td>
      <td className="py-2.5 px-3 text-center">
        {ud != null && (
          ud >= 0.1
            ? <span className="text-xs font-semibold text-green bg-green/10 border border-green/20 px-2 py-0.5 rounded-full">Undervalued</span>
            : ud <= -0.1
            ? <span className="text-xs text-red bg-red/10 border border-red/20 px-2 py-0.5 rounded-full">Overvalued</span>
            : <span className="text-xs text-muted bg-bg-hover border border-bg-border px-2 py-0.5 rounded-full">Fair</span>
        )}
      </td>
    </tr>
  );
}

// Builds valuation rows from multiples data
function buildRows(multiples, eps, bvps, rps, currentPrice, profitable, isFinancial) {
  if (!currentPrice) return [];
  const rows = [];

  const addRow = (label, multiple, perShare, mosPct) => {
    if (multiple == null || perShare == null || perShare <= 0) return;
    const fairValue = multiple * perShare;
    const mosPrice = fairValue * (1 - mosPct / 100);
    rows.push({ label, avgMultiple: multiple, fairValue, mosPrice, mosPct, currentPrice });
  };

  if (profitable || isFinancial) {
    if (!isFinancial && eps) {
      addRow(`P/E — 5Y Avg`, multiples?.avg_5y?.pe, eps, 15);
      addRow(`P/E — 10Y Avg`, multiples?.avg_10y?.pe, eps, 15);
    }
    if (bvps) {
      addRow(`P/B — 5Y Avg`, multiples?.avg_5y?.pb, bvps, 25);
      addRow(`P/B — 10Y Avg`, multiples?.avg_10y?.pb, bvps, 25);
    }
  }

  if (!profitable) {
    if (rps) {
      addRow(`P/S — 5Y Avg`, multiples?.avg_5y?.ps, rps, 25);
      addRow(`P/S — 10Y Avg`, multiples?.avg_10y?.ps, rps, 25);
    }
  }

  return rows;
}

const pct = (v) => `${(v * 100).toFixed(1)}%`;
const yr = (v) => `${v}y`;

export default function DCFCalculator({ ticker, currentPrice, stock, financials, multiplesHistory, defaultGrowthRate }) {
  const [params, setParams] = useState({
    growth_rate: 0.10,
    terminal_growth: 0.03,
    discount_rate: 0.10,
    years: 10,
  });
  const [growthSet, setGrowthSet] = useState(false);

  useEffect(() => {
    if (!growthSet && defaultGrowthRate != null) {
      setParams((p) => ({ ...p, growth_rate: defaultGrowthRate }));
      setGrowthSet(true);
    }
  }, [defaultGrowthRate, growthSet]);

  const { data: dcf, isLoading, isError } = useDCF(ticker, params);

  const price = currentPrice ?? dcf?.current_price;
  const iv = dcf?.intrinsic_value;

  const upPct = dcf?.upside_downside != null
    ? `${dcf.upside_downside >= 0 ? "+" : ""}${(dcf.upside_downside * 100).toFixed(1)}%`
    : "—";

  const chartData = dcf?.projections?.map((p) => ({
    year: `Y${p.year}`,
    "FCF ($M)": Math.round(p.fcf / 1e6),
    "PV ($M)": Math.round(p.present_value / 1e6),
  })) ?? [];

  // --- Multiple-based valuation inputs ---
  const f = financials?.[0];
  const netIncome = f?.net_income ?? 0;
  const profitable = netIncome > 0;
  const isFinancial = isFinancialSector(stock?.sector);

  const eps = f?.eps_diluted ?? f?.eps ?? null;
  const bvps = (f?.total_equity && f?.shares_outstanding && f.shares_outstanding > 0)
    ? f.total_equity / f.shares_outstanding : null;
  const rps = (f?.revenue && f?.shares_outstanding && f.shares_outstanding > 0)
    ? f.revenue / f.shares_outstanding : null;

  const multRows = buildRows(multiplesHistory, eps, bvps, rps, price, profitable, isFinancial);

  const companyType = !profitable ? "Non-Profitable" : isFinancial ? "Financial (P/B focus)" : "Profitable";

  return (
    <div className="flex flex-col gap-6">

      {/* Multiple-Based Valuation */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-sm font-semibold text-gray-300">Multiple-Based Valuation</h3>
          <span className={clsx(
            "text-xs px-2 py-0.5 rounded-full border font-medium",
            !profitable
              ? "text-orange-400 border-orange-400/30 bg-orange-400/10"
              : isFinancial
              ? "text-blue-400 border-blue-400/30 bg-blue-400/10"
              : "text-green border-green/30 bg-green/10"
          )}>
            {companyType}
          </span>
        </div>
        <p className="text-xs text-muted mb-4">
          {!profitable
            ? "Uses P/S (Price-to-Sales) — company has negative earnings."
            : isFinancial
            ? "Uses P/B (Price-to-Book) — financial sector. MoS 25%."
            : "Uses P/E (15% MoS) and P/B (25% MoS) based on historical average multiples."}
        </p>

        {/* Per-share inputs */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          {[
            { label: "EPS (Diluted)", value: eps, fmt: (v) => `$${v.toFixed(2)}` },
            { label: "Book Value / Share", value: bvps, fmt: (v) => `$${v.toFixed(2)}` },
            { label: "Revenue / Share", value: rps, fmt: (v) => `$${v.toFixed(2)}` },
          ].map(({ label, value, fmt }) => (
            <div key={label} className="bg-bg-hover rounded-lg p-3 text-center">
              <div className="text-[10px] text-muted uppercase tracking-wider mb-1">{label}</div>
              <div className="font-mono text-sm font-semibold text-gray-200">
                {value != null ? fmt(value) : "—"}
              </div>
            </div>
          ))}
        </div>

        {multRows.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bg-border text-[10px] text-muted uppercase tracking-wider">
                  <th className="text-left py-2 px-3">Method</th>
                  <th className="text-right py-2 px-3">Avg Multiple</th>
                  <th className="text-right py-2 px-3">Fair Value</th>
                  <th className="text-right py-2 px-3">MoS Buy Price</th>
                  <th className="text-right py-2 px-3">Upside / Down</th>
                  <th className="text-center py-2 px-3">Signal</th>
                </tr>
              </thead>
              <tbody>
                {multRows.map((r) => (
                  <MultRow key={r.label} {...r} updown={r.currentPrice} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-muted text-center py-4">
            No historical multiple data available. Force-refresh the stock to fetch ratios.
          </p>
        )}

        <div className="mt-3 flex gap-4 text-[10px] text-muted border-t border-bg-border pt-3">
          <span>Fair Value = Avg Multiple × Per-Share Metric</span>
          <span>·</span>
          <span>P/E MoS: 15% · P/B, P/S MoS: 25%</span>
          <span>·</span>
          <span>Current Price: {price != null ? `$${price.toFixed(2)}` : "—"}</span>
        </div>
      </div>

      {/* DCF Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Sliders */}
        <div className="card p-5 flex flex-col gap-5">
          <h3 className="text-sm font-semibold text-gray-300">DCF Assumptions</h3>
          <Slider label="FCF Growth Rate" value={params.growth_rate} min={-0.2} max={0.5} step={0.01}
            onChange={(v) => setParams((p) => ({ ...p, growth_rate: v }))} format={pct} />
          <Slider label="Terminal Growth" value={params.terminal_growth} min={0.01} max={0.08} step={0.005}
            onChange={(v) => setParams((p) => ({ ...p, terminal_growth: v }))} format={pct} />
          <Slider label="Discount Rate (WACC)" value={params.discount_rate} min={0.04} max={0.25} step={0.005}
            onChange={(v) => setParams((p) => ({ ...p, discount_rate: v }))} format={pct} />
          <Slider label="Projection Years" value={params.years} min={3} max={20} step={1}
            onChange={(v) => setParams((p) => ({ ...p, years: v }))} format={yr} />
        </div>

        {/* Core DCF output */}
        <div className="card p-5 flex flex-col gap-4">
          <h3 className="text-sm font-semibold text-gray-300">DCF Valuation Output</h3>
          {isLoading ? (
            <div className="flex-1 flex items-center justify-center text-muted text-sm gap-2">
              <div className="w-4 h-4 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
              Calculating…
            </div>
          ) : isError ? (
            <div className="text-red text-sm">No FCF data available for DCF.</div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-4">
                <Stat label="Intrinsic Value" value={iv != null ? `$${iv.toFixed(2)}` : "—"} accent="text-accent-blue" />
                <Stat label="Current Price" value={price != null ? `$${price.toFixed(2)}` : "—"} />
                <Stat label="Upside / Downside" value={upPct}
                  accent={dcf?.upside_downside >= 0 ? "text-green" : "text-red"} />
                <Stat label="Base FCF"
                  value={dcf?.base_fcf != null ? `$${(dcf.base_fcf / 1e9).toFixed(1)}B` : "—"} />
              </div>
              <div className="border-t border-bg-border pt-3 grid grid-cols-2 gap-1.5 text-xs text-muted">
                <div className="flex justify-between"><span>PV of FCFs</span><span className="font-mono">{dcf?.total_pv_fcf != null ? `$${(dcf.total_pv_fcf / 1e9).toFixed(1)}B` : "—"}</span></div>
                <div className="flex justify-between"><span>Terminal Value</span><span className="font-mono">{dcf?.terminal_value != null ? `$${(dcf.terminal_value / 1e9).toFixed(1)}B` : "—"}</span></div>
                <div className="flex justify-between"><span>PV Terminal</span><span className="font-mono">{dcf?.terminal_value_pv != null ? `$${(dcf.terminal_value_pv / 1e9).toFixed(1)}B` : "—"}</span></div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Margin of Safety scenarios */}
      {iv != null && price != null && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-1">DCF — Margin of Safety Buy Prices</h3>
          <p className="text-xs text-muted mb-4">
            Intrinsic value discounted by each buffer level. Green = current price is below the buy target.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bg-border text-xs text-muted uppercase tracking-wider">
                  <th className="text-left py-2 px-3">Buffer</th>
                  <th className="text-left py-2 px-3">Strategy</th>
                  <th className="text-right py-2 px-3">Buy Below</th>
                  <th className="text-right py-2 px-3">vs Current</th>
                  <th className="text-center py-2 px-3">Signal</th>
                </tr>
              </thead>
              <tbody>
                {MOS_LEVELS.map(({ pct: mos, label }) => {
                  const buyPrice = iv * (1 - mos / 100);
                  const diff = (price - buyPrice) / buyPrice;
                  const isBelow = price <= buyPrice;
                  return (
                    <tr key={mos}
                      className={clsx(
                        "border-b border-bg-border transition-colors",
                        isBelow ? "bg-green-bg/40 hover:bg-green-bg/60" : "hover:bg-bg-hover"
                      )}
                    >
                      <td className="py-2.5 px-3 font-mono font-semibold text-gray-200">{mos}%</td>
                      <td className="py-2.5 px-3 text-muted text-xs">{label}</td>
                      <td className={clsx("py-2.5 px-3 text-right font-mono font-semibold",
                        isBelow ? "text-green" : "text-gray-300")}>
                        ${buyPrice.toFixed(2)}
                      </td>
                      <td className={clsx("py-2.5 px-3 text-right font-mono text-xs",
                        isBelow ? "text-green" : "text-red")}>
                        {diff >= 0 ? "+" : ""}{(diff * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        {isBelow
                          ? <span className="text-xs font-semibold text-green bg-green-bg border border-green/20 px-2 py-0.5 rounded-full">Buy Zone ✓</span>
                          : <span className="text-xs text-muted bg-bg-hover border border-bg-border px-2 py-0.5 rounded-full">Above Target</span>
                        }
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* FCF Projection Chart */}
      {chartData.length > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">FCF Projections ($M)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="fcfGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#4f8ef7" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#4f8ef7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#242736" />
              <XAxis dataKey="year" tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip {...TT} />
              <Area type="monotone" dataKey="FCF ($M)" stroke="#4f8ef7" fill="url(#fcfGrad)" strokeWidth={2} />
              <Area type="monotone" dataKey="PV ($M)" stroke="#22c55e" fill="none" strokeWidth={1.5} strokeDasharray="4 2" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
