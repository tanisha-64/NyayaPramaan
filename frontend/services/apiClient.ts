import { supabase } from "@/lib/supabaseClient";

export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

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
  const authH = await authHeaders();
  const headers = isUpload ? authH : { "Content-Type": "application/json", ...authH };

  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${cleanPath}`, { ...options, headers: { ...headers, ...(options.headers || {}) } });
  } catch {
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
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
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
