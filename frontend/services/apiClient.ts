import { supabase } from "@/lib/supabaseClient";

const configuredApiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL;
export const API_BASE_URL = (
  configuredApiUrl || (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "")
).replace(/\/+$/, "");

async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleUnauthorized() {
  await supabase.auth.signOut();
  if (typeof window !== "undefined") window.location.href = "/login";
}

async function request<T>(path: string, options: RequestInit = {}, isUpload = false): Promise<T> {
  if (!API_BASE_URL) {
    throw new Error("Backend URL is not configured. Set NEXT_PUBLIC_API_BASE_URL in the deployment environment and redeploy.");
  }

  const authH = await authHeaders();
  const headers = isUpload ? authH : { "Content-Type": "application/json", ...authH };

  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const requestUrl = `${API_BASE_URL}${cleanPath}`;
  let res: Response;
  try {
    res = await fetch(requestUrl, { ...options, headers: { ...headers, ...(options.headers || {}) } });
  } catch (error) {
    console.error("[apiClient] Network request failed", {
      url: requestUrl,
      error: error instanceof Error ? error.name : "UnknownError",
    });
    throw new Error("Cannot reach the server. Please check your connection and try again.");
  }

  if (res.status === 401) {
    await handleUnauthorized();
    throw new Error("Session expired. Redirecting to login...");
  }
  if (res.status === 422) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "This document could not be processed.");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const reference = typeof body.request_id === "string" ? ` Reference: ${body.request_id}.` : "";
    throw new Error(`API error: ${res.status}.${reference}`);
  }
  const body = await res.json();
  if (body && typeof body === "object" && body.error === true) {
    const reference = typeof body.request_id === "string" ? ` Reference: ${body.request_id}.` : "";
    throw new Error(`The server could not complete the request.${reference}`);
  }
  return body;
}

export function apiGet<T>(path: string): Promise<T> { return request<T>(path, { method: "GET" }); }
export function apiPost<T>(path: string, body: unknown): Promise<T> { return request<T>(path, { method: "POST", body: JSON.stringify(body) }); }
export function apiPut<T>(path: string, body: unknown): Promise<T> { return request<T>(path, { method: "PUT", body: JSON.stringify(body) }); }
export function apiPatch<T>(path: string, body: unknown): Promise<T> { return request<T>(path, { method: "PATCH", body: JSON.stringify(body) }); }
export function apiDelete<T>(path: string): Promise<T> { return request<T>(path, { method: "DELETE" }); }
export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append("file", file);
  return request<T>(path, { method: "POST", body: formData }, true);
}
