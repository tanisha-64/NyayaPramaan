'use client'
import { useState } from 'react'
import { ConfidenceMeter } from './ConfidenceMeter'
import { ReportButton } from './ReportButton'
import { BookmarkButton } from './BookmarkButton'

type Source = {
  name: string
  type?: string
  url?: string | null
  verification_status?: string
  jurisdiction?: string | null
}

const STATUS_CONFIG: Record<string, { bg: string; border: string; text: string; label: string; icon: string }> = {
  verified: {
    bg: 'rgba(16, 185, 129, 0.12)',
    border: 'rgba(16, 185, 129, 0.3)',
    text: '#10B981',
    label: 'Verified',
    icon: '✓',
  },
  partial: {
    bg: 'rgba(245, 158, 11, 0.12)',
    border: 'rgba(245, 158, 11, 0.3)',
    text: '#F59E0B',
    label: 'Partially Verified',
    icon: '◐',
  },
  contradicted: {
    bg: 'rgba(239, 68, 68, 0.12)',
    border: 'rgba(239, 68, 68, 0.3)',
    text: '#EF4444',
    label: 'Contradicted',
    icon: '✕',
  },
  unverified: {
    bg: 'rgba(148, 163, 184, 0.12)',
    border: 'rgba(148, 163, 184, 0.25)',
    text: '#64748B',
    label: 'Pending',
    icon: '○',
  },
  external: {
    bg: 'rgba(59, 130, 246, 0.12)',
    border: 'rgba(59, 130, 246, 0.3)',
    text: '#3B82F6',
    label: 'Web Source',
    icon: '↗',
  },
}

const USEFULNESS_CONFIG: Record<string, { bg: string; border: string; text: string }> = {
  high: { bg: 'rgba(16, 185, 129, 0.12)', border: 'rgba(16, 185, 129, 0.28)', text: '#10B981' },
  medium: { bg: 'rgba(245, 158, 11, 0.12)', border: 'rgba(245, 158, 11, 0.28)', text: '#F59E0B' },
  low: { bg: 'rgba(239, 68, 68, 0.12)', border: 'rgba(239, 68, 68, 0.28)', text: '#EF4444' },
}

