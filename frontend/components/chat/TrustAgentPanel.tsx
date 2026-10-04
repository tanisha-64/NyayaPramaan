'use client'
import { useState } from 'react'
import { LegalClaim, VerificationSummary } from '@/services/chatService'

const STATUS_STYLE: Record<string, { bg: string; border: string; text: string; label: string; icon: string }> = {
  'SUPPORTED': {
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    text: 'text-emerald-400',
    label: 'SUPPORTED',
    icon: '✓',
  },
  'PARTIALLY SUPPORTED': {
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    text: 'text-amber-400',
    label: 'PARTIAL EVIDENCE',
    icon: '◐',
  },
  'CONTRADICTED': {
    bg: 'bg-rose-500/10',
    border: 'border-rose-500/30',
    text: 'text-rose-400',
    label: 'CONTRADICTED',
    icon: '✕',
  },
  'INSUFFICIENT EVIDENCE': {
    bg: 'bg-slate-500/10',
    border: 'border-slate-500/30',
    text: 'text-slate-400',
    label: 'INSUFFICIENT EVIDENCE',
    icon: '○',
  },
}

export function TrustAgentPanel({
  claims,
  summary,
}: {
  claims?: LegalClaim[]
  summary?: VerificationSummary
}) {
  const [expanded, setExpanded] = useState(false)

  if (!claims || claims.length === 0) return null

  const total = summary?.claims_analyzed ?? claims.length
  const supported = summary?.supported ?? claims.filter((c) => c.status === 'SUPPORTED').length
  const partial = summary?.partially_supported ?? claims.filter((c) => c.status === 'PARTIALLY SUPPORTED').length
  const insufficient = summary?.insufficient_evidence ?? claims.filter((c) => c.status === 'INSUFFICIENT EVIDENCE').length
  const coverage = summary?.evidence_coverage ?? Math.round(((supported + 0.5 * partial) / Math.max(total, 1)) * 100)

  return (
    <div className="mt-3.5 rounded-2xl border border-white/[0.08] bg-[#0A0D14]/90 p-4 shadow-sm backdrop-blur-sm transition-all">
      {/* Header / Summary Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/15 border border-indigo-500/25 text-xs text-indigo-300 font-bold">
            🛡️
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-white tracking-wide">
                TrustAgent Verification Layer
              </span>
              <span className="rounded-full bg-emerald-500/15 border border-emerald-500/25 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                Evidence Coverage: {coverage}%
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Claims Analyzed: <span className="text-slate-200 font-medium">{total}</span> • Supported:{' '}
              <span className="text-emerald-400 font-medium">{supported}</span> • Partial:{' '}
              <span className="text-amber-400 font-medium">{partial}</span> • Insufficient:{' '}
              <span className="text-slate-400 font-medium">{insufficient}</span>
            </p>
          </div>
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-white/[0.08] hover:text-white transition-all cursor-pointer"
        >
          <span>{expanded ? 'Hide Breakdown' : 'View Verified Claims'}</span>
          <span className="text-[10px]">{expanded ? '▲' : '▼'}</span>
        </button>
      </div>

      {/* Progress Bar */}
      <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full bg-gradient-to-r from-blue-500 via-indigo-400 to-emerald-400 transition-all duration-500 rounded-full"
          style={{ width: `${Math.min(100, Math.max(5, coverage))}%` }}
        />
      </div>

      {/* Expanded Claims List */}
      {expanded && (
        <div className="mt-4 space-y-2.5 border-t border-white/[0.06] pt-3.5 animate-fadeIn">
          <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium pb-1">
            <span>Independent Legal Claim Assertions</span>
            <span>Evidentiary Status</span>
          </div>

          {claims.map((c, idx) => {
            const rawStatus = (c.status || 'INSUFFICIENT EVIDENCE').toUpperCase()
            const cfg = STATUS_STYLE[rawStatus] || STATUS_STYLE['INSUFFICIENT EVIDENCE']

            return (
              <div
                key={idx}
                className="rounded-xl border border-white/[0.06] bg-[#0E121C] p-3 transition-all hover:border-white/[0.12]"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 text-xs text-slate-200 leading-relaxed font-normal">
                    <span className="font-semibold text-slate-400 mr-1.5">{idx + 1}.</span>
                    {c.claim}
                  </div>
                  <span
                    className={`inline-flex items-center gap-1 rounded-lg border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider shrink-0 ${cfg.bg} ${cfg.border} ${cfg.text}`}
                  >
                    <span>{cfg.icon}</span>
                    <span>{cfg.label}</span>
                  </span>
                </div>

                {/* Evidence citation */}
                {c.evidence && (
                  <div className="mt-2 rounded-lg bg-black/30 px-2.5 py-1.5 text-[11px] text-slate-300 border border-white/[0.04] flex items-start gap-1.5">
                    <span className="text-indigo-400 font-semibold shrink-0">Evidence:</span>
                    <span className="italic">{c.evidence}</span>
                    {c.source && (
                      <span className="ml-auto text-[10px] text-slate-400 shrink-0 font-medium">
                        [{c.source}]
                      </span>
                    )}
                  </div>
                )}
              </div>
            )
          })}

          <p className="pt-2 text-[10px] text-slate-400 italic">
            * Evidence coverage measures verified alignment with statutory provisions and judicial records. It does not predict court verdicts.
          </p>
        </div>
      )}
    </div>
  )
}
