import GuruScoreRing from "./GuruScoreRing";
import clsx from "clsx";

function StatCard({ label, value, sub, accent }) {
  return (
    <div className="card p-4 flex flex-col gap-1">
      <span className="text-xs text-muted uppercase tracking-wider">{label}</span>
      <span className={clsx("font-mono text-2xl font-semibold", accent ?? "text-gray-100")}>
        {value ?? "—"}
      </span>
      {sub && <span className="text-xs text-muted">{sub}</span>}
    </div>
  );
}

export default function ScoreCards({ stocks }) {
  if (!stocks?.length) return null;

  const withScore = stocks.filter((s) => s.guru_score != null);
  const avg =
    withScore.length > 0
      ? Math.round(withScore.reduce((a, s) => a + s.guru_score, 0) / withScore.length)
      : null;

  const undervalued = stocks.filter((s) => s.guru_value != null && s.guru_value >= 70).length;
  const topPick = withScore.sort((a, b) => b.guru_score - a.guru_score)[0];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
      <StatCard
        label="Stocks Screened"
        value={stocks.length}
        sub="matching filters"
      />
      <StatCard
        label="Avg GuruScore"
        value={avg}
        sub="across all results"
        accent={avg >= 70 ? "text-green" : avg >= 45 ? "text-yellow" : "text-red"}
      />
      <StatCard
        label="Undervalued"
        value={undervalued}
        sub="Value score ≥ 70"
        accent="text-accent-blue"
      />
      {topPick && (
        <div className="card p-4 flex items-center gap-3">
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
