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

export type AdminActivity = {
  total_registered_users: number | null;
  active_users_today: number | null;
};

export type HealthCheck = {
  name: string;
  ok: boolean;
  status: string;
};

export type AdminHealth = {
  checks: HealthCheck[];
};

export function getAdminMetrics() {
  return apiGet<AdminMetrics>("/admin/metrics");
}

export function getJudgmentsCount() {
  return apiGet<JudgmentsCountResponse>("/admin/judgments-count");
}

export function getAdminActivity() {
  return apiGet<AdminActivity>("/admin/activity");
}

export function getAdminHealth() {
  return apiGet<AdminHealth>("/admin/health");
}