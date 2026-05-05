import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import api from "../lib/api";

function fetchAnalysis() { return api.get("/market-analysis").then((r) => r.data); }
function fetchRawNews()   { return api.get("/news").then((r) => r.data); }

// ── Helpers ──────────────────────────────────────────────────────────────────

function timeAgo(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  if (isNaN(d)) return dateStr.slice(0, 10);
  const mins = Math.floor((Date.now() - d.getTime()) / 60000);
  if (mins < 60)   return `${mins}m ago`;
  if (mins < 1440) return `${Math.floor(mins / 60)}h ago`;
  return `${Math.floor(mins / 1440)}d ago`;
}

const SENTIMENT = {
  bullish: { label: "Bullish", cls: "text-green  bg-green-bg  border-green/20"  },
  bearish: { label: "Bearish", cls: "text-red    bg-red-bg    border-red/20"    },
  neutral: { label: "Neutral", cls: "text-muted  bg-bg-hover  border-bg-border" },
  positive:{ label: "Positive",cls: "text-green  bg-green-bg  border-green/20"  },
  negative:{ label: "Negative",cls: "text-red    bg-red-bg    border-red/20"    },
};

function SentimentBadge({ value }) {
  if (!value) return null;
  const s = SENTIMENT[value?.toLowerCase()] ?? SENTIMENT.neutral;
  return (
    <span className={clsx("text-[10px] font-semibold border px-2 py-0.5 rounded-full shrink-0", s.cls)}>
      {s.label}
    </span>
  );
}

// ── Section components ────────────────────────────────────────────────────────

function SectionHeader({ icon, title, count, accent }) {
  return (
    <div className={clsx("flex items-center gap-2 mb-3 pb-2 border-b border-bg-border")}>
      <span className="text-base">{icon}</span>
      <h3 className={clsx("font-semibold text-sm", accent ?? "text-gray-200")}>{title}</h3>
      {count != null && (
        <span className="ml-auto text-[10px] font-mono text-muted">{count} items</span>
      )}
    </div>
  );
}

function BreakingCard({ item }) {
  return (
    <div className="flex flex-col gap-1.5 py-3 border-b border-bg-border last:border-0">
      <div className="flex items-start gap-2">
        <p className="text-sm text-gray-200 leading-snug flex-1">{item.headline}</p>
        <SentimentBadge value={item.sentiment} />
      </div>
      {item.impact && (
        <p className="text-xs text-muted leading-relaxed">{item.impact}</p>
      )}
    </div>
  );
}

function MoveCard({ item }) {
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-bg-border last:border-0">
      <div className="shrink-0 w-20 text-xs font-mono font-semibold text-accent-blue truncate">
        {item.asset}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-200 leading-snug">{item.move}</p>
        {item.note && <p className="text-xs text-muted mt-0.5">{item.note}</p>}
      </div>
    </div>
  );
}

function MacroCard({ item }) {
  return (
    <div className="flex flex-col gap-1 py-3 border-b border-bg-border last:border-0">
      <div className="flex items-center gap-2">
        <p className="text-sm font-medium text-gray-200 flex-1 leading-snug">{item.theme}</p>
        <SentimentBadge value={item.sentiment} />
      </div>
      {item.detail && <p className="text-xs text-muted">{item.detail}</p>}
    </div>
  );
}

function NarrativeCard({ item }) {
  return (
    <div className="card p-4 flex flex-col gap-3">
      <h4 className="text-sm font-semibold text-gray-200">{item.title}</h4>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="bg-green-bg/30 border border-green/10 rounded-lg p-3">
          <div className="text-[10px] font-semibold text-green uppercase tracking-widest mb-1.5">Bull Case</div>
          <p className="text-xs text-gray-300 leading-relaxed">{item.bull_case}</p>
        </div>
        <div className="bg-red-bg/30 border border-red/10 rounded-lg p-3">
          <div className="text-[10px] font-semibold text-red uppercase tracking-widest mb-1.5">Bear Case</div>
          <p className="text-xs text-gray-300 leading-relaxed">{item.bear_case}</p>
        </div>
      </div>
      {item.consensus && (
        <div className="bg-bg-hover rounded-lg p-3 border border-bg-border">
          <div className="text-[10px] font-semibold text-muted uppercase tracking-widest mb-1">Consensus</div>
          <p className="text-xs text-gray-300">{item.consensus}</p>
        </div>
      )}
    </div>
  );
}

