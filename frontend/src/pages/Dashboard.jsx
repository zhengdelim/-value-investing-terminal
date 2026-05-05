import { useState, useCallback, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import Sidebar from "../components/Sidebar";
import StockTable from "../components/StockTable";
import ScoreCards from "../components/ScoreCards";
import MarketNews from "../components/MarketNews";
import IndexTicker from "../components/IndexTicker";
import SeedSP500Modal from "../components/SeedSP500Modal";
import { useStocks } from "../hooks/useStocks";
import { useWatchlist } from "../hooks/useWatchlist";
import { fetchSearch, fetchWatchlistStocks } from "../lib/api";

const DEFAULT_FILTERS = {
  pe_max: "", pb_max: "", pfcf_max: "", ev_ebitda_max: "",
  roe_min: "", roic_min: "", de_max: "", profit_margin_min: "",
  fcf_growth_min: "", revenue_growth_min: "", eps_growth_min: "",
  market_cap_min: "", market_cap_max: "", dividend_yield_min: "",
  insider_ownership_min: "", piotroski_min: "", altman_z_min: "",
  sector: "", limit: 50, offset: 0,
};

const TABS = [
  { id: "news",      label: "Market News",    icon: "📰" },
  { id: "screener",  label: "Stock Screener", icon: "⚙"  },
  { id: "watchlist", label: "Watchlist",      icon: "★"  },
];

export default function Dashboard() {
  const [activeTab, setActiveTab]       = useState("news");
  const [filters, setFilters]           = useState(DEFAULT_FILTERS);
  const [search, setSearch]             = useState("");
  const [showSuggestions, setShowSugg]  = useState(false);
  const [selectedIdx, setSelectedIdx]   = useState(-1);
  const [showSeedModal, setShowSeed]    = useState(false);
  const searchRef = useRef(null);
  const navigate  = useNavigate();

  const { isWatched, toggle: toggleWatch, tickers: watchedTickers,
          name: wlName, rename: renameWl, watchlistId } = useWatchlist();

  // Search suggestions
  const { data: suggestions = [], isFetching: suggestFetching } = useQuery({
    queryKey:  ["search", search],
    queryFn:   () => fetchSearch(search),
    enabled:   search.trim().length >= 1,
    staleTime: 1000 * 30,
    placeholderData: [],
  });

  // Watchlist stocks from backend
  const { data: wlStocks = [], isLoading: wlLoading } = useQuery({
    queryKey: ["watchlist-stocks", watchlistId, watchedTickers],
    queryFn:  () => fetchWatchlistStocks(watchlistId),
    enabled:  activeTab === "watchlist" && watchedTickers.length > 0,
    staleTime: 1000 * 60 * 5,
  });

  // Screener stocks
  const { data: stocks, isLoading } = useStocks(filters);
  const displayed = search
    ? (stocks ?? []).filter((s) =>
        s.ticker.toLowerCase().includes(search.toLowerCase()) ||
        s.name?.toLowerCase().includes(search.toLowerCase()))
    : stocks ?? [];

  const showSidebar = activeTab === "screener";

  // Close suggestions on outside click
  useEffect(() => {
    const h = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setShowSugg(false); setSelectedIdx(-1);
      }
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const handleChange = useCallback((field, value) =>
    setFilters((p) => ({ ...p, [field]: value })), []);

  const handleReset = useCallback(() => {
    setFilters(DEFAULT_FILTERS); setSearch("");
  }, []);

  const handleSearchKey = useCallback((e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault(); setSelectedIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault(); setSelectedIdx((i) => Math.max(i - 1, -1));
    } else if (e.key === "Escape") {
      setShowSugg(false); setSelectedIdx(-1);
    } else if (e.key === "Enter") {
      e.preventDefault();
      const pick = selectedIdx >= 0 ? suggestions[selectedIdx] : null;
      const ticker = pick ? pick.symbol : search.trim().toUpperCase();
      if (ticker) { setShowSugg(false); setSelectedIdx(-1); navigate(`/stock/${ticker}`); }
    }
  }, [search, suggestions, selectedIdx, navigate]);

  return (
    <div className="flex h-screen overflow-hidden">
      {showSeedModal && <SeedSP500Modal onClose={() => setShowSeed(false)} />}

      {showSidebar && (
        <Sidebar
          filters={filters}
          onChange={handleChange}
          onReset={handleReset}
          onPreset={setFilters}
        />
      )}

      <main className="flex-1 overflow-y-auto min-w-0">

        {/* ── Top bar ─────────────────────────────────────────── */}
        <div className="sticky top-0 z-10 bg-bg-primary border-b border-bg-border px-6 py-3 flex items-center gap-4">
          <span className="text-sm font-bold font-mono text-accent-blue tracking-wide whitespace-nowrap">
            ValueScreen
          </span>

          {/* Tabs */}
          <div className="flex gap-1">
            {TABS.map((t) => (
              <button key={t.id} onClick={() => setActiveTab(t.id)}
                className={clsx(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                  activeTab === t.id
                    ? "bg-accent-blue text-white"
                    : "text-muted hover:text-gray-200 hover:bg-bg-hover"
                )}>
                <span className="text-[11px]">{t.icon}</span>
                {t.label}
                {t.id === "watchlist" && watchedTickers.length > 0 && (
                  <span className="bg-yellow text-bg-primary font-mono font-bold text-[9px] px-1 rounded-full leading-tight">
                    {watchedTickers.length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Search — screener only */}
          {activeTab === "screener" && (
            <div className="flex-1 relative max-w-sm" ref={searchRef}>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted text-xs pointer-events-none">⌕</span>
                <input type="text" placeholder="Search ticker or company name…"
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setShowSugg(true); setSelectedIdx(-1); }}
                  onFocus={() => search.trim().length >= 1 && setShowSugg(true)}
                  onKeyDown={handleSearchKey}
                  className="w-full bg-bg-secondary border border-bg-border rounded-lg pl-7 pr-8 py-1.5 text-sm text-gray-200 placeholder-muted focus:outline-none focus:border-accent-blue transition-colors font-mono"
                />
                {search && (
                  <button onClick={() => { setSearch(""); setShowSugg(false); setSelectedIdx(-1); }}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-gray-300 text-base leading-none">×</button>
                )}
                {suggestFetching && (
                  <span className="absolute right-8 top-1/2 -translate-y-1/2 w-3 h-3 border border-accent-blue border-t-transparent rounded-full animate-spin" />
                )}
              </div>

              {showSuggestions && suggestions.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-bg-card border border-bg-border rounded-lg shadow-xl z-50 overflow-hidden">
                  {suggestions.map((s, i) => (
                    <button key={s.symbol}
                      onMouseDown={(e) => { e.preventDefault(); setShowSugg(false); navigate(`/stock/${s.symbol}`); }}
                      onMouseEnter={() => setSelectedIdx(i)}
                      className={clsx(
                        "w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors border-b border-bg-border last:border-0",
                        i === selectedIdx ? "bg-accent-blue/10" : "hover:bg-bg-hover"
                      )}>
                      <div className="flex items-center gap-1.5 shrink-0 w-24">
                        <span className="font-mono font-semibold text-sm text-accent-blue">{s.symbol}</span>
                        {s.in_db && <span className="text-[9px] text-green bg-green-bg border border-green/20 px-1 rounded">DB</span>}
                      </div>
                      <span className="flex-1 text-xs text-gray-300 truncate">{s.name}</span>
                      <span className="text-[10px] text-subtle font-mono shrink-0">{s.exchange}</span>
                    </button>
                  ))}
                  <div className="px-3 py-1.5 bg-bg-secondary border-t border-bg-border">
                    <span className="text-[10px] text-subtle">↑↓ navigate · Enter to open · Esc to close</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Right-side controls */}
          <div className="ml-auto flex items-center gap-2 shrink-0">
            {activeTab === "screener" && (
              <>
                <span className="text-xs text-muted font-mono">{displayed.length} results</span>
                <button onClick={() => setShowSeed(true)}
                  className="text-xs px-3 py-1.5 rounded border border-accent-blue/30 text-accent-blue hover:bg-accent-blue/10 transition-colors whitespace-nowrap">
                  + S&P 500
                </button>
              </>
            )}
          </div>
        </div>

        {/* ── Index ticker ──────────────────────────────────────── */}
        <IndexTicker />

        {/* ── Tab content ──────────────────────────────────────── */}

        {activeTab === "news" && <MarketNews />}

        {activeTab === "screener" && (
          <div className="p-6">
            <ScoreCards stocks={displayed} />
            <div className="card overflow-hidden">
              <StockTable stocks={displayed} isLoading={isLoading}
                isWatched={isWatched} onToggleWatch={toggleWatch} />
            </div>
            {stocks?.length === filters.limit && (
              <div className="mt-4 flex justify-center">
                <button onClick={() => setFilters((p) => ({ ...p, limit: p.limit + 50 }))}
                  className="px-4 py-2 text-sm text-accent-blue border border-accent-blue/30 rounded-lg hover:bg-accent-blue/10 transition-colors">
                  Load more
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === "watchlist" && (
          <div className="p-6">
            {/* Watchlist header */}
            <div className="flex items-center gap-3 mb-5">
              <div className="flex-1">
                <WatchlistNameEditor name={wlName} onRename={renameWl} />
                <p className="text-xs text-muted mt-0.5">
                  {watchedTickers.length === 0
                    ? "Star stocks in the Screener tab to add them here."
                    : `${watchedTickers.length} stock${watchedTickers.length !== 1 ? "s" : ""} · click any row to view details`}
                </p>
              </div>
              {watchedTickers.length > 0 && (
                <div className="flex gap-1 text-[10px] font-mono text-muted">
                  {watchedTickers.slice(0, 8).map((t) => (
                    <span key={t} className="bg-bg-hover border border-bg-border rounded px-1.5 py-0.5">{t}</span>
                  ))}
                  {watchedTickers.length > 8 && <span className="text-subtle">+{watchedTickers.length - 8}</span>}
                </div>
              )}
            </div>

            {watchedTickers.length === 0 ? (
              <div className="card flex flex-col items-center justify-center h-64 gap-3 text-center">
                <span className="text-4xl">★</span>
                <p className="text-sm text-gray-300 font-medium">Your watchlist is empty</p>
                <p className="text-xs text-muted max-w-xs">
                  Go to the <button onClick={() => setActiveTab("screener")}
                    className="text-accent-blue hover:underline">Stock Screener</button> tab and click the ☆ star next to any stock to add it here.
                </p>
              </div>
            ) : (
              <>
                {wlStocks.length > 0 && <ScoreCards stocks={wlStocks} />}
                <div className="card overflow-hidden">
                  <StockTable stocks={wlStocks} isLoading={wlLoading}
                    isWatched={isWatched} onToggleWatch={toggleWatch} />
                </div>
              </>
            )}
          </div>
        )}

      </main>
    </div>
  );
}

// Inline editable watchlist name
function WatchlistNameEditor({ name, onRename }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal]         = useState(name);
  useEffect(() => setVal(name), [name]);

  if (editing) {
    return (
      <div className="flex items-center gap-2">
        <input autoFocus value={val} onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") { onRename(val.trim() || name); setEditing(false); }
            if (e.key === "Escape") { setVal(name); setEditing(false); }
          }}
          className="bg-bg-secondary border border-accent-blue rounded px-2 py-0.5 text-sm font-semibold text-gray-200 focus:outline-none w-48"
        />
        <button onClick={() => { onRename(val.trim() || name); setEditing(false); }}
          className="text-xs text-green">✓</button>
        <button onClick={() => { setVal(name); setEditing(false); }}
          className="text-xs text-muted">✕</button>
      </div>
    );
  }
  return (
    <button onClick={() => setEditing(true)}
      className="text-base font-semibold text-gray-200 hover:text-accent-blue transition-colors flex items-center gap-1.5 group">
      {name}
      <span className="text-xs text-subtle group-hover:text-accent-blue opacity-0 group-hover:opacity-100 transition-opacity">✎</span>
    </button>
  );
}
