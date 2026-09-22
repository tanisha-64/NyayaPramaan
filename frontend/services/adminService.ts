import { apiGet } from "./apiClient";

export type AdminMetrics = {
  total_queries: number;
  verified_count: number;
  citation_accuracy_rate: number | null;
  model_usage_breakdown: Record<string, number>;
};

export type JudgmentsCountResponse = {
  total_judgments: number;
};

export function getAdminMetrics() {
  return apiGet<AdminMetrics>("/admin/metrics");
}

export function getJudgmentsCount() {
  return apiGet<JudgmentsCountResponse>("/admin/judgments-count");
}
