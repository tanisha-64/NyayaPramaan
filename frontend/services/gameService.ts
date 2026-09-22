import { apiGet, apiPost } from "./apiClient";

export type Choice = { text: string; is_best: boolean; points: number; explanation: string };
export type Scenario = { id: string; title: string; scenario_text: string; choices: Choice[]; category: string; verified?: boolean };
export type Progress = { total_points: number; scenarios_completed: number };

export function getScenario() { return apiGet<Scenario>("/game/scenario"); }
export function submitAnswer(points: number) { return apiPost<Progress>("/game/answer", { points }); }
export function getProgress() { return apiGet<Progress>("/game/progress"); }