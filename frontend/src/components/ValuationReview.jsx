import clsx from "clsx";
import { useValuationReview } from "../hooks/useStockDetail";

const VERDICT_STYLE = {
  "Deeply Undervalued": "text-green border-green/30 bg-green/10",
  "Undervalued":        "text-green border-green/30 bg-green/5",
  "Fairly Valued":      "text-accent-blue border-accent-blue/30 bg-accent-blue/5",
  "Overvalued":         "text-yellow border-yellow/30 bg-yellow/10",
  "Richly Priced":      "text-red border-red/30 bg-red/10",
  "Insufficient Data":  "text-muted border-bg-border",
};

const CONFIDENCE_DOT = {
  High:   "bg-green",
  Medium: "bg-yellow",
  Low:    "bg-red",
};

function fmt(v, prefix = "$") {
  if (v == null) return "—";
  return `${prefix}${v.toFixed(2)}`;
}

function pct(v) {
  if (v == null) return "—";
  return `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
}

export default function ValuationReview({ ticker }) {
  const { data, isLoading, isError } = useValuationReview(ticker);

  if (isLoading) return <div className="card p-5 text-sm text-muted animate-pulse">Calculating…</div>;
  if (isError || !data) return <div className="card p-5 text-sm text-muted">Valuation review unavailable — refresh stock data first.</div>;

  const verdictClass = VERDICT_STYLE[data.verdict] ?? VERDICT_STYLE["Insufficient Data"];

  return (
    <div className="flex flex-col gap-4">
      {/* Verdict card */}
      <div className="card p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-xs text-muted uppercase tracking-wider mb-1">Overall Verdict</div>
            <span className={clsx("text-sm font-semibold px-3 py-1 rounded-full border", verdictClass)}>
              {data.verdict}
            </span>
          </div>
          {data.current_price != null && (
            <div className="text-right">
              <div className="text-xs text-muted uppercase tracking-wider mb-1">Current Price</div>
              <div className="font-mono font-semibold text-gray-100">${data.current_price.toFixed(2)}</div>
            </div>
          )}
          {data.fair_value_range && (
            <div className="text-right">
              <div className="text-xs text-muted uppercase tracking-wider mb-1">Fair Value Range</div>
              <div className="font-mono font-semibold text-accent-blue">
                ${data.fair_value_range.low.toFixed(2)} – ${data.fair_value_range.high.toFixed(2)}
              </div>
              <div className="text-xs text-muted">mid ${data.fair_value_range.mid.toFixed(2)}</div>
            </div>
          )}
          {data.margin_of_safety != null && (
            <div className="text-right">
              <div className="text-xs text-muted uppercase tracking-wider mb-1">Margin of Safety</div>
              <div className={clsx(
                "font-mono font-semibold",
                data.margin_of_safety > 20 ? "text-green" : data.margin_of_safety > 0 ? "text-yellow" : "text-red"
              )}>
                {data.margin_of_safety.toFixed(1)}%
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Valuation methods */}
      {data.methods?.length > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Valuation Methods</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[500px]">
              <thead>
                <tr className="text-xs text-muted uppercase tracking-wider border-b border-bg-border">
                  <th className="text-left pb-2 font-medium">Method</th>
                  <th className="text-right pb-2 font-medium">Fair Value</th>
                  <th className="text-right pb-2 font-medium">Upside</th>
                  <th className="text-right pb-2 font-medium">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {data.methods.map((m, i) => (
                  <tr key={i} className="border-b border-bg-border/50">
                    <td className="py-3">
                      <div className="font-medium text-gray-200">{m.name}</div>
                      <div className="text-xs text-muted mt-0.5 max-w-sm leading-relaxed">{m.notes}</div>
                    </td>
                    <td className="py-3 text-right font-mono text-gray-100">{fmt(m.fair_value)}</td>
                    <td className={clsx(
                      "py-3 text-right font-mono font-semibold",
                      m.upside > 15 ? "text-green" : m.upside > 0 ? "text-yellow" : "text-red"
                    )}>
                      {pct(m.upside)}
                    </td>
                    <td className="py-3 text-right">
                      <span className="flex items-center justify-end gap-1.5">
                        <span className={clsx("w-1.5 h-1.5 rounded-full", CONFIDENCE_DOT[m.confidence] ?? "bg-muted")} />
                        <span className="text-xs text-muted">{m.confidence}</span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Key observations */}
      {data.key_observations?.length > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Key Observations</h3>
          <ul className="space-y-2">
            {data.key_observations.map((obs, i) => (
              <li key={i} className="text-sm text-muted leading-relaxed flex gap-2">
                <span className="text-accent-blue mt-0.5 shrink-0">·</span>
                {obs}
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="text-[10px] text-subtle text-center">
        Rule-based analysis from quantitative metrics only. Not financial advice. Always conduct your own due diligence.
      </p>
    </div>
  );
}
