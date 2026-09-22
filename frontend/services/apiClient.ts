import { supabase } from "@/lib/supabaseClient";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

async function authHeaders(): Promise<Record<string, string>> {
  const { data, error } = await supabase.auth.getSession();
  if (error) console.error("[apiClient] getSession error:", error);
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleUnauthorized(path: string) {
  // Only redirect if the path is explicitly a protected user-data endpoint
  const isPublicRoute = path.startsWith("/game") || path.startsWith("/quiz") || path.startsWith("/news") || path.startsWith("/health");
  if (!isPublicRoute) {
    await supabase.auth.signOut();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  }
}

async function request<T>(path: string, options: RequestInit = {}, isUpload = false): Promise<T> {
  const authH = await authHeaders();
  const headers = isUpload ? authH : { "Content-Type": "application/json", ...authH };

  let res: Response | null = null;
  const targetUrls = [API_BASE_URL];
  if (API_BASE_URL.includes("127.0.0.1")) {
    targetUrls.push(API_BASE_URL.replace("127.0.0.1", "localhost"));
  } else if (API_BASE_URL.includes("localhost")) {
    targetUrls.push(API_BASE_URL.replace("localhost", "127.0.0.1"));
  }

  let lastNetworkError: any = null;
  for (const base of targetUrls) {
    try {
      res = await fetch(`${base}${path}`, { ...options, headers: { ...headers, ...(options.headers || {}) } });
      if (res) break;
    } catch (networkErr) {
      lastNetworkError = networkErr;
    }
  }

  if (!res) {
    throw new Error(
      lastNetworkError?.name === "AbortError"
        ? "Request aborted"
        : "Cannot reach the server. Please check that the backend is running."
    );
  }

  if (res.status === 401) {
    await handleUnauthorized(path);
    throw new Error("Unauthorized access or session expired.");
  }
  if (!res.ok) {
    let errorDetail = `API error: ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson && (errJson.detail || errJson.message || errJson.error)) {
        errorDetail = errJson.detail || errJson.message || errJson.error;
      }
    } catch {
      // not JSON
    }
    throw new Error(errorDetail);
  }
  return res.json();
}


export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

export function apiPost<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(body) });
}

export function apiPut<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "PUT", body: JSON.stringify(body) });
}

export function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "PATCH", body: JSON.stringify(body) });
}

export function apiDelete<T>(path: string): Promise<T> {
  return request<T>(path, { method: "DELETE" });
}

export async function apiUpload<T>(path: string, file: File, signal?: AbortSignal): Promise<T> {
  const formData = new FormData();
  formData.append("file", file);
  return request<T>(path, { method: "POST", body: formData, signal }, true);
}