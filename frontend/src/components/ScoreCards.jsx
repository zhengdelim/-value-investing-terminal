import { useNavigate } from "react-router-dom";
import GuruScoreRing from "./GuruScoreRing";
import clsx from "clsx";

function StatCard({ label, value, sub, accent, onClick, active }) {
  return (
    <div
      onClick={onClick}
      className={clsx(
        "card p-4 flex flex-col gap-1 transition-colors",
        onClick && "cursor-pointer hover:border-accent-blue/50",
        active && "border-accent-blue/60 bg-accent-blue/5",
      )}
    >
      <span className="text-xs text-muted uppercase tracking-wider">{label}</span>
      <span className={clsx("font-mono text-2xl font-semibold", accent ?? "text-gray-100")}>
        {value ?? "—"}
      </span>
      {sub && (
        <span className={clsx("text-xs", active ? "text-accent-blue" : "text-muted")}>
          {active ? "click to clear filter" : sub}
        </span>
      )}
    </div>
  );
}

export default function ScoreCards({ stocks, activeFilter, onFilter }) {
  const navigate = useNavigate();
  if (!stocks?.length) return null;

  const withScore = stocks.filter((s) => s.guru_score != null);
  const avg =
    withScore.length > 0
      ? Math.round(withScore.reduce((a, s) => a + s.guru_score, 0) / withScore.length)
      : null;

  const undervalued = stocks.filter((s) => s.guru_value != null && s.guru_value >= 70).length;
  const highQuality = withScore.filter((s) => s.guru_score >= 70).length;
  const topPick = [...withScore].sort((a, b) => b.guru_score - a.guru_score)[0];

  const toggle = (key) => onFilter?.(activeFilter === key ? null : key);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
      <StatCard
        label="Stocks Screened"
        value={stocks.length}
        sub="matching filters"
      />
      <StatCard
        label="High Quality"
        value={highQuality}
        sub="GuruScore ≥ 70 · click to filter"
        accent={avg >= 70 ? "text-green" : avg >= 45 ? "text-yellow" : "text-red"}
        onClick={() => toggle("quality")}
        active={activeFilter === "quality"}
      />
      <StatCard
        label="Undervalued"
        value={undervalued}
        sub="Value score ≥ 70 · click to filter"
        accent="text-accent-blue"
        onClick={() => toggle("undervalued")}
        active={activeFilter === "undervalued"}
      />
      {topPick && (
        <div
          onClick={() => navigate(`/stock/${topPick.ticker}`)}
          className="card p-4 flex items-center gap-3 cursor-pointer hover:border-accent-blue/50 transition-colors"
        >
          <GuruScoreRing score={topPick.guru_score} size={52} />
          <div className="min-w-0">
            <div className="text-xs text-muted uppercase tracking-wider mb-0.5">Top Pick</div>
            <div className="font-mono font-semibold text-accent-blue truncate">{topPick.ticker}</div>
            <div className="text-xs text-muted truncate">{topPick.name}</div>
          </div>
        </div>
      )}
    </div>
  );
}
