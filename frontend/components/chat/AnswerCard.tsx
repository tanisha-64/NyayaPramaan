'use client'
import { useState } from 'react'

type Source = {
  name: string
  type: string
  url: string | null
  verification_status: string
  jurisdiction: string | null
  page?: number | null
  section?: string
  excerpt?: string
}

export type PramaanCard = {
  act: string
  section: string
  act_name?: string | null
  heading?: string | null
  quote?: string | null
  source_url?: string | null
  page?: number | null
  verified: boolean
}

const STATUS: Record<string, { bg: string; text: string; icon: string; label: string }> = {
  verified: { bg: 'rgba(31,122,77,0.18)', text: '#2ECC71', icon: '✅', label: 'Verified' },
  partial: { bg: 'rgba(184,134,46,0.18)', text: '#D9A441', icon: '🟡', label: 'Partially supported' },
  contradicted: { bg: 'rgba(184,86,46,0.18)', text: '#E06A47', icon: '🔴', label: 'Contradicted' },
  unverified: { bg: 'rgba(255,255,255,0.08)', text: '#9a9a9a', icon: '⚪', label: 'Unverified' },
  pending: { bg: 'rgba(184,134,46,0.18)', text: '#D9A441', icon: '⏳', label: 'Verification pending' },
  external: { bg: 'rgba(43,92,224,0.18)', text: '#5B8CFF', icon: '🌐', label: 'Live web source' },
}

const VERDICT: Record<string, string> = {
  GROUNDED: 'verified',
  PARTIALLY_GROUNDED: 'partial',
  CONTRADICTED: 'contradicted',
  VERIFICATION_PENDING: 'pending',
  NO_EVIDENCE_FOUND: 'none',
  RETRIEVAL_INSUFFICIENT: 'none',
}

const USEFULNESS: Record<string, { bg: string; text: string }> = {
  high: { bg: 'rgba(31,122,77,0.15)', text: '#2ECC71' },
  medium: { bg: 'rgba(184,134,46,0.15)', text: '#D9A441' },
  low: { bg: 'rgba(184,86,46,0.15)', text: '#E06A47' },
}

function splitName(name: string): { base: string; loc: string } {
  const [rawBase, ...rest] = (name || 'Source').split(' — ')
  let base = rawBase.replace(/\.(pdf|docx?|txt|png|jpe?g)$/i, '').replace(/[_]+/g, ' ').trim()
  if (base.length > 38) base = base.slice(0, 35).trimEnd() + '…'
  return { base: base || 'Source', loc: rest.join(' — ') }
}

