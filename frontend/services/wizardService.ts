import { apiGet, apiPost } from './apiClient'

export type WizardSummary = { id: string; title: string; icon: string }
export type WizardOption = { label: string; next: string }
export type WizardStep = {
  question?: string
  options?: WizardOption[]
  date_input?: boolean
  next?: string
  result?: { title: string; checklist: string[]; citations: string[] }
}
export type WizardDefinition = { title: string; icon: string; start: string; steps: Record<string, WizardStep> }
export type ChequeBounceDeadline = {
  bounce_date: string; notice_deadline: string; payment_window_ends: string; complaint_deadline: string
}

export function listWizards(): Promise<WizardSummary[]> {
  return apiGet('/wizards/list')
}

export function getWizard(id: string): Promise<WizardDefinition> {
  return apiGet(`/wizards/${id}`)
}

export function getChequeBounceDeadline(bounceDate: string): Promise<ChequeBounceDeadline> {
  return apiPost('/wizards/cheque-bounce/deadline', { bounce_date: bounceDate })
}