import { apiPost, apiGet, apiPatch, apiDelete } from "./apiClient";

export type ChatResponse = {
  answer: string;
  conclusion?: string;
  usefulness?: string;
  verified: boolean;
  sources: { name: string; type: string; url: string | null; verification_status: string; jurisdiction: string | null }[];
  quality_note?: string;
  department_suggestion?: string | null;
  suggestions?: string[];
  model_used?: string;
  session_id?: string;
};

export function askQuestion(query: string, caseIds: string[] = [], sessionId?: string, temporary?: boolean) {
  return apiPost<ChatResponse>("/chat/ask", {
    query,
    case_ids: caseIds,
    session_id: temporary ? null : sessionId ?? null,
  });
}

export function createSession(title = "New Chat") {
  return apiPost<any>("/chat/sessions", { title });
}

export function listSessions() {
  return apiGet<any[]>("/chat/sessions");
}

export function getSessionMessages(sessionId: string) {
  return apiGet<{ messages: any[]; documents: { case_id: string; filename: string }[] }>(`/chat/sessions/${sessionId}/messages`);
}

export function renameSession(sessionId: string, title: string) {
  return apiPatch(`/chat/sessions/${sessionId}`, { title });
}

export function togglePin(sessionId: string, pinned: boolean) {
  return apiPatch(`/chat/sessions/${sessionId}`, { pinned });
}

export function deleteSession(sessionId: string) {
  return apiDelete(`/chat/sessions/${sessionId}`);
}

export function clearAllSessions() {
  return apiDelete<{ status: string; cleared_sessions: number }>("/chat/sessions/clear/all");
}