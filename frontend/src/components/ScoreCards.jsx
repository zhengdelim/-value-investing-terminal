import { useNavigate } from "react-router-dom";
import GuruScoreRing from "./GuruScoreRing";
import clsx from "clsx";

function FilterCard({ label, value, sub, accent, onClick, active, icon }) {
  return (
    <div
      onClick={onClick}
      className={clsx(
        "card p-4 flex flex-col gap-1.5 transition-colors",
        onClick && "cursor-pointer hover:border-accent-blue/50",
        active && "border-accent-blue/60 bg-accent-blue/5",
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted uppercase tracking-wider">{label}</span>
        {icon && <span className="text-base opacity-60">{icon}</span>}
      </div>
      <span className={clsx("font-mono text-2xl font-semibold", accent ?? "text-gray-100")}>
        {value ?? "—"}
      </span>
      <span className={clsx("text-xs leading-snug", active ? "text-accent-blue" : "text-muted")}>
        {active ? "↩ click to clear filter" : sub}
      </span>
    </div>
  );
}

export default function ScoreCards({ stocks, activeFilter, onFilter }) {
  const navigate = useNavigate();
  if (!stocks?.length) return null;

  const withScore = stocks.filter((s) => s.guru_score != null);
  const avgScore = withScore.length > 0
    ? Math.round(withScore.reduce((a, s) => a + s.guru_score, 0) / withScore.length)
    : null;

  const highQuality  = withScore.filter((s) => s.guru_score >= 70).length;

  const undervalued  = stocks.filter(
    (s) => s.guru_score != null && s.guru_score > 80
         && s.dcf_upside != null && s.dcf_upside > 0.30
         && s.roe != null && s.roe > 0.15,
  ).length;

  const deepValue    = stocks.filter(
    (s) => s.pe_ratio != null && s.pe_ratio > 0 && s.pe_ratio < 15
         && s.pb_ratio != null && s.pb_ratio > 0 && s.pb_ratio < 1.5,
  ).length;

  const dividendIncome = stocks.filter(
    (s) => s.dividend_yield != null && s.dividend_yield >= 0.02,
  ).length;

  const topPick = [...withScore].sort((a, b) => b.guru_score - a.guru_score)[0];

  const toggle = (key) => onFilter?.(activeFilter === key ? null : key);

  const avgColor = avgScore == null ? "text-muted"
    : avgScore >= 70 ? "text-green"
    : avgScore >= 45 ? "text-yellow"
    : "text-red";

  return (
    <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3 mb-4">
      {/* Overview — not a filter, just summary */}
      <div className="card p-4 flex flex-col gap-1.5">
        <span className="text-xs text-muted uppercase tracking-wider">Screened</span>
        <span className="font-mono text-2xl font-semibold text-gray-100">{stocks.length}</span>
        <span className={clsx("text-xs font-semibold", avgColor)}>
          Avg Score {avgScore ?? "—"}
          <span className="font-normal text-muted"> / 100</span>
        </span>
      </div>

      <FilterCard
        label="High Quality"
        value={highQuality}
        sub="GuruScore ≥ 70"
        accent={avgScore >= 70 ? "text-green" : avgScore >= 45 ? "text-yellow" : "text-red"}
        icon="⭐"
        onClick={() => toggle("quality")}
        active={activeFilter === "quality"}
      />

      <FilterCard
        label="Undervalued"
        value={undervalued}
        sub="Score>80 · DCF>30% · ROE>15%"
        accent="text-accent-blue"
        icon="🎯"
        onClick={() => toggle("undervalued")}
        active={activeFilter === "undervalued"}
      />

      <FilterCard
        label="Deep Value"
        value={deepValue}
        sub="P/E < 15 · P/B < 1.5"
        accent="text-yellow"
        icon="💎"
        onClick={() => toggle("deepvalue")}
        active={activeFilter === "deepvalue"}
      />

      <FilterCard
        label="Dividend Income"
        value={dividendIncome}
        sub="Yield ≥ 2%"
        accent="text-green"
        icon="💰"
        onClick={() => toggle("dividend")}
        active={activeFilter === "dividend"}
      />

      {/* Top Pick */}
      {topPick ? (
        <div
          onClick={() => navigate(`/stock/${topPick.ticker}`)}
          className="card p-4 flex items-center gap-3 cursor-pointer hover:border-accent-blue/50 transition-colors"
        >
          <GuruScoreRing score={topPick.guru_score} size={48} />
          <div className="min-w-0">
            <div className="text-xs text-muted uppercase tracking-wider mb-0.5">Top Pick</div>
            <div className="font-mono font-semibold text-accent-blue truncate">{topPick.ticker}</div>
            <div className="text-xs text-muted truncate">{topPick.name}</div>
          </div>
        </div>
      ) : (
        <div className="card p-4" />
      )}
    </div>
  );
}
