import { apiPost, apiGet, apiPatch, apiDelete } from "./apiClient";

export type LegalClaim = {
  claim: string;
  status: 'SUPPORTED' | 'PARTIALLY SUPPORTED' | 'CONTRADICTED' | 'INSUFFICIENT EVIDENCE';
  evidence?: string;
  source?: string;
};

export type VerificationSummary = {
  claims_analyzed: number;
  supported: number;
  partially_supported: number;
  insufficient_evidence: number;
  contradicted: number;
  evidence_coverage: number; // 0-100%
};

export type Source = {
  name: string;
  type: string;
  url: string | null;
  verification_status: string;
  jurisdiction: string | null;
  page?: number;
  section?: string;
  excerpt?: string;
};

export type LegalSource = Source;

export type ChatResponse = {
  answer: string;
  conclusion?: string;
  usefulness?: string;
  verified: boolean;
  sources: Source[];
  claims?: LegalClaim[];
  verification_summary?: VerificationSummary;
  quality_note?: string;
  department_suggestion?: string | null;
  suggestions?: string[];
  model_used?: string;
  session_id?: string;
};

export function askQuestion(
  query: string,
  caseIdOrIds?: string | string[],
  sessionId?: string,
  temporary?: boolean,
  mode?: string
) {
  const caseId = Array.isArray(caseIdOrIds) ? caseIdOrIds[0] : caseIdOrIds;
  return apiPost<ChatResponse>("/chat/ask", {
    query,
    case_id: caseId ?? null,
    session_id: temporary ? null : sessionId ?? null,
  });
}

export function createSession(title = "New Chat") { return apiPost<any>("/chat/sessions", { title }); }
export function listSessions() { return apiGet<any[]>("/chat/sessions"); }
export function getSessionMessages(sessionId: string) {
  return apiGet<{ messages: any[]; case_id: string | null; case_filename: string | null; documents?: { case_id: string; filename: string }[] }>(`/chat/sessions/${sessionId}/messages`);
}
export function renameSession(sessionId: string, title: string) { return apiPatch(`/chat/sessions/${sessionId}`, { title }); }
export function togglePin(sessionId: string, pinned: boolean) { return apiPatch(`/chat/sessions/${sessionId}`, { pinned }); }
export function deleteSession(sessionId: string) { return apiDelete(`/chat/sessions/${sessionId}`); }
export function clearAllSessions() {
  return apiDelete<{ status: string; cleared_sessions: number }>("/chat/sessions/clear/all");
}
