import { useState } from "react";
import clsx from "clsx";

function SliderField({ label, field, value, min, max, step, onChange, pct = false }) {
  const display = value === "" || value === null || value === undefined ? "Any" : pct ? `${(value * 100).toFixed(0)}%` : value;
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between items-center">
        <label className="text-xs text-muted uppercase tracking-wider">{label}</label>
        <span className="text-xs font-mono text-accent-blue">{display}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value === "" || value == null ? min : value}
        onChange={(e) => onChange(field, e.target.value === String(min) ? "" : Number(e.target.value))}
        className="w-full accent-accent-blue cursor-pointer"
      />
    </div>
  );
}

function Section({ title, children }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="border-b border-bg-border pb-4 mb-4 last:border-0 last:mb-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex justify-between items-center mb-3 text-left"
      >
        <span className="text-xs font-semibold uppercase tracking-widest text-gray-400">{title}</span>
        <span className="text-muted text-xs">{open ? "▲" : "▼"}</span>
      </button>
      {open && <div className="flex flex-col gap-3">{children}</div>}
    </div>
  );
}

const PRESETS = [
  {
    id: "adam_khoo",
    label: "Adam Khoo",
    description: "ROE≥15 · ROIC≥10 · D/E≤0.5 · EPS↑8% · Margin≥10%",
    color: "text-yellow border-yellow/30 hover:bg-yellow/10",
    filters: {
      roe_min: 0.15, roic_min: 0.10, de_max: 0.5,
      profit_margin_min: 0.10, eps_growth_min: 0.08,
      revenue_growth_min: 0.01,
      // fcf_growth_min intentionally omitted — many stocks have NULL fcf_growth
    },
  },
  {
    id: "deep_value",
    label: "Deep Value",
    description: "P/E≤15 · P/FCF≤12 · ROE≥12 · D/E≤1",
    color: "text-green border-green/30 hover:bg-green/10",
    filters: {
      pe_max: 15, pfcf_max: 12, roe_min: 0.12, de_max: 1.0,
    },
  },
  {
    id: "quality_growth",
    label: "Quality Growth",
    description: "ROE≥20 · ROIC≥15 · EPS↑15% · Rev↑15%",
    color: "text-accent-blue border-accent-blue/30 hover:bg-accent-blue/10",
    filters: {
      roe_min: 0.20, roic_min: 0.15,
      eps_growth_min: 0.15, revenue_growth_min: 0.15,
    },
  },
];

export default function Sidebar({ filters, onChange, onReset, onPreset, mobileOpen, onMobileClose }) {
  return (
    <>
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/60 z-40 md:hidden" onClick={onMobileClose} />
      )}
    <aside className={clsx(
      "w-64 shrink-0 bg-bg-secondary border-r border-bg-border overflow-y-auto flex flex-col z-50",
      mobileOpen
        ? "fixed inset-y-0 left-0 h-full"
        : "hidden md:flex md:sticky md:top-0 md:h-screen"
    )}>
      <div className="p-4 border-b border-bg-border flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">
            <span className="text-accent-blue font-mono">VS</span>
            <span className="ml-2 text-gray-100">ValueScreen</span>
          </h1>
          <p className="text-xs text-muted mt-0.5">Value Investing Terminal</p>
        </div>
        {mobileOpen && (
          <button onClick={onMobileClose}
            className="md:hidden text-muted hover:text-gray-200 text-lg leading-none p-1">✕</button>
        )}
      </div>

      <div className="p-4 flex-1">
        {/* Presets */}
        <div className="mb-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-widest">Presets</span>
          </div>
          <div className="flex flex-col gap-1.5">
            {PRESETS.map((p) => (
              <button
                key={p.id}
                onClick={() => onPreset && onPreset((prev) => ({ ...prev, ...p.filters }))}
                className={`text-left px-3 py-2 rounded-lg border text-xs transition-colors ${p.color}`}
              >
                <div className="font-semibold">{p.label}</div>
                <div className="text-[10px] text-muted mt-0.5 leading-tight">{p.description}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="flex justify-between items-center mb-4">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-widest">Filters</span>
          <button onClick={onReset} className="text-xs text-muted hover:text-gray-300 transition-colors">
            Reset
          </button>
        </div>

        <Section title="Valuation">
          <SliderField label="P/E Max" field="pe_max" value={filters.pe_max} min={0} max={100} step={1} onChange={onChange} />
          <SliderField label="P/FCF Max" field="pfcf_max" value={filters.pfcf_max} min={0} max={100} step={1} onChange={onChange} />
          <SliderField label="EV/EBITDA Max" field="ev_ebitda_max" value={filters.ev_ebitda_max} min={0} max={50} step={1} onChange={onChange} />
        </Section>

        <Section title="Quality">
          <SliderField label="ROE Min" field="roe_min" value={filters.roe_min} min={0} max={0.5} step={0.01} onChange={onChange} pct />
          <SliderField label="ROIC Min" field="roic_min" value={filters.roic_min} min={0} max={0.5} step={0.01} onChange={onChange} pct />
          <SliderField label="Net Margin Min" field="profit_margin_min" value={filters.profit_margin_min} min={0} max={0.5} step={0.01} onChange={onChange} pct />
        </Section>

        <Section title="Growth">
          <SliderField label="Revenue Growth Min" field="revenue_growth_min" value={filters.revenue_growth_min} min={0} max={1} step={0.01} onChange={onChange} pct />
          <SliderField label="EPS Growth Min" field="eps_growth_min" value={filters.eps_growth_min} min={0} max={1} step={0.01} onChange={onChange} pct />
          <SliderField label="FCF Growth Min" field="fcf_growth_min" value={filters.fcf_growth_min} min={0} max={1} step={0.01} onChange={onChange} pct />
        </Section>

        <Section title="Financial Strength">
          <SliderField label="D/E Max" field="de_max" value={filters.de_max} min={0} max={5} step={0.1} onChange={onChange} />
          <SliderField label="Altman Z Min" field="altman_z_min" value={filters.altman_z_min} min={0} max={5} step={0.1} onChange={onChange} />
          <SliderField label="Piotroski Min" field="piotroski_min" value={filters.piotroski_min} min={0} max={9} step={1} onChange={onChange} />
        </Section>

        <Section title="Income & Ownership">
          <SliderField label="Dividend Yield Min" field="dividend_yield_min" value={filters.dividend_yield_min} min={0} max={0.15} step={0.005} onChange={onChange} pct />
          <SliderField label="Insider Ownership Min" field="insider_ownership_min" value={filters.insider_ownership_min} min={0} max={0.5} step={0.01} onChange={onChange} pct />
        </Section>

        <Section title="Market Cap">
          <SliderField label="Min ($B)" field="market_cap_min" value={filters.market_cap_min} min={0} max={500e9} step={1e9} onChange={onChange} />
          <SliderField label="Max ($B)" field="market_cap_max" value={filters.market_cap_max} min={0} max={3000e9} step={10e9} onChange={onChange} />
        </Section>
      </div>
    </aside>
    </>
  );
}
