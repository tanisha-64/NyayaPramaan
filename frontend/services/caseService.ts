import { apiGet, apiPut, apiDelete } from "./apiClient";

export type CaseSummary = {
  id: string;
  summary: string;
  filename?: string;
  status?: string;
  created_at: string;
  notes?: string;
};

export type CaseDetail = CaseSummary & {
  case_text: string;
  timeline: string;
};

export type CaseBriefResponse = {
  case_id: string;
  filename: string;
  brief_markdown: string;
  timeline?: string;
};

export function listCases() {
  return apiGet<CaseSummary[]>("/case/list");
}

export function getCase(caseId: string) {
  return apiGet<CaseDetail>(`/case/${caseId}`);
}

export function saveCaseNotes(caseId: string, notes: string) {
  return apiPut<{ status: string; notes: string }>(`/case/${caseId}/notes`, { notes });
}

export function getCaseBrief(caseId: string) {
  return apiGet<CaseBriefResponse>(`/case/${caseId}/brief`);
}

export function deleteCase(caseId: string) {
  return apiDelete(`/case/${caseId}`);
}

export function clearAllCases() {
  return apiDelete<{ status: string; cleared_count: number }>("/case/clear/all");
}