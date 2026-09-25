'use client'
import { useState } from 'react'

/**
 * ReportButton — "Report Incorrect Answer" floating action.
 * Sends feedback to backend for improvement tracking.
 * Shows a mini confirmation toast after reporting.
 */
export function ReportButton({
  onReport,
}: {
  onReport: (reason: string) => void
}) {
  const [showForm, setShowForm] = useState(false)
  const [reason, setReason] = useState('')
  const [submitted, setSubmitted] = useState(false)

  function handleSubmit() {
    if (!reason.trim()) return
    onReport(reason.trim())
    setSubmitted(true)
    setTimeout(() => {
      setShowForm(false)
      setSubmitted(false)
      setReason('')
    }, 2200)
  }

  if (submitted) {
    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 5,
          fontSize: 11,
          fontWeight: 600,
          color: '#10B981',
          background: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.25)',
          borderRadius: 8,
          padding: '4px 10px',
        }}
      >
        <span>✓</span> Report submitted — thank you!
      </span>
    )
  }

  if (showForm) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
          padding: 12,
          background: 'rgba(239, 68, 68, 0.06)',
          border: '1px solid rgba(239, 68, 68, 0.2)',
          borderRadius: 12,
          maxWidth: 380,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#F87171', letterSpacing: '0.03em' }}>
            ⚠️ Report Incorrect Information
          </span>
          <button
            onClick={() => { setShowForm(false); setReason('') }}
            style={{
              background: 'none',
              border: 'none',
              color: 'rgba(248,250,252,0.4)',
              cursor: 'pointer',
              fontSize: 14,
              lineHeight: 1,
            }}
          >
            ✕
          </button>
        </div>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="What seems incorrect? (e.g., wrong section number, outdated precedent, misquoted judgment...)"
          rows={2}
          style={{
            width: '100%',
            background: 'rgba(0,0,0,0.3)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 8,
            padding: '8px 10px',
            color: '#F8FAFC',
            fontSize: 12,
            resize: 'none',
            outline: 'none',
            fontFamily: 'inherit',
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 6 }}>
          <button
            onClick={() => { setShowForm(false); setReason('') }}
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 8,
              padding: '5px 12px',
              color: 'rgba(248,250,252,0.6)',
              fontSize: 11,
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!reason.trim()}
            style={{
              background: reason.trim() ? 'rgba(239, 68, 68, 0.2)' : 'rgba(239, 68, 68, 0.08)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 8,
              padding: '5px 12px',
              color: reason.trim() ? '#F87171' : 'rgba(248,163,163,0.4)',
              fontSize: 11,
              fontWeight: 600,
              cursor: reason.trim() ? 'pointer' : 'not-allowed',
            }}
          >
            Submit Report
          </button>
        </div>
      </div>
    )
  }

  return (
    <button
      onClick={() => setShowForm(true)}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        background: 'transparent',
        border: '1px solid transparent',
        borderRadius: 8,
        padding: '3px 8px',
        color: 'rgba(248,250,252,0.35)',
        fontSize: 11,
        cursor: 'pointer',
        transition: 'all 0.2s',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.color = '#F87171'
        e.currentTarget.style.background = 'rgba(239, 68, 68, 0.08)'
        e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.2)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.color = 'rgba(248,250,252,0.35)'
        e.currentTarget.style.background = 'transparent'
        e.currentTarget.style.borderColor = 'transparent'
      }}
      title="Report incorrect information in this answer"
    >
      <span>🚩</span>
      <span>Report</span>
    </button>
  )
}
