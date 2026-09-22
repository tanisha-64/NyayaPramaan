import { apiUpload, apiGet, apiDelete } from "./apiClient";

export type UploadResponse = {
  case_id: string;
  file_url: string;
  filename: string;
  status: string;
  document_type: string;
};

export type CaseStatus = {
  status: string;
  summary: string;
  timeline: string;
};

export function uploadDocument(file: File, signal?: AbortSignal) {
  return apiUpload<UploadResponse>("/document/upload", file, signal);
}

export function getCaseStatus(caseId: string) {
  return apiGet<CaseStatus>(`/document/${caseId}/status`);
}

export function deleteDocument(caseId: string) {
  return apiDelete(`/document/${caseId}`);
}