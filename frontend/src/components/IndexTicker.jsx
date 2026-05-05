import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { fetchIndices } from "../lib/api";

const STATE_DOT = {
  "Open":         "bg-green",
  "Pre-market":   "bg-yellow",
  "After-hours":  "bg-yellow",
  "Closed":       "bg-subtle",
  "Unknown":      "bg-subtle",
};

function fmt(price, currency) {
  if (price == null) return "—";
  // For large index values (>1000) no decimal; smaller ones 2dp
  const decimals = price >= 1000 ? 2 : 2;
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(price);
}

function IndexCard({ d }) {
  const up      = d.change_pct != null && d.change_pct > 0;
  const down    = d.change_pct != null && d.change_pct < 0;
  const flat    = !up && !down;
  const dotCls  = STATE_DOT[d.market_state] ?? "bg-subtle";

  return (
    <div className="flex flex-col gap-0.5 px-5 py-3 border-r border-bg-border last:border-0 min-w-[130px]">
      {/* Label + market state dot */}
      <div className="flex items-center gap-1.5">
        <span className={clsx("w-1.5 h-1.5 rounded-full shrink-0", dotCls)} />
        <span className="text-[10px] font-semibold text-muted uppercase tracking-widest">
          {d.label}
        </span>
        <span className="text-[9px] text-subtle ml-auto">{d.market_state}</span>
      </div>

      {/* Price */}
      <div className="font-mono font-bold text-base text-gray-100 leading-none">
        {fmt(d.price, d.currency)}
        <span className="text-[9px] font-normal text-subtle ml-1">{d.currency}</span>
      </div>

      {/* Change */}
      <div className={clsx(
        "flex items-center gap-1.5 text-xs font-mono",
        up ? "text-green" : down ? "text-red" : "text-muted"
      )}>
        <span>{up ? "▲" : down ? "▼" : "—"}</span>
        <span>
          {d.change != null ? `${d.change >= 0 ? "+" : ""}${fmt(d.change, d.currency)}` : "—"}
        </span>
        <span className="text-[11px]">
          {d.change_pct != null ? `(${d.change_pct >= 0 ? "+" : ""}${d.change_pct.toFixed(2)}%)` : ""}
        </span>
      </div>

      {/* Day range */}
      {(d.day_low != null && d.day_high != null) && (
        <div className="text-[9px] text-subtle font-mono mt-0.5">
          L {fmt(d.day_low)} · H {fmt(d.day_high)}
        </div>
      )}
    </div>
  );
}

function IndexCardSkeleton() {
  return (
    <div className="flex flex-col gap-1.5 px-5 py-3 border-r border-bg-border last:border-0 min-w-[130px] animate-pulse">
      <div className="h-2 bg-bg-hover rounded w-16" />
      <div className="h-5 bg-bg-hover rounded w-24 mt-0.5" />
      <div className="h-3 bg-bg-hover rounded w-20" />
      <div className="h-2 bg-bg-hover rounded w-28 mt-0.5" />
    </div>
  );
}

function SnapshotTime({ ts }) {
  if (!ts) return null;
  const d = new Date(ts);
  const date = d.toLocaleDateString("en-SG", { day: "2-digit", month: "short", year: "numeric" });
  const time = d.toLocaleTimeString("en-SG", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
  return (
    <div className="flex flex-col items-end justify-center px-5 shrink-0 border-l border-bg-border">
      <span className="text-[9px] text-subtle uppercase tracking-widest">Snapshot</span>
      <span className="text-[11px] font-mono text-gray-400 whitespace-nowrap">{date}</span>
      <span className="text-[13px] font-mono font-semibold text-gray-200 whitespace-nowrap leading-tight">{time}</span>
    </div>
  );
}

export default function IndexTicker() {
  const { data, isLoading, dataUpdatedAt } = useQuery({
    queryKey: ["market-indices"],
    queryFn:  fetchIndices,
    staleTime: 1000 * 60 * 3,
    refetchInterval: 1000 * 60 * 3,
    refetchOnWindowFocus: true,
  });

  return (
    <div className="bg-bg-secondary border-b border-bg-border overflow-x-auto">
      <div className="flex">
        <div className="flex min-w-0 flex-1">
          {isLoading
            ? Array.from({ length: 4 }).map((_, i) => <IndexCardSkeleton key={i} />)
            : (data ?? []).map((d) => <IndexCard key={d.key} d={d} />)
          }
        </div>
        {!isLoading && <SnapshotTime ts={dataUpdatedAt} />}
      </div>
    </div>
  );
}
