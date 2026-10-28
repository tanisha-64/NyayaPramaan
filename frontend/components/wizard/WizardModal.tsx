'use client'
import { useEffect, useState } from 'react'
import { listWizards, getWizard, getChequeBounceDeadline, WizardSummary, WizardDefinition, WizardStep, ChequeBounceDeadline } from '@/services/wizardService'

export function WizardModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [list, setList] = useState<WizardSummary[]>([])
  const [loadingList, setLoadingList] = useState(false)
  const [wizard, setWizard] = useState<WizardDefinition | null>(null)
  const [stepId, setStepId] = useState<string | null>(null)
  const [dateValue, setDateValue] = useState('')
  const [deadline, setDeadline] = useState<ChequeBounceDeadline | null>(null)
  const [calculating, setCalculating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open && list.length === 0 && !loadingList) {
      setLoadingList(true)
      listWizards()
        .then(setList)
        .catch(() => setError('Wizards load nahi ho paaye. Please try again.'))
        .finally(() => setLoadingList(false))
    }
  }, [open, list.length, loadingList])

  async function selectWizard(id: string) {
    setError(null)
    try {
      const w = await getWizard(id)
      setWizard(w); setStepId(w.start); setDeadline(null); setDateValue('')
    } catch {
      setError('Ye wizard load nahi ho paaya. Please try again.')
    }
  }

  async function calculateDeadline() {
    if (!dateValue) return
    setCalculating(true)
    try {
      setDeadline(await getChequeBounceDeadline(dateValue))
    } catch {
      setError('Deadline calculate nahi ho payi. Date check karo.')
    }
    setCalculating(false)
  }

  function backToList() {
    setWizard(null); setStepId(null); setDeadline(null); setError(null)
  }

  if (!open) return null

  const step: WizardStep | null = wizard && stepId ? wizard.steps[stepId] : null

  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 70, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <div onClick={(e) => e.stopPropagation()} style={{ width: '100%', maxWidth: 480, maxHeight: '85vh', overflowY: 'auto', background: '#0E121B', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 14, padding: 20, color: '#F7F5F0', boxSizing: 'border-box' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <span style={{ fontSize: 15, fontWeight: 600 }}>
            {wizard ? `${wizard.icon} ${wizard.title}` : '🧭 Guided Help'}
          </span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'rgba(247,245,240,0.5)', cursor: 'pointer', fontSize: 16 }}>✕</button>
        </div>

        {error && <p style={{ fontSize: 12, color: '#E06A47', marginBottom: 10 }}>⚠️ {error}</p>}

        {!wizard && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {loadingList && <p style={{ fontSize: 13, color: 'rgba(247,245,240,0.5)' }}>Loading...</p>}
            {list.map((w) => (
              <button key={w.id} onClick={() => selectWizard(w.id)} style={{
                textAlign: 'left', padding: '12px 14px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.12)',
                background: 'rgba(255,255,255,0.03)', color: '#F7F5F0', cursor: 'pointer', fontSize: 14,
              }}>
                {w.icon} {w.title}
              </button>
            ))}
          </div>
        )}

        {wizard && step && !step.result && (
          <div>
            <p style={{ fontSize: 14, marginBottom: 14, lineHeight: 1.5 }}>{step.question}</p>

            {step.date_input ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <input type="date" value={dateValue} onChange={(e) => setDateValue(e.target.value)}
                  style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.05)', color: '#F7F5F0' }} />
                <button onClick={calculateDeadline} disabled={!dateValue || calculating} style={{
                  padding: '10px 14px', borderRadius: 8, border: 'none', background: '#B8925A', color: '#0A0A0B',
                  fontWeight: 500, cursor: dateValue ? 'pointer' : 'default', opacity: dateValue ? 1 : 0.6,
                }}>
                  {calculating ? 'Calculating...' : 'Calculate Deadline'}
                </button>

                {deadline && (
                  <div style={{ marginTop: 6, padding: '10px 14px', borderRadius: 8, background: 'rgba(43,92,224,0.1)', border: '1px solid rgba(43,92,224,0.25)', fontSize: 13 }}>
                    <p style={{ margin: '0 0 4px' }}>📬 Legal notice bhejne ki deadline: <b>{deadline.notice_deadline}</b></p>
                    <p style={{ margin: '0 0 4px' }}>⏳ Payment window khatam: <b>{deadline.payment_window_ends}</b></p>
                    <p style={{ margin: 0 }}>⚖️ Complaint file karne ki deadline: <b>{deadline.complaint_deadline}</b></p>
                  </div>
                )}

                {step.next && (
                  <button onClick={() => setStepId(step.next!)} style={{
                    marginTop: 6, padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.2)',
                    background: 'transparent', color: 'rgba(247,245,240,0.8)', cursor: 'pointer', fontSize: 13,
                  }}>
                    Next: Steps dekho →
                  </button>
                )}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {(step.options || []).map((opt, i) => (
                  <button key={i} onClick={() => setStepId(opt.next)} style={{
                    textAlign: 'left', padding: '10px 14px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.15)',
                    background: 'rgba(255,255,255,0.03)', color: '#F7F5F0', cursor: 'pointer', fontSize: 13,
                  }}>
                    {opt.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {wizard && step?.result && (
          <div>
            <p style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>✅ {step.result.title}</p>
            <ul style={{ margin: 0, paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {step.result.checklist.map((line, i) => (
                <li key={i} style={{ fontSize: 13, lineHeight: 1.5 }}>{line}</li>
              ))}
            </ul>
            {step.result.citations.length > 0 && (
              <p style={{ marginTop: 12, fontSize: 11, color: 'rgba(247,245,240,0.5)' }}>
                📄 {step.result.citations.join(' · ')}
              </p>
            )}
          </div>
        )}

        {wizard && (
          <button onClick={backToList} style={{
            marginTop: 16, fontSize: 12, padding: '6px 10px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.15)',
            background: 'transparent', color: 'rgba(247,245,240,0.6)', cursor: 'pointer',
          }}>
            ← Wizards list pe wapas
          </button>
        )}

        <p style={{ marginTop: 14, fontSize: 10, color: 'rgba(247,245,240,0.35)' }}>
          👤 Ye general guidance hai, final decision ke liye qualified lawyer se consult karein.
        </p>
      </div>
    </div>
  )
}