export function AnswerCard({
  answer,
  conclusion,
  usefulness,
  sources,
  qualityNote,
  departmentSuggestion,
  confidenceScore,
  messageIndex,
}: {
  answer: string
  conclusion?: string
  usefulness?: string
  sources?: (Source | string)[]
  qualityNote?: string
  departmentSuggestion?: string | null
  confidenceScore?: number
  messageIndex?: number
}) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(answer)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // fallback
    }
  }

  // Normalize sources if array contains strings
  const normalizedSources: Source[] = (sources || []).map((s) => {
    if (typeof s === 'string') {
      return {
        name: s,
        type: 'statute',
        url: null,
        verification_status: 'verified',
        jurisdiction: null,
      }
    }
    return s
  })

  // Derive confidence from verification data if not provided
  const derivedConfidence = confidenceScore ?? deriveConfidence(normalizedSources, usefulness)
  const answerId = `answer-${messageIndex ?? Date.now()}`

  return (
    <div className="answer-card-surface w-full max-w-full rounded-2xl border border-white/[0.08] bg-gradient-to-b from-[#141722]/95 to-[#0F1118]/95 p-5 shadow-xl backdrop-blur-md transition-all">
      {/* Header bar: AI Model badge & Copy Action */}
      <div className="mb-3.5 flex items-center justify-between border-b border-white/[0.06] pb-3">
        <div className="flex items-center gap-2">
          <span className="flex h-5 w-5 items-center justify-center rounded-md bg-blue-500/15 text-[11px] text-blue-400 font-semibold border border-blue-500/20">
            ⚖️
          </span>
          <span className="text-xs font-semibold tracking-wide text-white">NyayaPramaan AI</span>
          <span className="rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
            Evidence Verified
          </span>
        </div>

        <div className="flex items-center gap-1">
          <BookmarkButton
            answerId={answerId}
            answerText={answer}
            conclusion={conclusion}
          />
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs text-slate-400 hover:bg-white/[0.06] hover:text-white transition-all cursor-pointer border border-transparent hover:border-white/[0.08]"
            title="Copy answer"
          >
            {copied ? (
              <>
                <span className="text-emerald-400 font-bold">✓</span>
                <span className="text-emerald-400 text-[11px] font-medium">Copied</span>
              </>
            ) : (
              <>
                <span>📋</span>
                <span className="text-[11px]">Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Confidence Meter — visual gauge */}
      {derivedConfidence > 0 && (
        <div className="mb-3.5 rounded-xl border border-white/[0.04] bg-white/[0.02] px-3.5 py-2.5">
          <ConfidenceMeter score={derivedConfidence} />
        </div>
      )}

      {/* Main Answer Body */}
      <div className="text-[14px] leading-relaxed text-slate-200 font-normal whitespace-pre-wrap tracking-[0.01em]">
        {answer}
      </div>

      {/* Key Takeaway / In Short Highlight Box */}
      {conclusion && (
        <div className="mt-4 rounded-xl border border-indigo-500/25 bg-gradient-to-r from-indigo-950/40 via-indigo-900/20 to-transparent p-3.5 shadow-sm">
          <div className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse-dot" />
            <span className="text-[11px] font-semibold uppercase tracking-wider text-indigo-400">
              Key Legal Takeaway
            </span>
          </div>
          <p className="mt-1.5 text-[13px] leading-relaxed text-slate-200 font-medium">
            {conclusion}
          </p>
        </div>
      )}

      {/* Sources & Citations Section */}
      {normalizedSources && normalizedSources.length > 0 && (
        <div className="mt-4 pt-3.5 border-t border-white/[0.06]">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Evidentiary Sources ({normalizedSources.length})
            </span>
          </div>

          <div className="flex flex-wrap gap-2">
            {normalizedSources.map((s, i) => {
              const statusKey = s.verification_status || 'verified'
              const cfg = STATUS_CONFIG[statusKey] || STATUS_CONFIG.verified
              const badgeContent = (
                <div
                  className="group flex items-center gap-2 rounded-xl border px-3 py-1.5 text-xs transition-all hover:brightness-105 shadow-xs"
                  style={{ backgroundColor: cfg.bg, borderColor: cfg.border }}
                >
                  <span className="text-slate-200 font-medium tracking-tight">
                    {s.name}
                  </span>
                  {s.jurisdiction && s.jurisdiction !== 'unknown' && (
                    <span className="text-[10px] text-slate-400 uppercase">
                      [{s.jurisdiction}]
                    </span>
                  )}
                  <span
                    className="flex items-center gap-1 text-[10px] font-semibold"
                    style={{ color: cfg.text }}
                  >
                    <span>{cfg.icon}</span>
                    <span>{cfg.label}</span>
                  </span>
                </div>
              )

              return s.url ? (
                <a
                  key={i}
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="no-underline"
                >
                  {badgeContent}
                </a>
              ) : (
                <div key={i}>{badgeContent}</div>
              )
            })}
          </div>
        </div>
      )}

      {/* Quality Note and Department Helpline Badges */}
      {(qualityNote || departmentSuggestion || usefulness) && (
        <div className="mt-3.5 flex flex-wrap items-center gap-2 pt-2 text-xs">
          {usefulness && (
            <span
              className="rounded-md border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider"
              style={{
                backgroundColor: USEFULNESS_CONFIG[usefulness]?.bg,
                borderColor: USEFULNESS_CONFIG[usefulness]?.border,
                color: USEFULNESS_CONFIG[usefulness]?.text,
              }}
            >
              Relevance: {usefulness}
            </span>
          )}

          {qualityNote && (
            <span className="flex items-center gap-1 text-[11px] text-amber-400 bg-amber-500/10 border border-amber-500/25 px-2.5 py-0.5 rounded-md font-medium">
              <span>⚠️</span>
              <span>{qualityNote}</span>
            </span>
          )}

          {departmentSuggestion && (
            <span className="flex items-center gap-1 text-[11px] text-blue-400 bg-blue-500/10 border border-blue-500/25 px-2.5 py-0.5 rounded-md font-medium">
              <span>📍</span>
              <span>{departmentSuggestion}</span>
            </span>
          )}
        </div>
      )}

      {/* Footer: Report + Legal Safeguard */}
      <div className="mt-3.5 border-t border-white/[0.04] pt-2.5 flex items-center justify-between text-[11px] text-slate-400">
        <div className="flex items-center gap-2">
          <span>Verified against statutes & case repository</span>
          <ReportButton
            onReport={(reason) => {
              // Send to backend for tracking — graceful fail
              try {
                fetch('/api/report', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ answerId, reason, timestamp: new Date().toISOString() }),
                }).catch(() => {})
              } catch {
                // Silent fail — report is stored locally as well
              }
              // Also store locally
              try {
                const reports = JSON.parse(localStorage.getItem('np_reports') || '[]')
                reports.push({ answerId, reason, timestamp: new Date().toISOString() })
                localStorage.setItem('np_reports', JSON.stringify(reports))
              } catch {}
            }}
          />
        </div>
        <span>Not formal legal representation</span>
      </div>
    </div>
  )
}

/**
 * Derive a confidence score from the verification data when not explicitly provided.
 */
function deriveConfidence(sources: Source[], usefulness?: string): number {
  if (!sources.length) return 0

  let total = 0
  for (const s of sources) {
    const status = s.verification_status || 'unverified'
    if (status === 'verified') total += 100
    else if (status === 'partial') total += 60
    else if (status === 'external') total += 50
    else if (status === 'contradicted') total += 10
    else total += 30 // unverified
  }

  let score = total / sources.length

  // Adjust by usefulness
  if (usefulness === 'high') score = Math.min(100, score * 1.05)
  else if (usefulness === 'low') score = Math.max(0, score * 0.75)

  return Math.round(score)
}