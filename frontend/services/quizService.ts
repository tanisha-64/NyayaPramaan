import { API_BASE_URL } from "./apiClient";

export type QuizQuestion = {
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
  judge_verified: boolean;
  caution_note: string;
};

export type UserQuizStats = {
  quizzes_taken: number;
  total_score: number;
  streak: number;
  best_score: number;
  last_quiz_date?: string;
};

// Fallback curated questions on Indian Law (BNS, IPC, Constitution, BNSS, Consumer Protection)
export const FALLBACK_QUIZ_BANK: QuizQuestion[] = [
  {
    question: "Which Article of the Indian Constitution guarantees the 'Right to Constitutional Remedies' (Writs)?",
    options: ["Article 32", "Article 21", "Article 14", "Article 19"],
    correct_index: 0,
    explanation: "Article 32 empowers citizens to move the Supreme Court directly for enforcement of Fundamental Rights. Dr. B.R. Ambedkar called it the heart and soul of the Constitution.",
    judge_verified: true,
    caution_note: ""
  },
  {
    question: "Under the Bharatiya Nyaya Sanhita (BNS), 2023, which section defines the offence of Murder?",
    options: ["Section 101", "Section 103", "Section 302", "Section 69"],
    correct_index: 0,
    explanation: "Under BNS 2023, Section 101 defines murder (corresponding to IPC Section 300), while Section 103 prescribes the punishment for murder.",
    judge_verified: true,
    caution_note: ""
  },
  {
    question: "What is the maximum period an accused can be detained in police custody under Section 167 CrPC / Section 187 BNSS during initial remand?",
    options: ["15 days", "30 days", "7 days", "24 hours"],
    correct_index: 0,
    explanation: "The Magistrate may authorize the detention of the accused in police custody for a term not exceeding 15 days in the whole or in parts under BNSS provisions.",
    judge_verified: true,
    caution_note: ""
  },
  {
    question: "Which landmark Supreme Court judgment established the 'Basic Structure Doctrine' of the Indian Constitution?",
    options: ["Kesavananda Bharati v. State of Kerala (1973)", "Maneka Gandhi v. Union of India (1978)", "Golaknath v. State of Punjab (1967)", "Minerva Mills v. Union of India (1980)"],
    correct_index: 0,
    explanation: "A 13-judge bench of the Supreme Court held in Kesavananda Bharati (1973) that Parliament cannot alter the basic structure or essential framework of the Constitution.",
    judge_verified: true,
    caution_note: ""
  },
  {
    question: "Under the Consumer Protection Act, 2019, which forum has jurisdiction for claims where the value of goods or services exceeds ₹10 Crore?",
    options: ["National Consumer Disputes Redressal Commission (NCDRC)", "State Consumer Disputes Redressal Commission", "District Consumer Disputes Redressal Commission", "Supreme Court of India directly"],
    correct_index: 0,
    explanation: "The National Commission (NCDRC) has pecuniary jurisdiction to entertain original complaints where the consideration exceeds ₹10 Crore.",
    judge_verified: true,
    caution_note: ""
  },
  {
    question: "Which section of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023 deals with Anticipatory Bail?",
    options: ["Section 482", "Section 438", "Section 437", "Section 484"],
    correct_index: 0,
    explanation: "Section 482 of the BNSS corresponds to Section 438 of the CrPC, enabling Sessions and High Courts to grant bail to persons apprehending arrest.",
    judge_verified: true,
    caution_note: ""
  },
  {
    question: "What does the Latin legal maxim 'Audi Alteram Partem' signify?",
    options: ["Listen to the other side / No one should be condemned unheard", "An act of God prejudices no one", "Ignorance of law is no excuse", "The burden of proof lies on the plaintiff"],
    correct_index: 0,
    explanation: "'Audi Alteram Partem' is a fundamental pillar of Natural Justice requiring that no party be condemned or penalized without an opportunity to be heard.",
    judge_verified: true,
    caution_note: ""
  },
  {
    question: "Under Article 21 of the Indian Constitution, the Right to Privacy was declared a fundamental right in which landmark case?",
    options: ["K.S. Puttaswamy v. Union of India (2017)", "Navtej Singh Johar v. Union of India (2018)", "Shreya Singhal v. Union of India (2015)", "Vishaka v. State of Rajasthan (1997)"],
    correct_index: 0,
    explanation: "A unanimous 9-judge bench in K.S. Puttaswamy (2017) affirmed that the Right to Privacy is an intrinsic part of the Right to Life and Personal Liberty under Article 21.",
    judge_verified: true,
    caution_note: ""
  }
];

function getQuizStorageKey(userId?: string | null): string {
  return `nyaya_quiz_stats_${userId || "guest"}`;
}

export function getLocalQuizStats(userId?: string | null): UserQuizStats {
  if (typeof window === "undefined") {
    return { quizzes_taken: 0, total_score: 0, streak: 0, best_score: 0 };
  }
  try {
    const raw = localStorage.getItem(getQuizStorageKey(userId));
    if (raw) return JSON.parse(raw);
  } catch {
    // ignore
  }
  return { quizzes_taken: 0, total_score: 0, streak: 0, best_score: 0 };
}

export function saveLocalQuizStats(stats: UserQuizStats, userId?: string | null): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(getQuizStorageKey(userId), JSON.stringify(stats));
  } catch {
    // ignore
  }
}

function shuffleOptions(q: QuizQuestion): QuizQuestion {
  const options = [...q.options];
  const correctText = options[q.correct_index];
  for (let i = options.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [options[i], options[j]] = [options[j], options[i]];
  }
  return {
    ...q,
    options,
    correct_index: options.indexOf(correctText),
  };
}

export async function getTodaysQuiz(): Promise<QuizQuestion[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/quiz/today`);
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) {
        return data;
      }
    }
  } catch (e) {
    console.warn("[quizService] Backend daily quiz unavailable, using curated question bank:", e);
  }

  // Shuffle and pick 5 distinct questions from curated bank
  const shuffled = [...FALLBACK_QUIZ_BANK].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, 5).map(shuffleOptions);
}