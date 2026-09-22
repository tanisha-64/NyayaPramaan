'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import { getScenario, submitAnswer, getProgress, Scenario, Progress } from '@/services/gameService'

const LEVELS = [
  { min: 0, name: 'Rookie', icon: '🥉', color: '#B08D57' },
  { min: 50, name: 'Defender', icon: '🥈', color: '#C0C0C0' },
  { min: 150, name: 'Champion', icon: '🥇', color: '#FFD700' },
  { min: 300, name: 'Legal Guardian', icon: '💎', color: '#5B8CFF' },
]

function getLevel(points: number) {
  return [...LEVELS].reverse().find((l) => points >= l.min) || LEVELS[0]
}

export default function RightsGamePage() {
  const { user, loading: authLoading, signOut } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login?redirect=/game')
    }
  }, [authLoading, user, router])

  const [scenario, setScenario] = useState<Scenario | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [progress, setProgress] = useState<Progress>({ total_points: 0, scenarios_completed: 0 })
  const [streak, setStreak] = useState(0)
  const [loading, setLoading] = useState(true)
  const [flash, setFlash] = useState<'correct' | 'wrong' | null>(null)

  useEffect(() => {
    if (!user) return

    // Load local progress if available
    try {
      const saved = localStorage.getItem('legal_game_progress')
      if (saved) {
        setProgress(JSON.parse(saved))
      }
    } catch {
      // ignore
    }

    loadScenario()
    getProgress()
      .then((p) => {
        if (p && (p.total_points > 0 || p.scenarios_completed > 0)) {
          setProgress(p)
          localStorage.setItem('legal_game_progress', JSON.stringify(p))
        }
      })
      .catch(() => {
        // Keep local progress
      })
  }, [user])

  async function loadScenario() {
    setLoading(true)
    setSelected(null)
    setFlash(null)
    try {
      const s = await getScenario()
      if (s && s.choices && s.choices.length > 0) {
        setScenario(s)
      } else {
        setScenario(null)
      }
    } catch {
      setScenario(null)
    }
    setLoading(false)
  }

  function playSound(type: 'correct' | 'wrong') {
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)

      if (type === 'correct') {
        osc.frequency.setValueAtTime(523.25, ctx.currentTime)
        osc.frequency.setValueAtTime(659.25, ctx.currentTime + 0.1)
        osc.frequency.setValueAtTime(783.99, ctx.currentTime + 0.2)
        gain.gain.setValueAtTime(0.15, ctx.currentTime)
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4)
        osc.start()
        osc.stop(ctx.currentTime + 0.4)
      } else {
        osc.type = 'sawtooth'
        osc.frequency.setValueAtTime(150, ctx.currentTime)
        gain.gain.setValueAtTime(0.12, ctx.currentTime)
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3)
        osc.start()
        osc.stop(ctx.currentTime + 0.3)
      }
    } catch {
      // Audio context might be restricted before interaction
    }
  }

  async function handleChoice(i: number) {
    if (selected !== null || !scenario) return
    setSelected(i)
    const isBest = scenario.choices[i].is_best
    setFlash(isBest ? 'correct' : 'wrong')
    playSound(isBest ? 'correct' : 'wrong')
    setStreak(isBest ? (s) => s + 1 : 0)
    const points = scenario.choices[i].points || 0

    // Update local state immediately
    const updatedLocal = {
      total_points: progress.total_points + points,
      scenarios_completed: progress.scenarios_completed + 1,
    }
    setProgress(updatedLocal)
    try {
      localStorage.setItem('legal_game_progress', JSON.stringify(updatedLocal))
    } catch {
      // ignore
    }

    try {
      const updated = await submitAnswer(points)
      if (updated && updated.total_points) {
        setProgress(updated)
        localStorage.setItem('legal_game_progress', JSON.stringify(updated))
      }
    } catch {
      /* non-fatal fallback already handled locally */
    }
  }

  if (authLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#050608] text-slate-400 font-sans text-sm">
        <div className="flex items-center gap-3">
          <span className="h-2.5 w-2.5 rounded-full bg-blue-500 animate-pulse-dot" />
          <span>Authenticating Legal Rights Game...</span>
        </div>
      </div>
    )
  }

  const level = getLevel(progress.total_points)

  return (
    <div className="min-h-screen bg-[#07090E] text-slate-100 font-sans">
      {/* Top App Header with Full Navigation */}
      <header className="sticky top-0 z-50 border-b border-white/[0.08] bg-[#07080D]/90 backdrop-blur-2xl px-6 py-3.5">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 no-underline">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-amber-500/20 via-blue-500/20 to-transparent border border-white/15 text-sm shadow-sm">
              ⚖️
            </span>
            <span className="font-[var(--font-serif)] text-base font-semibold tracking-wide text-white">
              NyayaPramaan
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-5 text-xs font-medium text-slate-300">
            <Link href="/public/chat" className="hover:text-white transition-colors">
              AI Chat
            </Link>
            <Link href="/app/dashboard" className="hover:text-white transition-colors">
              Case Workspace
            </Link>
            <Link href="/game" className="text-amber-400 font-semibold">
              Rights Game 🎮
            </Link>
            <Link href="/quiz" className="hover:text-white transition-colors">
              Daily Quiz
            </Link>
            <Link href="/news" className="hover:text-white transition-colors">
              Legal News
            </Link>
            <Link href="/trust-verification" className="hover:text-white transition-colors">
              Trust Engine
            </Link>
          </nav>

          <div className="flex items-center gap-3">
            <button
              onClick={() => signOut()}
              className="rounded-xl border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:border-red-500/30 hover:bg-red-500/10 hover:text-red-300 transition-all cursor-pointer"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* Main Game Arena */}
      <main className="mx-auto max-w-2xl px-4 py-8">
        {/* HUD bar */}
        <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.04] p-4 shadow-lg backdrop-blur-xl">
          <Link href="/public/chat" className="text-xs text-slate-400 hover:text-white transition-colors no-underline">
            ← Chat Workspace
          </Link>
          <div className="flex items-center gap-2">
            <span className="text-xl">{level.icon}</span>
            <span className="text-xs font-semibold" style={{ color: level.color }}>
              {level.name}
            </span>
          </div>
          <div className="flex items-center gap-4 text-xs font-medium">
            <span className="text-amber-400">🔥 Streak: {streak}</span>
            <span className="text-emerald-400">⭐ Points: {progress.total_points}</span>
          </div>
        </div>

        {/* Progress bar to next level */}
        <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-white/[0.08]">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              background: level.color,
              width: `${Math.min(100, (progress.total_points % 150) / 1.5)}%`,
            }}
          />
        </div>

        <div className="mt-6 text-center">
          <h1 className="font-[var(--font-serif)] text-2xl font-bold tracking-tight text-white">
            ⚖️ Legal Rights Defender
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Realistic everyday scenarios. Choose the right legal remedy.
          </p>
        </div>

        {loading && (
          <div className="mt-16 flex flex-col items-center justify-center text-center text-slate-400">
            <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse-dot mb-3" />
            <span className="text-xs">Loading scenario...</span>
          </div>
        )}

        {!loading && !scenario && (
          <div className="mt-16 text-center text-xs text-slate-400">
            <p>Couldn't load scenario.</p>
            <button
              onClick={loadScenario}
              className="mt-3 inline-block rounded-xl border border-blue-500/30 bg-blue-600/20 px-4 py-1.5 font-medium text-blue-300 hover:bg-blue-600/30 cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        {scenario && !loading && (
          <div
            className={`mt-6 rounded-3xl border p-6 sm:p-8 backdrop-blur-2xl transition-all duration-300 ${
              flash === 'correct'
                ? 'border-emerald-500/50 bg-emerald-500/[0.08] shadow-[0_0_40px_rgba(16,185,129,0.15)]'
                : flash === 'wrong'
                ? 'border-red-500/50 bg-red-500/[0.08] shadow-[0_0_40px_rgba(239,68,68,0.15)]'
                : 'border-white/10 bg-[#0E121B]/80 shadow-2xl'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="rounded-full border border-blue-500/30 bg-blue-500/15 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-blue-400">
                🎯 {scenario.category.replace(/_/g, ' ')}
              </span>
              <span className="text-[11px] text-slate-400">Scenario #{(progress.scenarios_completed || 0) + 1}</span>
            </div>

            <h2 className="mt-4 text-lg font-semibold text-white tracking-tight">{scenario.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-200">{scenario.scenario_text}</p>

            <div className="mt-6 flex flex-col gap-3">
              {scenario.choices.map((c, i) => {
                const isChosen = selected === i
                const isCorrectChoice = c.is_best
                let borderClass = 'border-white/10 bg-white/[0.03] hover:border-white/25 hover:bg-white/[0.06]'
                if (selected !== null) {
                  if (isCorrectChoice) {
                    borderClass = 'border-emerald-500/60 bg-emerald-500/15 text-emerald-200'
                  } else if (isChosen) {
                    borderClass = 'border-red-500/60 bg-red-500/15 text-red-200'
                  } else {
                    borderClass = 'border-white/5 bg-transparent opacity-40'
                  }
                }

                return (
                  <button
                    key={i}
                    onClick={() => handleChoice(i)}
                    disabled={selected !== null}
                    className={`group w-full rounded-2xl border p-4 text-left text-xs sm:text-sm transition-all cursor-pointer ${borderClass}`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="leading-relaxed font-medium">{c.text}</span>
                      {selected !== null && isCorrectChoice && <span className="text-base">✅</span>}
                      {selected !== null && isChosen && !isCorrectChoice && <span className="text-base">❌</span>}
                    </div>
                    {selected !== null && (isChosen || isCorrectChoice) && (
                      <p className="mt-3 border-t border-white/10 pt-2.5 text-xs text-slate-300 leading-relaxed">
                        {c.explanation}
                      </p>
                    )}
                  </button>
                )
              })}
            </div>

            {selected !== null && (
              <button
                onClick={loadScenario}
                className="mt-6 w-full rounded-2xl bg-gradient-to-r from-[#B8925A] via-[#C89B59] to-[#D4A368] py-3 text-xs sm:text-sm font-bold text-slate-950 shadow-lg hover:brightness-110 transition-all cursor-pointer"
              >
                Next Scenario →
              </button>
            )}
          </div>
        )}
      </main>
    </div>
  )
}