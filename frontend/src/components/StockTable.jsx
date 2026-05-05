import { useNavigate } from "react-router-dom";
import GuruScoreRing from "./GuruScoreRing";
import { MetricBadge } from "./Badge";
import clsx from "clsx";

function fmt(v, pct = false, decimals = 2) {
  if (v == null) return <span className="text-subtle">—</span>;
  const n = pct ? `${(v * 100).toFixed(1)}%` : v.toFixed(decimals);
  return <span className="font-mono">{n}</span>;
}

function fmtCap(v) {
  if (v == null) return <span className="text-subtle">—</span>;
  const b = v / 1e9;
  return <span className="font-mono">{b >= 1000 ? `$${(b / 1000).toFixed(1)}T` : `$${b.toFixed(1)}B`}</span>;
}

const COLS = [
  { key: "ticker", label: "Ticker", width: "w-24" },
  { key: "guru_score", label: "Score", width: "w-16" },
  { key: "current_price", label: "Price", width: "w-20" },
  { key: "market_cap", label: "Mkt Cap", width: "w-24" },
  { key: "pe_ratio", label: "P/E", width: "w-16" },
  { key: "pfcf_ratio", label: "P/FCF", width: "w-16" },
  { key: "roe", label: "ROE", width: "w-16" },
  { key: "roic", label: "ROIC", width: "w-16" },
  { key: "de_ratio", label: "D/E", width: "w-16" },
  { key: "profit_margin", label: "Margin", width: "w-16" },
  { key: "revenue_growth", label: "Rev ↑", width: "w-16" },
  { key: "eps_growth", label: "EPS ↑", width: "w-16" },
  { key: "piotroski_score", label: "Pio", width: "w-12" },
  { key: "altman_z", label: "Z", width: "w-16" },
  { key: "dividend_yield", label: "Div", width: "w-16" },
];

export default function StockTable({ stocks, isLoading, isWatched, onToggleWatch }) {
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Loading stocks…</span>
        </div>
      </div>
    );
  }

  if (!stocks?.length) {
    return (
      <div className="flex items-center justify-center h-64 text-muted">
        <div className="text-center">
          <div className="text-4xl mb-3">🔍</div>
          <p className="text-sm">No stocks match your filters.</p>
          <p className="text-xs mt-1">Try relaxing the criteria or adding stocks via the search.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-bg-border">
            {onToggleWatch && (
              <th className="py-2 px-2 w-8 text-center text-xs text-muted">☆</th>
            )}
            {COLS.map((c) => (
              <th
                key={c.key}
                className={clsx(
                  "text-left py-2 px-3 text-xs text-muted uppercase tracking-wider font-medium whitespace-nowrap",
                  c.width
                )}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {stocks.map((stock) => (
            <tr
              key={stock.ticker}
              onClick={() => navigate(`/stock/${stock.ticker}`)}
              className="border-b border-bg-border hover:bg-bg-hover cursor-pointer transition-colors group"
            >
              {onToggleWatch && (
                <td className="py-2.5 px-2 text-center" onClick={(e) => e.stopPropagation()}>
                  <button
                    onClick={() => onToggleWatch(stock.ticker)}
                    className={clsx(
                      "text-base leading-none transition-colors",
                      isWatched?.(stock.ticker) ? "text-yellow" : "text-subtle hover:text-yellow"
                    )}
                    title={isWatched?.(stock.ticker) ? "Remove from watchlist" : "Add to watchlist"}
                  >
                    {isWatched?.(stock.ticker) ? "★" : "☆"}
                  </button>
                </td>
              )}
              <td className="py-2.5 px-3">
                <div className="font-mono font-semibold text-accent-blue group-hover:text-blue-300 transition-colors">
                  {stock.ticker}
                </div>
                <div className="text-xs text-muted truncate max-w-[80px]">{stock.sector}</div>
              </td>

              <td className="py-2.5 px-3">
                <GuruScoreRing score={stock.guru_score} size={36} />
              </td>

              <td className="py-2.5 px-3 font-mono">
                {stock.current_price != null ? `$${stock.current_price.toFixed(2)}` : <span className="text-subtle">—</span>}
              </td>

              <td className="py-2.5 px-3">{fmtCap(stock.market_cap)}</td>

              <td className="py-2.5 px-3">
                <MetricBadge value={stock.pe_ratio} good={15} bad={40} invert />
              </td>

              <td className="py-2.5 px-3">
                <MetricBadge value={stock.pfcf_ratio} good={12} bad={40} invert />
              </td>

              <td className="py-2.5 px-3">
                <MetricBadge value={stock.roe} good={0.20} bad={0} pct />
              </td>

              <td className="py-2.5 px-3">
                <MetricBadge value={stock.roic} good={0.15} bad={0} pct />
              </td>

              <td className="py-2.5 px-3">
                <MetricBadge value={stock.de_ratio} good={0.5} bad={2.0} invert />
              </td>

              <td className="py-2.5 px-3">
                <MetricBadge value={stock.profit_margin} good={0.15} bad={0} pct />
              </td>

              <td className="py-2.5 px-3">
                <MetricBadge value={stock.revenue_growth} good={0.15} bad={0} pct />
              </td>

              <td className="py-2.5 px-3">
                <MetricBadge value={stock.eps_growth} good={0.15} bad={0} pct />
              </td>

              <td className="py-2.5 px-3">
                {stock.piotroski_score != null ? (
                  <span
                    className={clsx(
                      "font-mono font-semibold",
                      stock.piotroski_score >= 7 ? "text-green" : stock.piotroski_score >= 4 ? "text-yellow" : "text-red"
                    )}
                  >
                    {stock.piotroski_score}/9
                  </span>
                ) : (
                  <span className="text-subtle">—</span>
                )}
              </td>

              <td className="py-2.5 px-3">
                {stock.altman_z != null ? (
                  <span
                    className={clsx(
                      "font-mono font-semibold",
                      stock.altman_z > 2.99 ? "text-green" : stock.altman_z > 1.81 ? "text-yellow" : "text-red"
                    )}
                  >
                    {stock.altman_z.toFixed(2)}
                  </span>
                ) : (
                  <span className="text-subtle">—</span>
                )}
              </td>

              <td className="py-2.5 px-3">
                {stock.dividend_yield != null ? (
                  <span className="font-mono">{(stock.dividend_yield * 100).toFixed(2)}%</span>
                ) : (
                  <span className="text-subtle">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
