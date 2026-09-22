import { API_BASE_URL } from "./apiClient";

export type QuizQuestion = {
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
  judge_verified: boolean;
  caution_note: string;
};

export async function getTodaysQuiz(): Promise<QuizQuestion[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/quiz/today`);
    if (!res.ok) return [];
    return await res.json();
  } catch (e) {
    console.error("[quizService] getTodaysQuiz failed:", e);
    return [];
  }
}