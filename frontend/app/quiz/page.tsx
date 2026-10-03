'use client'
import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { TopNav } from '@/components/layout/TopNav'
import { Footer } from '@/components/layout/Footer'
import { useAuth } from '@/hooks/useAuth'
import {
  getTodaysQuiz,
  QuizQuestion,
  getLocalQuizStats,
  saveLocalQuizStats,
  UserQuizStats,
} from '@/services/quizService'

export default function QuizPage() {
  const { user, loading: authLoading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login?redirect=/quiz')
    }
  }, [authLoading, user, router])

  const [questions, setQuestions] = useState<QuizQuestion[]>([])
  const [current, setCurrent] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)
  const [score, setScore] = useState(0)
  const [finished, setFinished] = useState(false)
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<UserQuizStats>({
    quizzes_taken: 0,
    total_score: 0,
    streak: 0,
    best_score: 0,
  })

  const loadQuiz = useCallback(async () => {
    setLoading(true)
    setSelected(null)
    setScore(0)
    setFinished(false)
    setCurrent(0)
    try {
      const q = await getTodaysQuiz()
      setQuestions(q)
    } catch {
      // getTodaysQuiz guarantees fallback
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!user) return
    const userStats = getLocalQuizStats(user.id)
    setStats(userStats)
    loadQuiz()
  }, [user, loadQuiz])

  function handleAnswer(index: number) {
    if (selected !== null) return
    setSelected(index)
    const isCorrect = index === questions[current].correct_index
    if (isCorrect) setScore((s) => s + 1)
  }

  function handleNext() {
    if (current + 1 >= questions.length) {
      // Complete quiz and update user-isolated stats
      const finalScore = score + (selected === questions[current]?.correct_index ? 1 : 0)
      if (user) {
        const today = new Date().toISOString().split('T')[0]
        const isPassed = finalScore >= Math.ceil(questions.length * 0.6)
        const newStreak = isPassed ? (stats.streak || 0) + 1 : 0
        const updatedStats: UserQuizStats = {
          quizzes_taken: (stats.quizzes_taken || 0) + 1,
          total_score: (stats.total_score || 0) + finalScore,
          streak: newStreak,
          best_score: Math.max(stats.best_score || 0, finalScore),
          last_quiz_date: today,
        }
        setStats(updatedStats)
        saveLocalQuizStats(updatedStats, user.id)
      }
      setFinished(true)
      return
    }
    setCurrent((c) => c + 1)
    setSelected(null)
  }

  if (authLoading || !user) {
    return (
      <>
        <TopNav />
        <main className="min-h-[70vh] flex items-center justify-center text-slate-400 font-sans text-sm">
          <div className="flex items-center gap-3">
            <span className="h-2 w-2 rounded-full bg-[#B8925A] animate-pulse-dot" />
            <span>Authenticating Daily Quiz...</span>
          </div>
        </main>
        <Footer />
      </>
    )
  }

  return (
    <>
      <TopNav />
      <main className="min-h-[80vh] px-4 py-10 font-sans text-slate-100">
        <div className="mx-auto max-w-2xl">
          {/* Header Stats Bar */}
          <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.04] p-4 shadow-lg backdrop-blur-xl">
            <Link href="/public/chat" className="text-xs text-slate-400 hover:text-white transition-colors no-underline">
              ← Chat Workspace
            </Link>
            <div className="flex items-center gap-4 text-xs font-medium">
              <span className="text-amber-400">🔥 Streak: {stats.streak || 0}</span>
              <span className="text-emerald-400">⭐ Best Score: {stats.best_score || 0}/5</span>
            </div>
          </div>

          <div className="mt-8 text-center">
            <h1 className="font-[var(--font-serif)] text-2xl font-bold tracking-tight text-white">
              📜 Daily Legal Intelligence Quiz
            </h1>
            <p className="mt-1 text-xs text-slate-400">
              Test your knowledge of the Indian Constitution, BNS, BNSS, and Landmark Judgments.
            </p>
          </div>

          {loading && (
            <div className="mt-16 flex flex-col items-center justify-center text-center text-slate-400">
              <span className="h-2 w-2 rounded-full bg-[#B8925A] animate-pulse-dot mb-3" />
              <span className="text-xs">Preparing today&apos;s verified quiz...</span>
            </div>
          )}

          {!loading && !finished && questions.length > 0 && (
            <div className="mt-6 rounded-3xl border border-white/10 bg-[#0E121B]/80 p-6 sm:p-8 backdrop-blur-2xl shadow-2xl">
              {/* Progress Indicator */}
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="font-semibold text-[#D4A368]">Question {current + 1} of {questions.length}</span>
                <span>Score: {score}</span>
              </div>
              <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-white/[0.08]">
                <div
                  className="h-full bg-gradient-to-r from-[#B8925A] to-[#D4A368] transition-all duration-300"
                  style={{ width: `${((current + 1) / questions.length) * 100}%` }}
                />
              </div>

              {/* Question Text */}
              <h2 className="mt-6 text-base sm:text-lg font-semibold text-white leading-snug">
                {questions[current].question}
              </h2>

              {/* Options */}
              <div className="mt-6 flex flex-col gap-3">
                {questions[current].options.map((opt, idx) => {
                  const isSelected = selected === idx
                  const isCorrect = idx === questions[current].correct_index
                  let btnStyle = 'border-white/10 bg-white/[0.03] hover:border-white/25 hover:bg-white/[0.06]'

                  if (selected !== null) {
                    if (isCorrect) {
                      btnStyle = 'border-emerald-500/60 bg-emerald-500/15 text-emerald-200'
                    } else if (isSelected) {
                      btnStyle = 'border-red-500/60 bg-red-500/15 text-red-200'
                    } else {
                      btnStyle = 'border-white/5 bg-transparent opacity-40'
                    }
                  }

                  return (
                    <button
                      key={idx}
                      onClick={() => handleAnswer(idx)}
                      disabled={selected !== null}
                      className={`w-full rounded-2xl border p-4 text-left text-xs sm:text-sm transition-all cursor-pointer ${btnStyle}`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-medium leading-relaxed">{opt}</span>
                        {selected !== null && isCorrect && <span>✅</span>}
                        {selected !== null && isSelected && !isCorrect && <span>❌</span>}
                      </div>
                    </button>
                  )
                })}
              </div>

              {/* Explanation Note */}
              {selected !== null && questions[current].explanation && (
                <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-xs text-slate-300 leading-relaxed">
                  <span className="font-semibold text-[#D4A368]">📖 Legal Precedent / Provision:</span>
                  <p className="mt-1">{questions[current].explanation}</p>
                </div>
              )}

              {/* Next Button */}
              {selected !== null && (
                <button
                  onClick={handleNext}
                  className="mt-6 w-full rounded-2xl bg-gradient-to-r from-[#B8925A] via-[#C89B59] to-[#D4A368] py-3 text-xs sm:text-sm font-bold text-slate-950 shadow-lg hover:brightness-110 transition-all cursor-pointer"
                >
                  {current + 1 === questions.length ? 'Complete Quiz & View Score →' : 'Next Question →'}
                </button>
              )}
            </div>
          )}

          {finished && (
            <div className="mt-8 rounded-3xl border border-white/10 bg-[#0E121B]/90 p-8 text-center backdrop-blur-2xl shadow-2xl">
              <div className="text-4xl">🎉</div>
              <h2 className="mt-4 font-[var(--font-serif)] text-2xl font-bold text-white">
                Daily Quiz Complete!
              </h2>
              <p className="mt-2 text-sm text-slate-300">
                You scored <span className="font-bold text-[#D4A368] text-lg">{score}</span> out of{' '}
                <span className="font-bold text-white text-lg">{questions.length}</span>
              </p>

              <div className="mt-6 inline-flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.04] px-6 py-3 text-xs">
                <span className="text-amber-400">🔥 Current Streak: {stats.streak}</span>
                <span className="text-emerald-400">⭐ Quizzes Completed: {stats.quizzes_taken}</span>
              </div>

              <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
                <button
                  onClick={loadQuiz}
                  className="w-full sm:w-auto rounded-xl bg-gradient-to-r from-[#B8925A] via-[#C89B59] to-[#D4A368] px-6 py-2.5 text-xs font-bold text-slate-950 hover:brightness-110 transition-all cursor-pointer"
                >
                  Retake / Practice Again
                </button>
                <Link
                  href="/public/chat"
                  className="w-full sm:w-auto rounded-xl border border-white/15 bg-white/[0.05] px-6 py-2.5 text-xs font-semibold text-slate-200 hover:bg-white/[0.1] hover:text-white transition-all text-center no-underline"
                >
                  Return to AI Chat
                </Link>
              </div>
            </div>
          )}
        </div>
      </main>
      <Footer />
    </>
  )
}