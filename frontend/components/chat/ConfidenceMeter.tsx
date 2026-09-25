'use client'

/**
 * ConfidenceMeter — A visual 0-100% gauge for answer confidence.
 * Shows a gradient progress bar + numeric percentage.
 * Color transitions: red (0-40) → amber (40-70) → green (70-100).
 */
export function ConfidenceMeter({ score }: { score: number }) {
  const clamped = Math.max(0, Math.min(100, Math.round(score)))

  let barColor: string
  let labelColor: string
  let label: string

  if (clamped >= 75) {
    barColor = 'linear-gradient(90deg, #10B981, #34D399)'
    labelColor = '#10B981'
    label = 'High Confidence'
  } else if (clamped >= 50) {
    barColor = 'linear-gradient(90deg, #F59E0B, #FBBF24)'
    labelColor = '#F59E0B'
    label = 'Moderate Confidence'
  } else if (clamped >= 25) {
    barColor = 'linear-gradient(90deg, #F97316, #FB923C)'
    labelColor = '#F97316'
    label = 'Low Confidence'
  } else {
    barColor = 'linear-gradient(90deg, #EF4444, #F87171)'
    labelColor = '#EF4444'
    label = 'Very Low Confidence'
  }

  return (
    <div className="confidence-meter" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      {/* Label */}
      <span
        style={{
          fontSize: 10,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: 'rgba(248,250,252,0.5)',
          whiteSpace: 'nowrap',
        }}
      >
        Confidence
      </span>

      {/* Track */}
      <div
        style={{
          flex: 1,
          height: 6,
          borderRadius: 999,
          background: 'rgba(255,255,255,0.06)',
          overflow: 'hidden',
          minWidth: 80,
          maxWidth: 160,
          position: 'relative',
        }}
      >
        {/* Fill */}
        <div
          style={{
            width: `${clamped}%`,
            height: '100%',
            borderRadius: 999,
            background: barColor,
            transition: 'width 0.8s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        />
      </div>

      {/* Value + Status */}
      <span
        style={{
          fontSize: 11,
          fontWeight: 700,
          color: labelColor,
          fontVariantNumeric: 'tabular-nums',
          whiteSpace: 'nowrap',
        }}
      >
        {clamped}%
      </span>
      <span
        style={{
          fontSize: 10,
          fontWeight: 600,
          color: labelColor,
          opacity: 0.85,
          whiteSpace: 'nowrap',
        }}
      >
        {label}
      </span>
    </div>
  )
}
