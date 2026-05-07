import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchStock, fetchFinancials, fetchDCF, fetchInsiders, fetchMultiplesHistory, fetchSegments, fetchResearch, fetchValuationReview } from "../lib/api";

export function useStockDetail(ticker) {
  return useQuery({
    queryKey: ["stock", ticker],
    queryFn: () => fetchStock(ticker),
    enabled: !!ticker,
    staleTime: 1000 * 60 * 60 * 24,
  });
}

export function useRefreshStock(ticker) {
  const qc = useQueryClient();
  return async () => {
    await fetchStock(ticker, true);
    await qc.invalidateQueries({ queryKey: ["stock", ticker] });
    await qc.invalidateQueries({ queryKey: ["financials", ticker] });
    await qc.invalidateQueries({ queryKey: ["analysis", ticker] });
    await qc.invalidateQueries({ queryKey: ["dcf", ticker] });
  };
}

export function useFinancials(ticker, period = "annual") {
  return useQuery({
    queryKey: ["financials", ticker, period],
    queryFn: () => fetchFinancials(ticker, period),
    enabled: !!ticker,
  });
}

export function useDCF(ticker, params) {
  return useQuery({
    queryKey: ["dcf", ticker, params],
    queryFn: () => fetchDCF(ticker, params),
    enabled: !!ticker,
  });
}

export function useInsiders(ticker) {
  return useQuery({
    queryKey: ["insiders", ticker],
    queryFn: () => fetchInsiders(ticker),
    enabled: !!ticker,
  });
}

export function useMultiplesHistory(ticker) {
  return useQuery({
    queryKey: ["multiples-history", ticker],
    queryFn: () => fetchMultiplesHistory(ticker),
    enabled: !!ticker,
    staleTime: 1000 * 60 * 60 * 24,
  });
}

export function useSegments(ticker) {
  return useQuery({
    queryKey: ["segments", ticker],
    queryFn: () => fetchSegments(ticker),
    enabled: !!ticker,
    staleTime: 1000 * 60 * 60 * 24,
  });
}

export function useResearch(ticker) {
  return useQuery({
    queryKey: ["research", ticker],
    queryFn: () => fetchResearch(ticker),
    enabled: !!ticker,
    staleTime: 1000 * 60 * 60 * 24,
  });
}

export function useValuationReview(ticker) {
  return useQuery({
    queryKey: ["valuation-review", ticker],
    queryFn: () => fetchValuationReview(ticker),
    enabled: !!ticker,
    staleTime: 1000 * 60 * 60 * 24,
  });
}