function PramaanDeck({ cards }: { cards: PramaanCard[] }) {
  if (!cards.length) return null
  return (
    <div style={{ marginTop: 10 }}>
      <div style={{ fontSize: 11, color: 'rgba(247,245,240,0.65)', marginBottom: 6 }}>🔖 Pramaan (Proof)</div>
      {cards.map((c, i) => (
        <div key={i} style={{
          marginBottom: 6, padding: '8px 12px', borderRadius: 10,
          background: c.verified ? 'rgba(31,122,77,0.10)' : 'rgba(184,86,46,0.12)',
          border: `1px solid ${c.verified ? 'rgba(46,204,113,0.3)' : 'rgba(224,106,71,0.4)'}`,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, flexWrap: 'wrap' }}>
            <span style={{ color: c.verified ? '#2ECC71' : '#E06A47', fontWeight: 600 }}>
              {c.verified ? '✅' : '⚠️'} {c.act} Section {c.section}
            </span>
            {c.act_name && <span style={{ color: 'rgba(247,245,240,0.5)' }}>· {c.act_name}</span>}
          </div>
          {c.verified ? (
            <>
              {c.quote && (
                <div style={{ marginTop: 4, fontSize: 11.5, color: 'rgba(247,245,240,0.65)', borderLeft: '2px solid rgba(46,204,113,0.5)', paddingLeft: 8 }}>
                  {c.quote}
                </div>
              )}
              {c.source_url && (
                <a href={c.source_url} target="_blank" rel="noopener noreferrer"
                   style={{ display: 'inline-block', marginTop: 4, fontSize: 11, color: '#5B8CFF' }}>
                  View official text{c.page ? ` (Page ${c.page})` : ''} →
                </a>
              )}
            </>
          ) : (
            <div style={{ marginTop: 4, fontSize: 11.5, color: '#E06A47' }}>
              Could not be verified against our official statute database — please confirm on India Code before relying on this.
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function EvidenceDeck({ sources }: { sources: Source[] }) {
  const [idx, setIdx] = useState(0)
  const [open, setOpen] = useState(false)
  const n = sources.length
  const go = (d: number) => {
    setOpen(false)
    setIdx((i) => (i + d + n) % n)
  }

  const cardBase: React.CSSProperties = {
    position: 'absolute', left: 0, right: 0, top: 0, borderRadius: 10, padding: '8px 12px',
    border: '1px solid rgba(255,255,255,0.10)', transition: 'transform .25s ease, opacity .25s ease',
    boxSizing: 'border-box', overflow: 'hidden',
  }

  const renderCard = (s: Source, k: number, expanded: boolean) => {
    const st = STATUS[s.verification_status] || STATUS.unverified
    const { base, loc } = splitName(s.name)
    const where = s.page ? `Page ${s.page}` : (s.section || loc || '')
    return (
      <div
        key={`${idx}-${k}`}
        style={{
          ...cardBase,
          position: expanded ? 'relative' : 'absolute',
          background: k === 0 ? '#1d2230' : k === 1 ? '#262d3f' : '#2d3548',
          transform: expanded ? 'none' : `translateY(${k * 12}px) scale(${1 - k * 0.05})`,
          transformOrigin: 'top center',
          opacity: 1,
          zIndex: 10 - k,
          height: expanded ? 'auto' : 62,
          cursor: k === 0 && n > 1 ? 'pointer' : 'default',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, whiteSpace: 'nowrap' }}>
          <span title={st.label} style={{ padding: '1px 8px', borderRadius: 10, background: st.bg, color: st.text, fontSize: 11, flexShrink: 0 }}>
            {st.icon} {st.label}
          </span>
          {s.url ? (
            <a href={s.url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}
               style={{ color: '#5B8CFF', textDecoration: 'none', overflow: 'hidden', textOverflow: 'ellipsis' }} title={s.name}>
              {base}
            </a>
          ) : (
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }} title={s.name}>{base}</span>
          )}
          {where && <span style={{ color: 'rgba(247,245,240,0.6)', flexShrink: 0 }}>· {where}</span>}
          {k === 0 && s.excerpt && s.excerpt.length > 90 && (
            <button
              onClick={(e) => { e.stopPropagation(); setOpen((o) => !o) }}
              style={{ marginLeft: 'auto', background: 'none', border: 'none', color: '#5B8CFF', fontSize: 11, cursor: 'pointer', padding: 0, flexShrink: 0 }}
            >
              {expanded ? 'Hide text ▲' : 'Show text ▼'}
            </button>
          )}
        </div>
        {s.excerpt && (
          <div
            style={{
              marginTop: 6, fontSize: 11.5, color: 'rgba(247,245,240,0.62)', borderLeft: '2px solid rgba(91,140,255,0.55)',
              paddingLeft: 8, whiteSpace: expanded ? 'pre-wrap' : 'nowrap',
              overflow: 'hidden', textOverflow: 'ellipsis',
            }}
          >
            {s.excerpt}
          </div>
        )}
      </div>
    )
  }

  const visible = [0, 1, 2].filter((k) => k < n).map((k) => ({ s: sources[(idx + k) % n], k }))

  return (
    <div style={{ marginTop: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11, color: 'rgba(247,245,240,0.65)', marginBottom: 6 }}>
        <span>📎 Evidence · {n}</span>
        {n > 1 && (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <button aria-label="Previous evidence" onClick={() => go(-1)} style={navBtn}>‹</button>
            {idx + 1} / {n}
            <button aria-label="Next evidence" onClick={() => go(1)} style={navBtn}>›</button>
          </span>
        )}
      </div>

      {open ? (
        renderCard(sources[idx], 0, true)
      ) : (
        <div
          role="button"
          tabIndex={0}
          aria-label="Show next evidence"
          onClick={() => n > 1 && go(1)}
          onKeyDown={(e) => { if ((e.key === 'Enter' || e.key === ' ') && n > 1) { e.preventDefault(); go(1) } }}
          style={{ position: 'relative', height: 62 + (Math.min(n, 3) - 1) * 12 }}
        >
          {[...visible].reverse().map(({ s, k }) => renderCard(s, k, false))}
        </div>
      )}
    </div>
  )
}

const navBtn: React.CSSProperties = {
  background: 'rgba(255,255,255,0.08)', border: 'none', color: 'inherit', borderRadius: 6,
  width: 22, height: 22, cursor: 'pointer', lineHeight: '20px', fontSize: 14,
}

export function AnswerCard({ answer, conclusion, usefulness, sources, pramaanCards, qualityNote, departmentSuggestion, verified, verdictState }: {
  answer: string
  conclusion?: string
  usefulness?: string
  sources?: Source[]
  pramaanCards?: PramaanCard[]
  qualityNote?: string
  departmentSuggestion?: string | null
  verified?: boolean
  verdictState?: string
}) {
  const notApplicable = verdictState === 'NOT_APPLICABLE'   // greetings / refusals: no evidence UI at all
  const generalInfo = verdictState === 'GENERAL_INFO'       // casual legal answer, nothing to verify against
  const key = verdictState ? (VERDICT[verdictState] ?? 'unverified') : (verified ? 'verified' : 'unverified')
  const badge = key === 'none' ? null : STATUS[key]
  const list = (sources || []).filter((s) => s && (s.name || s.excerpt))
  const pramaan = (pramaanCards || []).filter((c) => c && c.act && c.section)

  return (
    <div style={{ maxWidth: '90%' }}>
      <div style={{ padding: '12px 16px', borderRadius: 10, background: 'rgba(255,255,255,0.05)', fontSize: 14, whiteSpace: 'pre-wrap', lineHeight: 1.55 }}>
        {answer}
      </div>

      {!notApplicable && !generalInfo && badge && (
        <span style={{ display: 'inline-flex', marginTop: 8, fontSize: 11, padding: '4px 10px', borderRadius: 14, background: badge.bg, color: badge.text }}>
          Evidence status: {badge.icon} {badge.label}
        </span>
      )}
      {!notApplicable && !generalInfo && key === 'none' && (
        <span style={{ display: 'inline-flex', marginTop: 8, fontSize: 11, padding: '4px 10px', borderRadius: 14, background: 'rgba(255,255,255,0.08)', color: '#9a9a9a' }}>
          🔎 Nothing in the document supports this
        </span>
      )}
      {generalInfo && (
        <span style={{ display: 'inline-flex', marginTop: 8, fontSize: 11, padding: '4px 10px', borderRadius: 14, background: 'rgba(255,255,255,0.06)', color: '#9a9a9a' }}>
          ℹ️ General legal information
        </span>
      )}

      {!notApplicable && conclusion && (
        <div style={{ marginTop: 8, padding: '10px 14px', borderRadius: 8, background: 'rgba(43,92,224,0.1)', border: '1px solid rgba(43,92,224,0.25)' }}>
          <span style={{ fontSize: 11, color: '#5B8CFF', fontWeight: 600, textTransform: 'uppercase' }}>In Short</span>
          <p style={{ margin: '4px 0 0', fontSize: 13 }}>{conclusion}</p>
        </div>
      )}

      {!notApplicable && pramaan.length > 0 && <PramaanDeck cards={pramaan} />}
      {!notApplicable && list.length > 0 && <EvidenceDeck sources={list} />}

      {!notApplicable && usefulness && USEFULNESS[usefulness] && (
        <div style={{ marginTop: 8 }}>
          <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 10, background: USEFULNESS[usefulness].bg, color: USEFULNESS[usefulness].text }}>
            Usefulness: {usefulness}
          </span>
        </div>
      )}

      {qualityNote && <p style={{ marginTop: 8, fontSize: 11, color: '#D9A441' }}>⚠️ {qualityNote}</p>}
      {departmentSuggestion && <p style={{ marginTop: 8, fontSize: 12, color: 'rgba(247,245,240,0.6)' }}>📍 {departmentSuggestion}</p>}
      {!notApplicable && (
        <p style={{ marginTop: 8, fontSize: 10, color: 'rgba(247,245,240,0.35)' }}>
          👤 Final decisions on any specific case rest with a qualified lawyer or judge.
        </p>
      )}
    </div>
  )
}