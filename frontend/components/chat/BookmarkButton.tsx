'use client'
import { useState } from 'react'

/**
 * BookmarkButton — Save/unsave an answer for later reference.
 * Persists to localStorage as a lightweight solution.
 * A dedicated "Saved Answers" section can read from the same key.
 */
export function BookmarkButton({
  answerId,
  answerText,
  conclusion,
}: {
  answerId: string
  answerText: string
  conclusion?: string
}) {
  const storageKey = 'np_saved_answers'

  function getSaved(): Record<string, { text: string; conclusion?: string; savedAt: string }> {
    try {
      return JSON.parse(localStorage.getItem(storageKey) || '{}')
    } catch {
      return {}
    }
  }

  const [isSaved, setIsSaved] = useState(() => {
    if (typeof window === 'undefined') return false
    return !!getSaved()[answerId]
  })

  const [justSaved, setJustSaved] = useState(false)

  function toggleBookmark() {
    const saved = getSaved()
    if (saved[answerId]) {
      delete saved[answerId]
      setIsSaved(false)
    } else {
      saved[answerId] = {
        text: answerText.slice(0, 500),
        conclusion,
        savedAt: new Date().toISOString(),
      }
      setIsSaved(true)
      setJustSaved(true)
      setTimeout(() => setJustSaved(false), 1800)
    }
    localStorage.setItem(storageKey, JSON.stringify(saved))
  }

  return (
    <button
      onClick={toggleBookmark}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        background: isSaved ? 'rgba(184, 146, 90, 0.12)' : 'transparent',
        border: `1px solid ${isSaved ? 'rgba(184, 146, 90, 0.3)' : 'transparent'}`,
        borderRadius: 8,
        padding: '3px 8px',
        color: isSaved ? '#B8925A' : 'rgba(248,250,252,0.35)',
        fontSize: 11,
        cursor: 'pointer',
        transition: 'all 0.25s ease',
        fontWeight: isSaved ? 600 : 400,
      }}
      onMouseEnter={(e) => {
        if (!isSaved) {
          e.currentTarget.style.color = '#B8925A'
          e.currentTarget.style.background = 'rgba(184, 146, 90, 0.08)'
          e.currentTarget.style.borderColor = 'rgba(184, 146, 90, 0.2)'
        }
      }}
      onMouseLeave={(e) => {
        if (!isSaved) {
          e.currentTarget.style.color = 'rgba(248,250,252,0.35)'
          e.currentTarget.style.background = 'transparent'
          e.currentTarget.style.borderColor = 'transparent'
        }
      }}
      title={isSaved ? 'Remove from saved answers' : 'Save this answer for later'}
    >
      <span>{isSaved ? '★' : '☆'}</span>
      <span>{justSaved ? 'Saved!' : isSaved ? 'Saved' : 'Save'}</span>
    </button>
  )
}
