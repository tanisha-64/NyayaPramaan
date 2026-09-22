'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { TopNav } from '@/components/layout/TopNav'
import { Footer } from '@/components/layout/Footer'
import { useAuth } from '@/hooks/useAuth'
import { getTodaysQuiz, QuizQuestion } from '@/services/quizService'

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
  const [loadFailed, setLoadFailed] = useState(false)

  useEffect(() => {
    if (!user) return
    getTodaysQuiz().then((q) => {
      setQuestions(q)
      setLoadFailed(q.length === 0)
    })
  }, [user])

  function retryLoad() {
    setLoadFailed(false)
    getTodaysQuiz().then((q) => {
      setQuestions(q)
      setLoadFailed(q.length === 0)
    })
  }

  function handleAnswer(index: number) {
    if (selected !== null) return
    setSelected(index)
    if (index === questions[current].correct_index) setScore((s) => s + 1)
  }

  function next() {
    if (current + 1 >= questions.length) { setFinished(true); return }
    setCurrent((c) => c + 1)
    setSelected(null)
  }

  if (authLoading || !user) {
    return (
      <>
        <TopNav />
        <main style={{ maxWidth: 700, margin: '0 auto', padding: '80px 20px', textAlign: 'center', color: 'rgba(247,245,240,0.5)' }}>
          Authenticating Daily Quiz...
        </main>
        <Footer />
      </>
    )
  }

  if (loadFailed) {
    return (
      <>
        <TopNav />
        <main style={{ maxWidth: 700, margin: '0 auto', padding: '80px 20px', textAlign: 'center' }}>
          <p style={{ color: 'rgba(247,245,240,0.5)' }}>Couldn't load today's quiz.</p>
          <button onClick={retryLoad} style={{ marginTop: 12, padding: '8px 16px', borderRadius: 6, border: 'none', background: '#B8925A', color: '#0A0A0B', cursor: 'pointer' }}>Retry</button>
        </main>
        <Footer />
      </>
    )
  }

  if (!questions.length) {
    return (
      <>
        <TopNav />
        <main style={{ maxWidth: 700, margin: '0 auto', padding: '80px 20px', textAlign: 'center', color: 'rgba(247,245,240,0.5)' }}>
          Loading today's quiz...
        </main>
        <Footer />
      </>
    )
  }

  if (finished) {
    return (
      <>
        <TopNav />
        <main style={{ maxWidth: 700, margin: '0 auto', padding: '80px 20px', textAlign: 'center' }}>
          <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 32 }}>Quiz Complete</h1>
          <p style={{ marginTop: 16, fontSize: 20, color: 'var(--color-gold)' }}>You scored {score} / {questions.length}</p>
        </main>
        <Footer />
      </>
    )
  }

  const q = questions[current]

  return (
    <>
      <TopNav />
      <main style={{ maxWidth: 700, margin: '0 auto', padding: '60px 20px' }}>
        <p style={{ fontSize: 12, color: 'rgba(247,245,240,0.4)', textTransform: 'uppercase', letterSpacing: 1 }}>
          Daily Legal Quiz — Question {current + 1} of {questions.length}
        </p>
        <h2 style={{ marginTop: 12, fontSize: 20 }}>{q.question}</h2>

        <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {q.options.map((opt, i) => {
            let bg = 'rgba(255,255,255,0.03)'
            if (selected !== null) {
              if (i === q.correct_index) bg = 'rgba(31,122,77,0.2)'
              else if (i === selected) bg = 'rgba(184,86,46,0.2)'
            }
            return (
              <button key={i} onClick={() => handleAnswer(i)} style={{
                textAlign: 'left', padding: '12px 16px', borderRadius: 8,
                border: '1px solid rgba(255,255,255,0.15)', background: bg,
                color: '#F7F5F0', cursor: selected === null ? 'pointer' : 'default', fontSize: 14,
              }}>
                {opt}
              </button>
            )
          })}
        </div>

        {selected !== null && (
          <div style={{ marginTop: 20, padding: 16, borderRadius: 8, background: 'rgba(255,255,255,0.03)' }}>
            <p style={{ fontSize: 13, color: 'rgba(247,245,240,0.7)' }}>{q.explanation}</p>
            {!q.judge_verified && (
              <p style={{ marginTop: 8, fontSize: 12, color: '#B8862E' }}>{q.caution_note}</p>
            )}
            <button onClick={next} style={{ marginTop: 16, padding: '8px 16px', borderRadius: 6, border: 'none', background: '#B8925A', color: '#0A0A0B', cursor: 'pointer' }}>
              {current + 1 >= questions.length ? 'Finish' : 'Next Question'}
            </button>
          </div>
        )}
      </main>
      <Footer />
    </>
  )
}