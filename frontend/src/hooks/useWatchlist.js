import { useState, useEffect, useCallback } from "react";
import { createWatchlist, addToWatchlist, removeFromWatchlist, updateWatchlist } from "../lib/api";

const LS_KEY = "valuescreen_watchlist_id";
const LS_NAME = "valuescreen_watchlist_name";

function getOrCreateId() {
  let id = localStorage.getItem(LS_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(LS_KEY, id);
  }
  return id;
}

export function useWatchlist() {
  const [watchlistId]   = useState(getOrCreateId);
  const [name, setName] = useState(() => localStorage.getItem(LS_NAME) || "My Watchlist");
  const [tickers, setTickers] = useState(() => {
    try { return JSON.parse(localStorage.getItem("valuescreen_wl_tickers") || "[]"); }
    catch { return []; }
  });

  // Sync tickers to localStorage
  useEffect(() => {
    localStorage.setItem("valuescreen_wl_tickers", JSON.stringify(tickers));
  }, [tickers]);

  // Ensure watchlist exists on backend on first mount
  useEffect(() => {
    createWatchlist({ id: watchlistId, name, tickers }).catch(() => {});
  }, [watchlistId]); // eslint-disable-line

  const isWatched = useCallback((ticker) => tickers.includes(ticker), [tickers]);

  const toggle = useCallback(async (ticker) => {
    const t = ticker.toUpperCase();
    if (tickers.includes(t)) {
      setTickers((prev) => prev.filter((x) => x !== t));
      await removeFromWatchlist(watchlistId, [t]).catch(() => {});
    } else {
      setTickers((prev) => [...prev, t]);
      await addToWatchlist(watchlistId, [t]).catch(() => {});
    }
  }, [tickers, watchlistId]);

  const rename = useCallback(async (newName) => {
    setName(newName);
    localStorage.setItem(LS_NAME, newName);
    await updateWatchlist(watchlistId, { name: newName }).catch(() => {});
  }, [watchlistId]);

  return { watchlistId, name, tickers, isWatched, toggle, rename };
}
