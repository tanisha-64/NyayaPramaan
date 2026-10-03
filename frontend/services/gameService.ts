import { apiGet, apiPost } from "./apiClient";

export type Choice = {
  text: string;
  is_best: boolean;
  points: number;
  explanation: string;
};

export type Scenario = {
  id: string;
  title: string;
  scenario_text: string;
  choices: Choice[];
  category: string;
  verified?: boolean;
};

export type UserProgress = {
  total_points: number;
  scenarios_completed: number;
  streak: number;
  best_streak: number;
  last_played_date?: string;
  level_name?: string;
};

// Fallback high-quality curated scenarios for 100% offline & zero-latency reliability
export const FALLBACK_SCENARIOS: Scenario[] = [
  {
    id: "arrest_01",
    category: "arrest_rights",
    title: "Police Detention Without Stated Grounds",
    scenario_text: "You are stopped by police officers at 9:00 PM near a metro station. An officer demands you accompany them to the police station without stating any reason or showing identification.",
    choices: [
      {
        text: "Politely ask for the officer's name/designation and demand to know the specific grounds of arrest under Section 50 CrPC / Section 47 BNSS.",
        is_best: true,
        points: 10,
        explanation: "Under Article 22(1) of the Constitution and Section 50 CrPC (Section 47 BNSS), every citizen has the fundamental right to know the grounds of arrest and consult a legal counsel."
      },
      {
        text: "Physically resist the officer and try to run away.",
        is_best: false,
        points: 0,
        explanation: "Resisting a public servant can lead to additional charges under Section 186/353 IPC (Section 221/132 BNS)."
      },
      {
        text: "Offer cash on the spot to settle the matter immediately.",
        is_best: false,
        points: 0,
        explanation: "Attempting to bribe a police officer is a cognizable offence under the Prevention of Corruption Act."
      }
    ],
    verified: true
  },
  {
    id: "arrest_02",
    category: "women_safety_rights",
    title: "Arrest of a Woman After Sunset",
    scenario_text: "At 8:30 PM, police officers arrive at a woman's residence intending to arrest her in connection with a non-violent financial dispute.",
    choices: [
      {
        text: "State that under Section 46(4) CrPC / Section 43(5) BNSS, a woman cannot be arrested after sunset and before sunrise except in exceptional circumstances with prior Magistrate permission.",
        is_best: true,
        points: 10,
        explanation: "Section 46(4) CrPC strictly prohibits arresting women between sunset and sunrise except under exceptional circumstances with prior judicial sanction."
      },
      {
        text: "Go to the station immediately with the male officers without asking any questions.",
        is_best: false,
        points: 2,
        explanation: "A woman is entitled to be accompanied by a female police officer and cannot be taken into custody at night without judicial sanction."
      },
      {
        text: "Refuse all communication and lock the premises.",
        is_best: false,
        points: 0,
        explanation: "Asserting legal statutory rights through lawful dialogue is the prescribed procedure."
      }
    ],
    verified: true
  },
  {
    id: "consumer_01",
    category: "consumer_rights",
    title: "Defective Electronics & 'No Refund' Policy",
    scenario_text: "You purchased a new laptop that stopped working within 3 days. The store manager points to a receipt stating 'No Returns / No Refunds' and refuses repair or replacement.",
    choices: [
      {
        text: "Lodge a complaint on the National Consumer Helpline (NCH / INGRAM 1915) and prepare a consumer grievance under the Consumer Protection Act, 2019.",
        is_best: true,
        points: 10,
        explanation: "Under the Consumer Protection Act 2019, blanket 'no refund' clauses for defective products constitute an Unfair Trade Practice. Consumers are legally entitled to repair, replacement, or refund."
      },
      {
        text: "Accept the store's statement and discard the laptop.",
        is_best: false,
        points: 0,
        explanation: "Consumers have legally enforceable rights against manufacturing defects and unfair trade practices."
      },
      {
        text: "Create abusive posts targeting individual store employees on social media.",
        is_best: false,
        points: 0,
        explanation: "Defamation and harassment can lead to civil and criminal liability; legal consumer dispute forums provide statutory remedies."
      }
    ],
    verified: true
  },
  {
    id: "property_01",
    category: "property_rights",
    title: "Arbitrary Disconnection of Essential Amenities",
    scenario_text: "Your landlord abruptly cuts off water and electricity to your rented apartment following a disagreement over rent enhancement, giving you 24 hours to vacate.",
    choices: [
      {
        text: "File an urgent petition before the Rent Authority / Civil Court for restoration of essential services and an injunction against illegal eviction.",
        is_best: true,
        points: 10,
        explanation: "Landlords are prohibited by state tenancy acts and the Model Tenancy Act from withholding essential supplies (water/electricity) without just cause or evicting without due process."
      },
      {
        text: "Immediately vacate without asserting your tenancy rights.",
        is_best: false,
        points: 0,
        explanation: "Tenants are protected against summary extra-judicial eviction under tenancy laws."
      },
      {
        text: "Damage the rental property in retaliation.",
        is_best: false,
        points: 0,
        explanation: "Damaging property constitutes criminal mischief under Section 425 IPC / Section 324 BNS."
      }
    ],
    verified: true
  },
  {
    id: "cyber_01",
    category: "workplace_rights",
    title: "Unauthorized Digital Payment Fraud",
    scenario_text: "You notice an unauthorized debit of ₹25,000 from your bank account despite never sharing your OTP or PIN with anyone.",
    choices: [
      {
        text: "Report the fraud to the National Cyber Crime Reporting Portal (1930 / cybercrime.gov.in) and notify your bank within 3 days for zero liability under RBI guidelines.",
        is_best: true,
        points: 10,
        explanation: "RBI's circular on customer liability in unauthorized electronic banking transactions grants zero liability if the customer notifies the bank within 3 working days."
      },
      {
        text: "Wait a month to see if the bank reverses the transaction automatically.",
        is_best: false,
        points: 0,
        explanation: "Delaying beyond 3 days increases customer liability under RBI regulations."
      },
      {
        text: "Contact unverified recovery agents found on search engines.",
        is_best: false,
        points: 0,
        explanation: "Third-party recovery agents are frequently secondary scams targeting cyber fraud victims."
      }
    ],
    verified: true
  }
];

