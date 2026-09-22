import { apiPost } from "./apiClient";

export type PrecedentResult = {
  display_name?: string;
  case_name?: string;
  court?: string;
  year?: number;
  jurisdiction_type?: string;
  full_text: string;
  combined_score?: number;
};

export type SearchFilters = {
  query: string;
  match_count?: number;
  court?: string;
  year_from?: number;
  year_to?: number;
  jurisdiction_type?: string;
};

export function searchPrecedents(filters: string | SearchFilters) {
  const payload = typeof filters === "string" ? { query: filters } : filters;
  return apiPost<{ results: PrecedentResult[] }>("/search/precedents", payload);
}