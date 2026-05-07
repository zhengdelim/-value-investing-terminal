import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import {
  startSp500Seed, fetchSeedProgress,
  startUsStocksSeed, fetchUsStocksProgress,
} from "../lib/api";

const MODES = {
  sp500: {
    label: "S&P 500",
    badge: "~503 stocks",
    badgeColor: "text-accent-blue border-accent-blue/30 bg-accent-blue/10",
    description: "Deep-seeds all S&P 500 constituents with full metrics — ROE, ROIC, EPS, growth, GuruScore. Takes 15–20 min.",
    warning: null,
    startFn: startSp500Seed,
    progressFn: fetchSeedProgress,
    progressKey: "sp500-progress",
    defaultTotal: 503,
  },
  us: {
    label: "All US Stocks",
    badge: "~7,500+ stocks",
    badgeColor: "text-yellow border-yellow/30 bg-yellow/10",
    description: "Seeds all NYSE + Nasdaq stocks from SEC EDGAR (free, no API quota). Adds ticker + name + exchange as stubs. Quality metrics load on first click. Takes ~5 sec.",
    warning: "Stub seed only — quality filters (ROE, ROIC, etc.) show '—' until a stock is individually refreshed.",
    startFn: startUsStocksSeed,
    progressFn: fetchUsStocksProgress,
    progressKey: "us-stocks-progress",
    defaultTotal: 8000,
  },
};

function SeedPanel({ mode, onClose }) {
  const cfg = MODES[mode];
  const qc = useQueryClient();
  const [started, setStarted] = useState(false);

  const { data: progress } = useQuery({
    queryKey: [cfg.progressKey],
    queryFn: cfg.progressFn,
    refetchInterval: started ? 2000 : false,
    staleTime: 0,
  });

  const { mutate: seed, isPending } = useMutation({
    mutationFn: cfg.startFn,
    onSuccess: () => {
      setStarted(true);
      qc.invalidateQueries({ queryKey: [cfg.progressKey] });
    },
  });

  const running  = progress?.running ?? false;
  const done     = progress?.done    ?? 0;
  const total    = progress?.total   ?? cfg.defaultTotal;
  const pct      = progress?.pct     ?? 0;
  const finished = !running && done > 0;

  return (
    <div className="flex flex-col gap-4">
      {/* Info box */}
      {!started && !running && (
        <div className="bg-bg-hover border border-bg-border rounded-lg p-4 text-xs text-muted space-y-2">
          <p><span className="text-gray-300 font-semibold">{cfg.badge}</span> — {cfg.description}</p>
          {cfg.warning && (
            <p className="text-yellow/80 border-t border-bg-border pt-2">{cfg.warning}</p>
          )}
          {mode === "us" && (
            <p className="text-muted">After seeding, click any stock to trigger a full data refresh for quality metrics.</p>
          )}
        </div>
      )}

      {/* Progress */}
      {(started || running || finished) && (
        <div className="flex flex-col gap-2">
          <div className="flex justify-between text-xs">
            <span className={clsx("font-semibold", running ? "text-accent-blue" : finished ? "text-green" : "text-muted")}>
              {running ? "Seeding…" : finished ? "Complete" : "Idle"}
            </span>
            <span className="font-mono text-muted">{done.toLocaleString()} / {total.toLocaleString()}</span>
          </div>
          <div className="w-full h-2.5 bg-bg-hover rounded-full overflow-hidden">
            <div
              className={clsx("h-full rounded-full transition-all duration-500", finished ? "bg-green" : "bg-accent-blue")}
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-muted font-mono">
            <span>{pct.toFixed(1)}% done</span>
            {mode === "us" && progress?.added != null && (
              <span className="text-green">+{progress.added.toLocaleString()} new</span>
            )}
          </div>
        </div>
      )}

      {running && !isPending && (
        <p className="text-xs text-accent-blue bg-accent-blue/10 border border-accent-blue/20 rounded-lg px-3 py-2">
          Seed is running. You can safely close this modal — it continues in the background.
        </p>
      )}

      {finished && (
        <div className="bg-green-bg border border-green/20 rounded-lg px-4 py-3 text-xs text-green">
          ✓ {mode === "us"
            ? `${progress?.added?.toLocaleString() ?? done} new stocks added.`
            : `${progress?.success?.length ?? done} stocks loaded.`}
          {mode === "us" && progress?.skipped > 0 && (
            <span className="text-muted ml-2">{progress.skipped.toLocaleString()} already in DB.</span>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 justify-end">
        <button onClick={onClose}
          className="px-4 py-2 text-xs text-muted border border-bg-border rounded-lg hover:bg-bg-hover transition-colors">
          {finished ? "Close" : "Close (runs in background)"}
        </button>
        {!running && !finished && (
          <button
            onClick={() => seed()}
            disabled={isPending}
            className="px-4 py-2 text-xs bg-accent-blue text-white rounded-lg hover:bg-accent-blue/80 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {isPending && <span className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />}
            Start Seeding
          </button>
        )}
        {(running || finished) && (
          <button
            onClick={() => qc.invalidateQueries({ queryKey: [cfg.progressKey] })}
            className="px-4 py-2 text-xs border border-accent-blue/40 text-accent-blue rounded-lg hover:bg-accent-blue/10 transition-colors"
          >
            ↻ Refresh
          </button>
        )}
      </div>
    </div>
  );
}

export default function SeedSP500Modal({ onClose }) {
  const [mode, setMode] = useState("us");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-bg-card border border-bg-border rounded-xl shadow-2xl w-full max-w-md mx-4">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-bg-border">
          <div>
            <h2 className="font-semibold text-gray-200 text-sm">Seed Stock Database</h2>
            <p className="text-xs text-muted mt-0.5">Populate your screener with stock data</p>
          </div>
          <button onClick={onClose} className="text-muted hover:text-gray-300 text-xl leading-none">×</button>
        </div>

        <div className="p-5 flex flex-col gap-4">
          {/* Mode toggle */}
          <div className="flex gap-2">
            {Object.entries(MODES).map(([key, cfg]) => (
              <button
                key={key}
                onClick={() => setMode(key)}
                className={clsx(
                  "flex-1 flex flex-col items-start px-3 py-2.5 rounded-lg border text-xs transition-colors",
                  mode === key
                    ? "border-accent-blue/50 bg-accent-blue/10"
                    : "border-bg-border hover:bg-bg-hover"
                )}
              >
                <span className={clsx(
                  "text-[10px] font-semibold px-1.5 py-0.5 rounded border mb-1",
                  cfg.badgeColor
                )}>{cfg.badge}</span>
                <span className={clsx("font-semibold", mode === key ? "text-accent-blue" : "text-gray-300")}>
                  {cfg.label}
                </span>
              </button>
            ))}
          </div>

          {/* Panel for selected mode */}
          <SeedPanel key={mode} mode={mode} onClose={onClose} />
        </div>
      </div>
    </div>
  );
}
