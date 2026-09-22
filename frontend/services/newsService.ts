import { API_BASE_URL } from "./apiClient";

export type NewsArticle = { title: string; summary: string; image: string; url: string; source: string; date: string };

export async function getLegalNews(): Promise<{ articles: NewsArticle[] }> {
  try {
    const res = await fetch(`${API_BASE_URL}/news/legal`);
    if (!res.ok) return { articles: [] };
    return await res.json();
  } catch (e) {
    console.error("[newsService] getLegalNews failed:", e);
    return { articles: [] };
  }
}