function InsightCard({ item, index }) {
  const colors = ["text-accent-blue", "text-green", "text-yellow", "text-accent-purple", "text-muted"];
  return (
    <div className="flex gap-3 py-3 border-b border-bg-border last:border-0">
      <div className={clsx("font-mono font-bold text-lg shrink-0 w-6 text-center", colors[index % colors.length])}>
        {index + 1}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-200 leading-snug">{item.insight}</p>
        {item.watch && (
          <p className="text-xs text-muted mt-1">
            <span className="text-accent-blue font-semibold">Watch: </span>{item.watch}
          </p>
        )}
        {item.timeframe && (
          <span className="text-[10px] font-mono text-muted bg-bg-hover border border-bg-border rounded px-1.5 py-0.5 mt-1 inline-block">
            {item.timeframe}
          </span>
        )}
      </div>
    </div>
  );
}

// ── Raw news feed ─────────────────────────────────────────────────────────────

function RawNewsCard({ item }) {
  return (
    <a href={item.url} target="_blank" rel="noopener noreferrer"
      className="card flex gap-4 p-4 hover:bg-bg-hover transition-colors group">
      {item.image && (
        <img src={item.image} alt="" className="w-20 h-14 object-cover rounded shrink-0 bg-bg-hover"
          onError={(e) => { e.currentTarget.style.display = "none"; }} />
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <span className="text-[10px] font-semibold text-accent-blue bg-accent-blue/10 border border-accent-blue/20 px-2 py-0.5 rounded-full">
            {item.source}
          </span>
          <span className="text-[10px] text-subtle ml-auto">{timeAgo(item.published)}</span>
        </div>
        <h3 className="text-sm font-semibold text-gray-200 leading-snug group-hover:text-accent-blue transition-colors line-clamp-2">
          {item.title}
        </h3>
        {item.summary && (
          <p className="text-xs text-muted mt-1 line-clamp-1">{item.summary}</p>
        )}
      </div>
    </a>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function SkeletonSection({ lines = 3 }) {
  return (
    <div className="card p-5 animate-pulse">
      <div className="h-4 bg-bg-hover rounded w-1/3 mb-4" />
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-3 bg-bg-hover rounded mb-2" style={{ width: `${70 + (i % 3) * 10}%` }} />
      ))}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

const VIEW_TABS = [
  { id: "briefing", label: "AI Briefing" },
  { id: "feed",     label: "Raw Feed"    },
];

export default function MarketNews() {
  const [view, setView] = useState("briefing");

  const {
    data: analysis, isLoading: aLoading, isError: aError, refetch: aRefetch, isFetching: aFetching,
  } = useQuery({
    queryKey: ["market-analysis"],
    queryFn: fetchAnalysis,
    staleTime: 1000 * 60 * 30,
    refetchOnWindowFocus: false,
  });

  const {
    data: rawNews, isLoading: nLoading,
  } = useQuery({
    queryKey: ["market-news"],
    queryFn: fetchRawNews,
    staleTime: 1000 * 60 * 15,
    refetchOnWindowFocus: false,
    enabled: view === "feed",
  });

  const isAI = analysis?.ai_powered;

  return (
    <div className="p-6">
      {/* Header row */}
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div>
          <h2 className="text-base font-semibold text-gray-200">Market Intelligence</h2>
          <p className="text-xs text-muted mt-0.5">
            {analysis
              ? <>
                  {analysis.article_count} articles · {analysis.sources?.slice(0, 4).join(", ")}
                  {analysis.sources?.length > 4 && ` +${analysis.sources.length - 4} more`}
                </>
              : "Aggregating from Yahoo Finance, CNBC, MarketWatch, Investing.com…"
            }
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* View switcher */}
          <div className="flex bg-bg-secondary border border-bg-border rounded-lg p-0.5">
            {VIEW_TABS.map((t) => (
              <button key={t.id} onClick={() => setView(t.id)}
                className={clsx(
                  "px-3 py-1 text-xs rounded-md transition-colors",
                  view === t.id ? "bg-accent-blue text-white" : "text-muted hover:text-gray-300"
                )}>
                {t.label}
              </button>
            ))}
          </div>

          {/* Refresh */}
          <button onClick={() => aRefetch()} disabled={aFetching}
            className={clsx(
              "text-xs px-3 py-1.5 rounded border flex items-center gap-1.5 transition-colors",
              aFetching ? "border-bg-border text-muted cursor-not-allowed"
                        : "border-accent-blue/40 text-accent-blue hover:bg-accent-blue/10"
            )}>
            {aFetching ? <><span className="w-3 h-3 border border-accent-blue border-t-transparent rounded-full animate-spin" />Refreshing…</> : "↻ Refresh"}
          </button>
        </div>
      </div>

      {/* AI badge */}
      {!aLoading && view === "briefing" && (
        <div className={clsx(
          "flex items-center gap-2 text-xs mb-5 px-3 py-2 rounded-lg border",
          isAI
            ? "bg-accent-blue/10 border-accent-blue/20 text-accent-blue"
            : "bg-bg-hover border-bg-border text-muted"
        )}>
          <span>{isAI ? "⚡" : "📋"}</span>
          {isAI
            ? "Analysis generated by Claude AI from live market headlines"
            : <>Rule-based summary · Add <code className="font-mono bg-bg-secondary px-1 rounded">ANTHROPIC_API_KEY</code> to <code className="font-mono bg-bg-secondary px-1 rounded">.env</code> for AI-powered analysis</>
          }
        </div>
      )}

      {/* ── BRIEFING VIEW ─────────────────────────────────────────── */}
      {view === "briefing" && (
        <>
          {aLoading ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {Array.from({ length: 5 }).map((_, i) => <SkeletonSection key={i} lines={4} />)}
            </div>
          ) : aError ? (
            <div className="card p-6 text-sm text-red text-center">
              Could not load market analysis. Check backend connection.
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

              {/* Breaking News */}
              <div className="card p-5">
                <SectionHeader icon="🔴" title="Breaking News" accent="text-red"
                  count={analysis?.breaking_news?.length} />
                {(analysis?.breaking_news ?? []).map((item, i) => (
                  <BreakingCard key={i} item={item} />
                ))}
                {!analysis?.breaking_news?.length && (
                  <p className="text-sm text-muted italic">No breaking items.</p>
                )}
              </div>

              {/* Market Moves */}
              <div className="card p-5">
                <SectionHeader icon="📊" title="Market Moves" accent="text-accent-blue"
                  count={analysis?.market_moves?.length} />
                {(analysis?.market_moves ?? []).map((item, i) => (
                  <MoveCard key={i} item={item} />
                ))}
                {!analysis?.market_moves?.length && (
                  <p className="text-sm text-muted italic">No notable moves identified.</p>
                )}
              </div>

              {/* Macro Themes */}
              <div className="card p-5">
                <SectionHeader icon="🌍" title="Macro Themes" accent="text-yellow"
                  count={analysis?.macro_themes?.length} />
                {(analysis?.macro_themes ?? []).map((item, i) => (
                  <MacroCard key={i} item={item} />
                ))}
                {!analysis?.macro_themes?.length && (
                  <p className="text-sm text-muted italic">No macro items identified.</p>
                )}
              </div>

              {/* Actionable Insights */}
              <div className="card p-5">
                <SectionHeader icon="🎯" title="Actionable Insights" accent="text-green"
                  count={analysis?.actionable_insights?.length} />
                {(analysis?.actionable_insights ?? []).map((item, i) => (
                  <InsightCard key={i} item={item} index={i} />
                ))}
                {!analysis?.actionable_insights?.length && (
                  <p className="text-sm text-muted italic">No insights available.</p>
                )}
              </div>

              {/* Key Narratives — full width */}
              {analysis?.key_narratives?.length > 0 && (
                <div className="lg:col-span-2 flex flex-col gap-4">
                  <SectionHeader icon="💡" title="Key Narratives" accent="text-accent-purple"
                    count={analysis.key_narratives.length} />
                  {analysis.key_narratives.map((item, i) => (
                    <NarrativeCard key={i} item={item} />
                  ))}
                </div>
              )}

            </div>
          )}
        </>
      )}

      {/* ── RAW FEED VIEW ─────────────────────────────────────────── */}
      {view === "feed" && (
        <div className="flex flex-col gap-3">
          {nLoading
            ? Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="card flex gap-4 p-4 animate-pulse">
                  <div className="w-20 h-14 bg-bg-hover rounded shrink-0" />
                  <div className="flex-1 flex flex-col gap-2 py-1">
                    <div className="h-2.5 bg-bg-hover rounded w-1/4" />
                    <div className="h-3.5 bg-bg-hover rounded w-full" />
                    <div className="h-3.5 bg-bg-hover rounded w-3/4" />
                  </div>
                </div>
              ))
            : (rawNews ?? []).map((item, i) => <RawNewsCard key={i} item={item} />)
          }
        </div>
      )}
    </div>
  );
}
