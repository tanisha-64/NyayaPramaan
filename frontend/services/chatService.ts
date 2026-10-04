
import { apiPost, apiGet, apiPatch, apiDelete } from "./apiClient";



export type Source = { name: string; type: string; url: string | null; verification_status: string; jurisdiction: string | null };



export type ChatResponse = {

  answer: string; conclusion?: string; usefulness?: string; verified: boolean;

  sources: Source[]; quality_note?: string; department_suggestion?: string | null;

  suggestions?: string[]; model_used?: string; session_id?: string;

};



export function askQuestion(query: string, caseId?: string, sessionId?: string, temporary?: boolean) {

  return apiPost<ChatResponse>("/chat/ask", { query, case_id: caseId ?? null, session_id: temporary ? null : sessionId ?? null });

}



export function createSession(title = "New Chat") { return apiPost<any>("/chat/sessions", { title }); }

export function listSessions() { return apiGet<any[]>("/chat/sessions"); }

export function getSessionMessages(sessionId: string) {

  return apiGet<{ messages: any[]; case_id: string | null; case_filename: string | null }>(`/chat/sessions/${sessionId}/messages`);

}

export function renameSession(sessionId: string, title: string) { return apiPatch(`/chat/sessions/${sessionId}`, { title }); }

export function togglePin(sessionId: string, pinned: boolean) { return apiPatch(`/chat/sessions/${sessionId}`, { pinned }); }

export function deleteSession(sessionId: string) { return apiDelete(`/chat/sessions/${sessionId}`); }

