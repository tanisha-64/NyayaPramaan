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

const STATUS_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  verified: { bg: 'rgba(31,122,77,0.15)', text: '#2ECC71', label: '✅ Verified' },
  partial: { bg: 'rgba(184,134,46,0.15)', text: '#D9A441', label: '🟡 Partially Supported' },
  contradicted: { bg: 'rgba(184,86,46,0.15)', text: '#E06A47', label: '🔴 Contradicted' },
  unverified: { bg: 'rgba(255,255,255,0.08)', text: '#999', label: '⚪ Unverified' },
  pending: { bg: 'rgba(184,134,46,0.15)', text: '#D9A441', label: '⏳ Verification Pending' },
  external: { bg: 'rgba(43,92,224,0.15)', text: '#5B8CFF', label: '🌐 Live Web Source' },
}

const USEFULNESS_COLORS: Record<string, { bg: string; text: string }> = {
  high: { bg: 'rgba(31,122,77,0.15)', text: '#2ECC71' },
  medium: { bg: 'rgba(184,134,46,0.15)', text: '#D9A441' },
  low: { bg: 'rgba(184,86,46,0.15)', text: '#E06A47' },
}

const VERDICT_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  GROUNDED: STATUS_COLORS.verified,
  PARTIALLY_GROUNDED: STATUS_COLORS.partial,
  CONTRADICTED: STATUS_COLORS.contradicted,
  NO_EVIDENCE_FOUND: STATUS_COLORS.unverified,
  RETRIEVAL_INSUFFICIENT: STATUS_COLORS.unverified,
  VERIFICATION_PENDING: STATUS_COLORS.pending,
}

export function AnswerCard({ answer, conclusion, usefulness, sources, qualityNote, departmentSuggestion, verified, verdictState }: {
  answer: string
  conclusion?: string
  usefulness?: string
  sources?: Source[]
  qualityNote?: string
  departmentSuggestion?: string | null
  verified?: boolean
  verdictState?: string
}) {
  const verification = verified === true
    ? STATUS_COLORS.verified
    : VERDICT_STYLES[verdictState || ''] || STATUS_COLORS.unverified

  return (
    <div style={{ maxWidth: '90%' }}>
      <div style={{ padding: '12px 16px', borderRadius: 10, background: 'rgba(255,255,255,0.05)', fontSize: 14, whiteSpace: 'pre-wrap' }}>
        {answer}
      </div>

      <span style={{ display: 'inline-flex', marginTop: 8, fontSize: 11, padding: '4px 10px', borderRadius: 14, background: verification.bg, color: verification.text }}>
        Evidence status: {verification.label}
      </span>

      {conclusion && (
        <div style={{ marginTop: 8, padding: '10px 14px', borderRadius: 8, background: 'rgba(43,92,224,0.1)', border: '1px solid rgba(43,92,224,0.25)' }}>
          <span style={{ fontSize: 11, color: '#5B8CFF', fontWeight: 600, textTransform: 'uppercase' }}>In Short</span>
          <p style={{ margin: '4px 0 0', fontSize: 13 }}>{conclusion}</p>
        </div>
      )}

      {sources && sources.length > 0 && (
        <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {sources.map((s, i) => {
            const style = STATUS_COLORS[s.verification_status] || STATUS_COLORS.unverified
            const content = (
              <span style={{ fontSize: 11, padding: '4px 10px', borderRadius: 14, background: style.bg, color: style.text, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                {s.name || 'Source'} {s.jurisdiction && s.jurisdiction !== 'unknown' && `(${s.jurisdiction})`} · {style.label}
              </span>
            )
            return (
              <div key={i} style={{ display: 'grid', gap: 4 }}>
                {s.url ? (
                  <a href={s.url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none' }}>{content}</a>
                ) : content}
                {(s.page || s.section || s.excerpt) && (
                  <details style={{ fontSize: 11, color: 'rgba(247,245,240,0.65)' }}>
                    <summary style={{ cursor: 'pointer', padding: '2px 4px' }}>
                      {s.page ? `Page ${s.page}` : s.section || 'Source details'}
                    </summary>
                    {s.section && <div style={{ padding: '4px 8px' }}>{s.section}</div>}
                    {s.excerpt && (
                      <blockquote style={{ margin: '2px 0 0', padding: '6px 8px', borderLeft: '2px solid rgba(91,140,255,0.6)', background: 'rgba(255,255,255,0.03)', whiteSpace: 'pre-wrap' }}>
                        {s.excerpt}
                      </blockquote>
                    )}
                  </details>
                )}
              </div>
            )
          })}
        </div>
      )}

      <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {usefulness && (
          <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 10, background: USEFULNESS_COLORS[usefulness]?.bg, color: USEFULNESS_COLORS[usefulness]?.text }}>
            Usefulness: {usefulness}
          </span>
        )}
      </div>

      {qualityNote && <p style={{ marginTop: 8, fontSize: 11, color: '#D9A441' }}>⚠️ {qualityNote}</p>}
      {departmentSuggestion && <p style={{ marginTop: 8, fontSize: 12, color: 'rgba(247,245,240,0.6)' }}>📍 {departmentSuggestion}</p>}
      <p style={{ marginTop: 8, fontSize: 10, color: 'rgba(247,245,240,0.35)' }}>
        👤 Final decisions on any specific case rest with a qualified lawyer or judge.
      </p>
    </div>
  )
}
