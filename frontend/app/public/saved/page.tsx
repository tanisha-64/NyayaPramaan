'use client'
import { useState, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { RoleGuard } from '@/components/auth/RoleGuard'
import Link from 'next/link'

type SavedAnswer = {
  text: string
  conclusion?: string
  savedAt: string
}

function SavedAnswersContent() {
  const { signOut } = useAuth()
  const [saved, setSaved] = useState<Record<string, SavedAnswer>>({})
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    try {
      const raw = localStorage.getItem('np_saved_answers')
      if (raw) setSaved(JSON.parse(raw))
    } catch {}
  }, [])

  function removeSaved(id: string) {
    const updated = { ...saved }
    delete updated[id]
    setSaved(updated)
    localStorage.setItem('np_saved_answers', JSON.stringify(updated))
  }

  function clearAll() {
    setSaved({})
    localStorage.setItem('np_saved_answers', '{}')
  }

  const entries = Object.entries(saved).filter(([, v]) => {
    if (!searchTerm.trim()) return true
    const term = searchTerm.toLowerCase()
    return v.text.toLowerCase().includes(term) || (v.conclusion || '').toLowerCase().includes(term)
  }).sort(([, a], [, b]) => new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime())

  return (
    <div className="min-h-screen bg-[#0A0A0B] text-slate-100 font-sans antialiased">
      {/* Header */}
      <header className="border-b border-[#B8925A]/15 bg-[#0A0A0B]/90 backdrop-blur-2xl sticky top-0 z-30">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-3.5">
          <div className="flex items-center gap-3">
            <Link href="/public/chat" className="flex items-center gap-2 text-white no-underline">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#B8925A]/20 border border-[#B8925A]/25 text-sm">
                ★
              </span>
              <span className="text-sm font-semibold">Saved Answers</span>
            </Link>
            <span className="rounded-full bg-[#B8925A]/12 border border-[#B8925A]/25 px-2 py-0.5 text-[10px] font-semibold text-[#B8925A]">
              {entries.length} saved
            </span>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/public/chat"
              className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs text-slate-300 hover:bg-white/[0.08] hover:text-white transition-all no-underline"
            >
              ← Back to Chat
            </Link>
            {entries.length > 0 && (
              <button
                onClick={clearAll}
                className="rounded-lg border border-red-500/20 bg-red-500/08 px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/15 transition-all cursor-pointer"
              >
                Clear All
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8">
        {/* Search */}
        {entries.length > 3 && (
          <div className="mb-6">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search saved answers..."
              className="w-full rounded-xl border border-[#B8925A]/15 bg-[#B8925A]/[0.04] px-4 py-2.5 text-sm text-white placeholder:text-slate-400 outline-none focus:border-[#B8925A]/40 focus:ring-1 focus:ring-[#B8925A]/20"
            />
          </div>
        )}

        {entries.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-[#B8925A]/15 border border-[#B8925A]/20 text-3xl mb-5">
              ★
            </div>
            <h2 className="text-lg font-semibold text-white mb-2">No saved answers yet</h2>
            <p className="text-xs text-slate-400 max-w-sm leading-relaxed">
              Click the ★ Save button on any AI response in your chat to bookmark it here for quick reference later.
            </p>
            <Link
              href="/public/chat"
              className="mt-6 rounded-xl bg-gradient-to-r from-[#B8925A] to-[#D4A368] px-5 py-2.5 text-xs font-semibold text-slate-950 hover:brightness-110 transition-all no-underline shadow-md"
            >
              Start Chatting →
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {entries.map(([id, item]) => (
              <div
                key={id}
                className="rounded-2xl border border-[#B8925A]/12 bg-[#B8925A]/[0.03] p-5 shadow-sm transition-all hover:border-[#B8925A]/25"
              >
                {/* Answer text preview */}
                <p className="text-sm leading-relaxed text-slate-200 whitespace-pre-wrap">
                  {item.text}
                </p>

                {/* Conclusion if available */}
                {item.conclusion && (
                  <div className="mt-3 rounded-xl border border-indigo-500/20 bg-indigo-500/[0.06] p-3">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-indigo-400">
                      Key Takeaway
                    </span>
                    <p className="mt-1 text-xs text-slate-300">{item.conclusion}</p>
                  </div>
                )}

                {/* Footer: date + remove */}
                <div className="mt-3 flex items-center justify-between border-t border-[#B8925A]/08 pt-2.5">
                  <span className="text-[11px] text-slate-400">
                    Saved on {new Date(item.savedAt).toLocaleString()}
                  </span>
                  <button
                    onClick={() => removeSaved(id)}
                    className="text-[11px] text-slate-400 hover:text-red-400 transition-colors cursor-pointer"
                  >
                    🗑 Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

export default function SavedPage() {
  return (
    <RoleGuard allowedRole="public">
      <SavedAnswersContent />
    </RoleGuard>
  )
}
