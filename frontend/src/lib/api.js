import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 30000,
});

export const fetchScreener = (params) =>
  api.get("/stocks", { params }).then((r) => r.data);

export const fetchStock = (ticker, force = false) =>
  api.get(`/stocks/${ticker}`, { params: force ? { force: true } : undefined }).then((r) => r.data);

export const fetchFinancials = (ticker, period = "annual") =>
  api.get(`/stocks/${ticker}/financials`, { params: { period } }).then((r) => r.data);

export const fetchDCF = (ticker, params) =>
  api.get(`/stocks/${ticker}/dcf`, { params }).then((r) => r.data);

export const fetchInsiders = (ticker) =>
  api.get(`/stocks/${ticker}/insiders`).then((r) => r.data);

export const fetchAnalysis = (ticker) =>
  api.get(`/stocks/${ticker}/analysis`).then((r) => r.data);

export const fetchMultiplesHistory = (ticker) =>
  api.get(`/stocks/${ticker}/multiples-history`).then((r) => r.data);

export const fetchSegments = (ticker) =>
  api.get(`/stocks/${ticker}/segments`).then((r) => r.data);

export const fetchIndices = () =>
  api.get("/indices").then((r) => r.data);

export const fetchSearch = (q) =>
  api.get("/stocks/search", { params: { q } }).then((r) => r.data);

// Watchlist
export const createWatchlist    = (body)        => api.post("/watchlist", body).then((r) => r.data);
export const getWatchlist       = (wid)         => api.get(`/watchlist/${wid}`).then((r) => r.data);
export const addToWatchlist     = (wid, tickers) => api.post(`/watchlist/${wid}/add`, { tickers }).then((r) => r.data);
export const removeFromWatchlist= (wid, tickers) => api.post(`/watchlist/${wid}/remove`, { tickers }).then((r) => r.data);
export const updateWatchlist    = (wid, body)   => api.put(`/watchlist/${wid}`, body).then((r) => r.data);
export const fetchWatchlistStocks = (wid)       => api.get(`/watchlist/${wid}/stocks`).then((r) => r.data);

// S&P 500 deep seed (full metrics per stock)
export const fetchSp500Tickers    = ()          => api.get("/sp500/tickers").then((r) => r.data);
export const startSp500Seed       = ()          => api.post("/sp500/seed").then((r) => r.data);
export const fetchSeedProgress    = ()          => api.get("/sp500/progress").then((r) => r.data);

// All US stocks bulk seed (basic data via screener — fast)
export const startUsStocksSeed    = ()          => api.post("/us-stocks/seed").then((r) => r.data);
export const fetchUsStocksProgress = ()         => api.get("/us-stocks/progress").then((r) => r.data);

// Rescore all stocks from existing DB data (no FMP quota used)
export const rescoreAllStocks   = ()            => api.post("/stocks/rescore").then((r) => r.data);

export default api;
