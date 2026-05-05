import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { startSp500Seed, fetchSeedProgress } from "../lib/api";

export default function SeedSP500Modal({ onClose }) {
  const qc = useQueryClient();
  const [started, setStarted] = useState(false);

  const { data: progress } = useQuery({
    queryKey: ["sp500-progress"],
    queryFn: fetchSeedProgress,
    refetchInterval: started ? 2000 : false,
    staleTime: 0,
  });

  const { mutate: seed, isPending } = useMutation({
    mutationFn: startSp500Seed,
    onSuccess: () => {
      setStarted(true);
      qc.invalidateQueries({ queryKey: ["sp500-progress"] });
    },
  });

  const running  = progress?.running ?? false;
  const done     = progress?.done    ?? 0;
  const total    = progress?.total   ?? 503;
  const pct      = progress?.pct     ?? 0;
  const failed   = progress?.failed  ?? [];
  const finished = !running && done > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-bg-card border border-bg-border rounded-xl shadow-2xl w-full max-w-md mx-4">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-bg-border">
          <div>
            <h2 className="font-semibold text-gray-200 text-sm">Expand to S&P 500</h2>
            <p className="text-xs text-muted mt-0.5">Fetches all 503 constituents via yfinance</p>
          </div>
          <button onClick={onClose} className="text-muted hover:text-gray-300 text-xl leading-none">×</button>
        </div>

        <div className="p-5 flex flex-col gap-4">
          {/* Info box */}
          {!started && !running && (
            <div className="bg-bg-hover border border-bg-border rounded-lg p-4 text-xs text-muted space-y-1.5">
              <p><span className="text-gray-300 font-semibold">503 stocks</span> will be fetched from yfinance (no FMP quota used).</p>
              <p>Runs in the background in batches of 5 — takes about <span className="text-gray-300">3–5 minutes</span>.</p>
              <p>You can close this modal; seeding continues. Come back to check progress.</p>
            </div>
          )}

          {/* Progress bar */}
          {(started || running || finished) && (
            <div className="flex flex-col gap-2">
              <div className="flex justify-between text-xs">
                <span className={clsx("font-semibold", running ? "text-accent-blue" : finished ? "text-green" : "text-muted")}>
                  {running ? "Seeding…" : finished ? "Complete" : "Idle"}
                </span>
                <span className="font-mono text-muted">{done} / {total}</span>
              </div>
              <div className="w-full h-2.5 bg-bg-hover rounded-full overflow-hidden">
                <div
                  className={clsx("h-full rounded-full transition-all duration-500",
                    finished ? "bg-green" : "bg-accent-blue")}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-muted font-mono">
                <span>{pct.toFixed(1)}% done</span>
                {failed.length > 0 && (
                  <span className="text-red">{failed.length} failed</span>
                )}
              </div>
            </div>
          )}

          {/* Already running notice */}
          {running && !isPending && (
            <p className="text-xs text-accent-blue bg-accent-blue/10 border border-accent-blue/20 rounded-lg px-3 py-2">
              Seed is running. You can safely close this modal — it continues in the background.
            </p>
          )}

          {/* Done summary */}
          {finished && (
            <div className="bg-green-bg border border-green/20 rounded-lg px-4 py-3 text-xs text-green">
              ✓ {progress.success?.length ?? done} stocks loaded successfully.
              {failed.length > 0 && (
                <span className="text-red ml-2">{failed.length} failed: {failed.slice(0, 6).join(", ")}</span>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-2 px-5 pb-5 justify-end">
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
            <button onClick={() => { qc.invalidateQueries({ queryKey: ["sp500-progress"] }); }}
              className="px-4 py-2 text-xs border border-accent-blue/40 text-accent-blue rounded-lg hover:bg-accent-blue/10 transition-colors">
              ↻ Refresh
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
