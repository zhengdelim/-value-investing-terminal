import clsx from "clsx";
import { useResearch } from "../hooks/useStockDetail";

const TIER_COLOR = {
  Premium:       "text-green border-green/30 bg-green/10",
  "High Quality":"text-accent-blue border-accent-blue/30 bg-accent-blue/10",
  Average:       "text-yellow border-yellow/30 bg-yellow/10",
  "Below Average":"text-red border-red/30 bg-red/10",
};

const GROWTH_COLOR = {
  "High Growth":     "text-green",
  "Moderate Growth": "text-accent-blue",
  "Slow Growth":     "text-yellow",
  Declining:         "text-red",
  Unknown:           "text-muted",
};

const FORTRESS_COLOR = {
  Fortress:   "text-green",
  Stable:     "text-accent-blue",
  Stretched:  "text-yellow",
  Distressed: "text-red",
};

function Badge({ label, colorClass }) {
  return (
    <span className={clsx("text-xs font-semibold px-2.5 py-1 rounded-full border", colorClass)}>
      {label}
    </span>
  );
}

function Section({ title, items, emptyMsg = "No signals." }) {
  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-gray-300 mb-3">{title}</h3>
      {items?.length > 0 ? (
        <ul className="space-y-2">
          {items.map((s, i) => (
            <li key={i} className="text-sm text-muted leading-relaxed flex gap-2">
              <span className="text-accent-blue mt-0.5 shrink-0">·</span>
              {s}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted">{emptyMsg}</p>
      )}
    </div>
  );
}

export default function MarketResearch({ ticker }) {
  const { data, isLoading, isError } = useResearch(ticker);

  if (isLoading) return <div className="card p-5 text-sm text-muted animate-pulse">Analysing…</div>;
  if (isError || !data) return <div className="card p-5 text-sm text-muted">Research unavailable — refresh stock data first.</div>;

  return (
    <div className="flex flex-col gap-4">
      {/* Summary badges */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-gray-300 mb-4">Business Profile</h3>
        <div className="flex flex-wrap gap-3 mb-5">
          <Badge label={data.quality_tier} colorClass={TIER_COLOR[data.quality_tier] ?? "text-muted border-bg-border"} />
          <Badge
            label={data.growth_profile}
            colorClass={clsx("border-bg-border", GROWTH_COLOR[data.growth_profile] ?? "text-muted")}
          />
          <Badge
            label={`${data.fortress_tier} Balance Sheet`}
            colorClass={clsx("border-bg-border", FORTRESS_COLOR[data.fortress_tier] ?? "text-muted")}
          />
          {data.sector_context?.name && (
            <Badge label={data.sector_context.name} colorClass="text-muted border-bg-border" />
          )}
        </div>
        {data.sector_context?.ctx && (
          <p className="text-xs text-muted leading-relaxed italic border-l-2 border-bg-border pl-3">
            {data.sector_context.ctx}
          </p>
        )}
      </div>

      {/* Investment Thesis */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">Investment Thesis</h3>
        <ul className="space-y-2">
          {data.investment_thesis?.map((t, i) => (
            <li key={i} className="text-sm text-gray-300 leading-relaxed flex gap-2">
              <span className="text-green mt-0.5 shrink-0">✓</span>
              {t}
            </li>
          ))}
        </ul>
      </div>

      {/* Key Risks */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">Key Risks</h3>
        <ul className="space-y-2">
          {data.key_risks?.map((r, i) => (
            <li key={i} className="text-sm text-muted leading-relaxed flex gap-2">
              <span className="text-red mt-0.5 shrink-0">!</span>
              {r}
            </li>
          ))}
        </ul>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Section title="Capital Efficiency" items={data.efficiency_signals} />
        <Section title="Growth Signals" items={data.growth_signals} />
        <Section title="Financial Fortress" items={data.fortress_signals} />
      </div>
    </div>
  );
}
