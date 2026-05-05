import { useQuery } from "@tanstack/react-query";
import { fetchScreener } from "../lib/api";

export function useStocks(filters) {
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v !== "" && v !== null && v !== undefined)
  );
  return useQuery({
    queryKey: ["stocks", params],
    queryFn: () => fetchScreener(params),
    keepPreviousData: true,
  });
}