function getUserStorageKey(userId?: string | null): string {
  return `nyaya_game_progress_${userId || "guest"}`;
}

export function getLocalUserProgress(userId?: string | null): UserProgress {
  if (typeof window === "undefined") {
    return { total_points: 0, scenarios_completed: 0, streak: 0, best_streak: 0 };
  }
  try {
    const raw = localStorage.getItem(getUserStorageKey(userId));
    if (raw) return JSON.parse(raw);
  } catch {
    // ignore
  }
  return { total_points: 0, scenarios_completed: 0, streak: 0, best_streak: 0 };
}

export function saveLocalUserProgress(progress: UserProgress, userId?: string | null): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(getUserStorageKey(userId), JSON.stringify(progress));
  } catch {
    // ignore
  }
}

export async function getScenario(): Promise<Scenario> {
  try {
    const s = await apiGet<Scenario>("/game/scenario");
    if (s && s.choices && s.choices.length > 0) {
      return s;
    }
  } catch (err) {
    console.warn("[gameService] Backend scenario fetch failed, serving curated fallback:", err);
  }

  // Pick random curated scenario and shuffle choices
  const base = FALLBACK_SCENARIOS[Math.floor(Math.random() * FALLBACK_SCENARIOS.length)];
  const shuffledChoices = [...base.choices].sort(() => Math.random() - 0.5);
  return {
    ...base,
    id: `${base.id}_${Date.now()}`,
    choices: shuffledChoices,
  };
}

export async function submitAnswer(
  points: number,
  isBest: boolean,
  userId?: string | null
): Promise<UserProgress> {
  const current = getLocalUserProgress(userId);
  const today = new Date().toISOString().split("T")[0];

  const newPoints = current.total_points + points;
  const newCompleted = current.scenarios_completed + 1;
  const newStreak = isBest ? (current.streak || 0) + 1 : 0;
  const newBestStreak = Math.max(current.best_streak || 0, newStreak);

  const updated: UserProgress = {
    total_points: newPoints,
    scenarios_completed: newCompleted,
    streak: newStreak,
    best_streak: newBestStreak,
    last_played_date: today,
  };

  saveLocalUserProgress(updated, userId);

  // Sync with backend API if available
  try {
    const remote = await apiPost<{ total_points: number; scenarios_completed: number; streak?: number }>(
      "/game/answer",
      { points, is_best: isBest, streak: newStreak }
    );
    if (remote && remote.total_points) {
      updated.total_points = remote.total_points;
      updated.scenarios_completed = remote.scenarios_completed;
      saveLocalUserProgress(updated, userId);
    }
  } catch {
    // Keep local progress
  }

  return updated;
}

export async function getProgress(userId?: string | null): Promise<UserProgress> {
  const local = getLocalUserProgress(userId);
  try {
    const remote = await apiGet<{ total_points: number; scenarios_completed: number; streak?: number }>(
      "/game/progress"
    );
    if (remote && (remote.total_points > 0 || remote.scenarios_completed > 0)) {
      const merged: UserProgress = {
        ...local,
        total_points: Math.max(local.total_points, remote.total_points),
        scenarios_completed: Math.max(local.scenarios_completed, remote.scenarios_completed),
        streak: remote.streak !== undefined ? remote.streak : local.streak,
      };
      saveLocalUserProgress(merged, userId);
      return merged;
    }
  } catch {
    // ignore
  }
  return local;
}