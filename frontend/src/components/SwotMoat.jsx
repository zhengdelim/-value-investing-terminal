import clsx from "clsx";
import { useQuery } from "@tanstack/react-query";
import { fetchAnalysis } from "../lib/api";

const SWOT_CONFIG = {
  strengths:    { label: "Strengths",    icon: "↑", color: "text-green",  bg: "bg-green-bg  border-green/20"  },
  weaknesses:   { label: "Weaknesses",   icon: "↓", color: "text-red",    bg: "bg-red-bg    border-red/20"    },
  opportunities:{ label: "Opportunities",icon: "◆", color: "text-accent-blue", bg: "bg-accent-blue/10 border-accent-blue/20" },
  threats:      { label: "Threats",      icon: "▲", color: "text-yellow", bg: "bg-yellow-bg border-yellow/20" },
};

function SwotQuadrant({ type, items }) {
  const { label, icon, color, bg } = SWOT_CONFIG[type];
  return (
    <div className={clsx("card border p-4 flex flex-col gap-2", bg)}>
      <div className={clsx("flex items-center gap-2 mb-1", color)}>
        <span className="font-mono font-bold">{icon}</span>
        <span className="text-xs font-semibold uppercase tracking-widest">{label}</span>
        <span className="ml-auto font-mono text-xs opacity-60">{items.length}</span>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-muted italic">None identified from current metrics.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {items.map((item, i) => (
            <li key={i} className="flex gap-2 text-sm text-gray-300 leading-relaxed">
              <span className={clsx("mt-1 shrink-0 text-xs", color)}>•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function MoatBar({ score }) {
  const color = score >= 65 ? "#22c55e" : score >= 35 ? "#f59e0b" : "#ef4444";
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-3 bg-bg-hover rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
      <span className="font-mono font-semibold text-sm" style={{ color }}>{score}</span>
    </div>
  );
}

const STRENGTH_COLORS = {
  Wide:    "bg-green-bg text-green border border-green/20",
  Narrow:  "bg-yellow-bg text-yellow border border-yellow/20",
  Likely:  "bg-accent-blue/10 text-accent-blue border border-accent-blue/20",
  "None / Uncertain": "bg-red-bg text-red border border-red/20",
};

export default function SwotMoat({ ticker }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["analysis", ticker],
    queryFn: () => fetchAnalysis(ticker),
    enabled: !!ticker,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48 text-muted text-sm gap-3">
        <div className="w-5 h-5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
        Analysing {ticker}…
      </div>
    );
  }

  if (isError || !data) {
    return <div className="text-red text-sm p-4">Could not load analysis. Fetch stock detail first.</div>;
  }

  const { swot, moat } = data;

  return (
    <div className="flex flex-col gap-6">
      {/* SWOT Grid */}
      <div>
        <h3 className="text-sm font-semibold text-gray-300 mb-3">SWOT Analysis</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SwotQuadrant type="strengths"     items={swot.strengths} />
          <SwotQuadrant type="weaknesses"    items={swot.weaknesses} />
          <SwotQuadrant type="opportunities" items={swot.opportunities} />
          <SwotQuadrant type="threats"       items={swot.threats} />
        </div>
      </div>

      {/* Moat Analysis */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-300">Economic Moat</h3>
          <span
            className={clsx(
              "text-xs font-semibold px-3 py-1 rounded-full",
              STRENGTH_COLORS[moat.width] ?? STRENGTH_COLORS["None / Uncertain"]
            )}
          >
            {moat.width}
          </span>
        </div>

        <div className="mb-4">
          <div className="flex justify-between text-xs text-muted mb-1">
            <span>Moat Score</span>
            <span className="font-mono">{moat.score} / 100</span>
          </div>
          <MoatBar score={moat.score} />
          <div className="flex justify-between text-[10px] text-subtle mt-1">
            <span>None / Uncertain</span>
            <span>Narrow Moat</span>
            <span>Wide Moat</span>
          </div>
        </div>

        {moat.signals.length === 0 ? (
          <p className="text-sm text-muted italic">No clear moat signals identified from available metrics.</p>
        ) : (
          <div className="flex flex-col">
            {moat.signals.map((s, i) => (
              <div key={i} className="border-t border-bg-border pt-4 pb-1 first:border-0 first:pt-0">
                <div className="flex gap-3 items-start">
                  <div className="flex flex-col items-center gap-1 shrink-0 w-24">
                    <span className="text-xs font-semibold text-gray-300 text-center leading-tight">{s.source}</span>
                    <span
                      className={clsx(
                        "text-[10px] px-2 py-0.5 rounded-full font-mono",
                        STRENGTH_COLORS[s.strength] ?? "bg-bg-hover text-muted"
                      )}
                    >
                      {s.strength}
                    </span>
                  </div>
                  <div className="flex-1 flex flex-col gap-2">
                    <p className="text-sm text-gray-200 font-medium leading-relaxed">{s.detail}</p>
                    {s.smart && (
                      <div className="flex flex-col gap-1.5 text-xs text-muted leading-relaxed">
                        {s.smart.specific && <p>{s.smart.specific}</p>}
                        {s.smart.assessment && <p>{s.smart.assessment}</p>}
                        {(s.smart.risk || s.smart.timeframe) && (
                          <div className="flex flex-col gap-1 pt-1 border-t border-bg-border mt-0.5">
                            {s.smart.risk && (
                              <p><span className="text-red font-semibold">Risk: </span>{s.smart.risk}</p>
                            )}
                            {s.smart.timeframe && (
                              <p><span className="text-gray-400 font-semibold">Horizon: </span>{s.smart.timeframe}</p>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <p className="text-xs text-subtle italic">
        Analysis is rule-based and derived from quantitative metrics. It does not substitute for fundamental research.
      </p>
    </div>
  );
}
