'use client'
import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { useIsMobile } from '@/hooks/useIsMobile'
import { useVoiceInput } from '@/hooks/useVoiceInput'
import { useVoiceOutput } from '@/hooks/useVoiceOutput'
import { uploadDocument, UploadResponse, getCaseStatus } from '@/services/documentService'
import { askQuestion, listSessions, getSessionMessages, renameSession, deleteSession, togglePin, deleteMessagesFrom, ChatSession, Source } from '@/services/chatService'
import { AnswerCard } from '@/components/chat/AnswerCard'
import { TypingIndicator } from '@/components/chat/TypingIndicator'
import { ChatSidebar } from '@/components/chat/ChatSidebar'
import { WizardModal } from '@/components/wizard/WizardModal'

type PramaanCard = {
  act: string
  section: string
  act_name?: string | null
  heading?: string | null
  quote?: string | null
  source_url?: string | null
  page?: number | null
  verified: boolean
}

type Message = {
  key: string
  id?: string
  role: 'user' | 'assistant'; content: string; attachedFileName?: string
  conclusion?: string; usefulness?: string; sources?: Source[]; pramaanCards?: PramaanCard[]
  qualityNote?: string; departmentSuggestion?: string | null
  verified?: boolean; verdictState?: string
}
type ActiveDoc = { caseId: string; fileName: string }

let keyCounter = 0
function makeKey(): string {
  keyCounter += 1
  return `m${Date.now()}_${keyCounter}`
}

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

function normalizeSources(sources: unknown): Source[] {
  if (!Array.isArray(sources)) return []
  return sources.map((value): Source => {
    if (typeof value === 'string') {
      return { name: value, type: 'document', url: null, verification_status: 'unverified', jurisdiction: null }
    }
    const source = value as Record<string, unknown>
    return {
      name: typeof source.name === 'string' ? source.name : 'Source',
      type: typeof source.type === 'string' ? source.type : 'document',
      url: typeof source.url === 'string' ? source.url : null,
      verification_status: typeof source.verification_status === 'string' ? source.verification_status : 'unverified',
      jurisdiction: typeof source.jurisdiction === 'string' ? source.jurisdiction : null,
      page: typeof source.page === 'number' ? source.page : null,
      section: typeof source.section === 'string' ? source.section : undefined,
      excerpt: typeof source.excerpt === 'string' ? source.excerpt : undefined,
    }
  })
}

/* ── Topic chips for welcome screen ── */
const TOPIC_CHIPS: { label: string; query: string; icon: string }[] = [
  { label: 'FIR kaise darj karein?', query: 'FIR kaise darj karein?', icon: '📋' },
  { label: 'Zero FIR kya hai?', query: 'Zero FIR kya hoti hai?', icon: '🔄' },
  { label: 'Bail kaise milti hai?', query: 'Bail kaise milti hai?', icon: '⚖️' },
  { label: 'Cheque bounce par kya karein?', query: 'Cheque bounce hone par kya karein?', icon: '💳' },
  { label: 'IPC 302 → BNS?', query: 'IPC 302 ab BNS me kaunsa section hai?', icon: '🔀' },
  { label: 'Arrest par rights', query: 'Arrest hone par mere kya rights hain?', icon: '🛡️' },
  { label: 'Online fraud ho gaya', query: 'Online fraud ho gaya, FIR kaise karein?', icon: '🌐' },
  { label: 'Dahej complaint', query: 'Dahej utpidan ki complaint kaise karein?', icon: '📝' },
]

const SUPPORTED_TOPICS = [
  'FIR / Zero FIR', 'Bail — regular, anticipatory, default', 'Arrest ke adhikar',
  'Cheque bounce (NI Act)', 'Murder, robbery, theft', 'Cheating, fraud, cyber fraud',
  'Kidnapping', 'Sexual offences', 'Dowry / 498A', 'Assault, hurt',
  'Dhamki, trespass, defamation', 'Drunk driving', 'IPC ↔ BNS mapping', 'Free legal aid',
]

export default function PublicChat() {
  const { user, loading: authLoading, signOut } = useAuth()
  const router = useRouter()
  const isMobile = useIsMobile()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [wizardOpen, setWizardOpen] = useState(false)

  useEffect(() => {
    if (!authLoading && !user) router.push('/login')
  }, [authLoading, user, router])

  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeSession, setActiveSession] = useState<string | null>(null)
  const [isTemporary, setIsTemporary] = useState(false)

  const [activeDoc, setActiveDoc] = useState<ActiveDoc | null>(null)
  const [uploadingFileName, setUploadingFileName] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [documentIndexing, setDocumentIndexing] = useState(false)

  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [editText, setEditText] = useState('')

  const fileInputRef = useRef<HTMLInputElement>(null)
  const { listening, startListening, micError } = useVoiceInput((text) => setQuery((prev) => (prev ? prev + ' ' + text : text)))
  const { speakingId, speak, speechError } = useVoiceOutput()

  useEffect(() => { if (user) refreshSessions() }, [user])

  useEffect(() => {
    if (!activeDoc || !documentIndexing) return

    let cancelled = false
    let timer: ReturnType<typeof setTimeout>
    let attempts = 0

    const checkStatus = async () => {
      try {
        const status = await getCaseStatus(activeDoc.caseId)
        if (cancelled) return
        if (status.status === 'ready') {
          setDocumentIndexing(false)
          return
        }
        if (status.status === 'failed') {
          setDocumentIndexing(false)
          setUploadError(status.rejection_reason || 'Document indexing failed. Please upload it again.')
          return
        }
        if (attempts++ >= 60) {
          setDocumentIndexing(false)
          setUploadError('Document indexing is taking longer than expected. Please wait a little and try again.')
          return
        }
        timer = setTimeout(checkStatus, 1500)
      } catch (error) {
        if (cancelled) return
        console.error('Could not check document indexing status:', error)
        setDocumentIndexing(false)
        setUploadError('Could not check document indexing status. Please try again.')
      }
    }

    void checkStatus()
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [activeDoc, documentIndexing])

  async function refreshSessions() {
    try {
      const list = await listSessions()
      setSessions(Array.isArray(list) ? list : [])
    } catch (err) { console.error(err) }
  }

  function handleNewChat() {
    setActiveSession(null); setMessages([]); setSuggestions([])
    setIsTemporary(false); setActiveDoc(null); setUploadError(null); setDocumentIndexing(false)
    setEditingKey(null); setEditText('')
  }

  function handleToggleTemporary() {
    const next = !isTemporary
    setIsTemporary(next)
    if (next) {
      setActiveSession(null); setMessages([]); setSuggestions([]); setActiveDoc(null); setDocumentIndexing(false)
    }
  }

  async function handleSelectSession(id: string) {
    setActiveSession(id); setIsTemporary(false); setUploadError(null)
    setEditingKey(null); setEditText('')
    try {
      const { messages: msgs, case_id, case_filename } = await getSessionMessages(id)
      setMessages(msgs.map((m) => ({
        key: m.id ?? makeKey(),
        id: m.id,
        role: m.role === 'user' ? 'user' : 'assistant',
        content: m.content,
        sources: normalizeSources(m.sources),
      })))
      setActiveDoc(case_id && case_filename ? { caseId: case_id, fileName: case_filename } : null)
      setSuggestions([])
    } catch (err) { console.error(err) }
  }

  async function handleRename(id: string, title: string) { await renameSession(id, title); refreshSessions() }
  async function handleTogglePin(id: string, pinned: boolean) { await togglePin(id, pinned); refreshSessions() }
  async function handleDelete(id: string) {
    await deleteSession(id)
    if (activeSession === id) { setActiveSession(null); setMessages([]) }
    refreshSessions()
  }

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadError(null)
    setDocumentIndexing(false)
    setUploadingFileName(file.name)
    try {
      const result: UploadResponse = await uploadDocument(file)
      setActiveDoc({ caseId: result.case_id, fileName: result.filename })
      setDocumentIndexing(result.status === 'processing')
    } catch (err: unknown) {
      setUploadError(getErrorMessage(err, "This document couldn't be processed. Please try a different legal document."))
    }
    setUploadingFileName(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  function clearActiveDocument() {
    setActiveDoc(null)
    setDocumentIndexing(false)
  }

  async function sendQuery(text: string) {
    if (!text.trim() || loading || documentIndexing) return
    const userKey = makeKey()

    setMessages((prev) => [...prev, { key: userKey, role: 'user', content: text, attachedFileName: activeDoc?.fileName }])
    setQuery(''); setSuggestions([]); setLoading(true)

    try {
      const result = await askQuestion(text, activeDoc?.caseId, activeSession ?? undefined, isTemporary)
      if (!isTemporary && result.session_id && result.session_id !== activeSession) {
        setActiveSession(result.session_id); refreshSessions()
      }
      setMessages((prev) => {
        const updated = prev.map((mm) => (mm.key === userKey ? { ...mm, id: result.user_message_id } : mm))
        updated.push({
          key: makeKey(),
          id: result.message_id,
          role: 'assistant', content: result.answer, conclusion: result.conclusion,
          usefulness: result.usefulness, sources: result.sources,
          pramaanCards: result.pramaan_cards,
          qualityNote: result.quality_note, departmentSuggestion: result.department_suggestion,
          verified: result.verified, verdictState: result.verdict_state,
        })
        return updated
      })
      setSuggestions(result.suggestions || [])
    } catch (err: unknown) {
      setMessages((prev) => [...prev, { key: makeKey(), role: 'assistant', content: getErrorMessage(err, 'Something went wrong. Please try again.') }])
    }
    setLoading(false)
  }

  function startEdit(key: string, content: string) {
    setEditingKey(key)
    setEditText(content)
  }

  function cancelEdit() {
    setEditingKey(null)
    setEditText('')
  }

  async function saveEdit(key: string) {
    const msg = messages.find((mm) => mm.key === key)
    const text = editText.trim()
    if (!msg || !text) return
    setEditingKey(null)
    setEditText('')
    if (msg.id && activeSession) {
      try { await deleteMessagesFrom(activeSession, msg.id) } catch (err) { console.error(err) }
    }
    setMessages((prev) => {
      const idx = prev.findIndex((mm) => mm.key === key)
      return idx === -1 ? prev : prev.slice(0, idx)
    })
    await sendQuery(text)
  }

  const showWelcome = messages.length === 0 && !loading
  const [showTopics, setShowTopics] = useState(false)

  if (authLoading || !user) {
    return <div style={{ height: '100vh', background: '#0A0A0B', color: '#F7F5F0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Loading...</div>
  }

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: '#0A0A0B', color: '#F7F5F0', fontFamily: 'sans-serif' }}>
      <ChatSidebar sessions={sessions} activeId={activeSession} onSelect={handleSelectSession}
        onNew={handleNewChat} onRename={handleRename} onDelete={handleDelete} onTogglePin={handleTogglePin}
        onLogout={signOut} isMobile={isMobile} mobileOpen={sidebarOpen} onCloseMobile={() => setSidebarOpen(false)} />

      <main style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        <div style={{ flexShrink: 0, borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
          <div style={{ maxWidth: 700, margin: '0 auto', padding: '20px 20px 16px', display: 'flex', flexWrap: 'wrap', rowGap: 10, justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', minWidth: 0 }}>
              {isMobile && (
                <button onClick={() => setSidebarOpen(true)} title="Menu" style={{ flexShrink: 0, background: 'none', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 8, color: '#F7F5F0', cursor: 'pointer', fontSize: 16, padding: '4px 8px' }}>☰</button>
              )}
              <div style={{ minWidth: 0 }}>
                <h1 style={{ fontSize: 20, margin: 0 }}>NyayaPramaan — Ask a Legal Question</h1>
                <p style={{ color: 'rgba(247,245,240,0.5)', fontSize: 12, marginTop: 4 }}>
                  General legal information, not professional advice. English, Hindi, or Hinglish.
                </p>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', flexWrap: 'wrap' }}>
              <button onClick={() => setShowTopics((v) => !v)} title="Supported topics dekhein" style={{
                fontSize: 11, padding: '6px 10px', borderRadius: 16, whiteSpace: 'nowrap',
                border: '1px solid rgba(184,146,90,0.4)', background: showTopics ? 'rgba(184,146,90,0.15)' : 'transparent',
                color: '#B8925A', cursor: 'pointer',
              }}>
                📚 Topics
              </button>
              <button onClick={handleToggleTemporary} title="Temporary chats are never saved" style={{
                fontSize: 11, padding: '6px 10px', borderRadius: 16, whiteSpace: 'nowrap',
                border: `1px solid ${isTemporary ? '#B8862E' : 'rgba(255,255,255,0.2)'}`,
                background: isTemporary ? 'rgba(184,134,46,0.15)' : 'transparent',
                color: isTemporary ? '#B8862E' : 'rgba(247,245,240,0.6)', cursor: 'pointer',
              }}>
                {isTemporary ? '⏳ Temporary Chat ON' : '⏳ Temporary Chat'}
              </button>
            </div>
          </div>
          {showTopics && (
            <div style={{ maxWidth: 700, margin: '0 auto', padding: '0 20px 12px' }}>
              <div style={{ padding: '12px 16px', borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}>
                <p style={{ fontSize: 11, fontWeight: 600, color: 'rgba(247,245,240,0.5)', marginBottom: 8, textTransform: 'uppercase' }}>Ye topics supported hain</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                  {SUPPORTED_TOPICS.map((t, i) => (
                    <span key={i} style={{ fontSize: 11, padding: '3px 9px', borderRadius: 10, background: 'rgba(255,255,255,0.06)', color: 'rgba(247,245,240,0.55)' }}>{t}</span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        <div style={{ flex: 1, overflowY: 'auto' }}>
          <div style={{ maxWidth: 700, margin: '0 auto', padding: '16px 20px' }}>

            {/* ── Welcome Screen ── */}
            {showWelcome && (
              <div style={{ textAlign: 'center', paddingTop: 40, paddingBottom: 20 }}>
                <div style={{ fontSize: 40, marginBottom: 12 }}>⚖️</div>
                <h2 style={{ fontSize: 22, fontWeight: 600, margin: '0 0 8px' }}>Namaste! Kya poochhna hai?</h2>
                <p style={{ color: 'rgba(247,245,240,0.55)', fontSize: 13, maxWidth: 480, margin: '0 auto 24px' }}>
                  Police, FIR aur Criminal Law se related koi bhi sawal poochho — Hindi, English ya Hinglish me.
                  Hum BNS, BNSS, BSA, IPC, CrPC aur NI Act ke official text se verified jawab dete hain.
                </p>

                {/* Example question chips */}
                <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 8, marginBottom: 28 }}>
                  {TOPIC_CHIPS.map((chip, i) => (
                    <button key={i} onClick={() => sendQuery(chip.query)} style={{
                      fontSize: 12, padding: '8px 14px', borderRadius: 20,
                      border: '1px solid rgba(184,146,90,0.35)', background: 'rgba(184,146,90,0.08)',
                      color: 'rgba(247,245,240,0.8)', cursor: 'pointer',
                      transition: 'background 0.15s, border-color 0.15s',
                    }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(184,146,90,0.18)'; e.currentTarget.style.borderColor = 'rgba(184,146,90,0.5)' }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(184,146,90,0.08)'; e.currentTarget.style.borderColor = 'rgba(184,146,90,0.35)' }}
                    >
                      {chip.icon} {chip.label}
                    </button>
                  ))}
                </div>

                {/* Supported topics */}
                <div style={{ textAlign: 'left', maxWidth: 480, margin: '0 auto', padding: '16px 20px', borderRadius: 12, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}>
                  <p style={{ fontSize: 12, fontWeight: 600, color: 'rgba(247,245,240,0.6)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    Supported Topics
                  </p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {SUPPORTED_TOPICS.map((t, i) => (
                      <span key={i} style={{ fontSize: 11, padding: '4px 10px', borderRadius: 12, background: 'rgba(255,255,255,0.06)', color: 'rgba(247,245,240,0.55)' }}>
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {messages.map((m) => (
              <div key={m.key} style={{ marginBottom: 20, textAlign: m.role === 'user' ? 'right' : 'left' }}>
                {m.role === 'user' ? (
                  <div style={{ display: 'inline-block', maxWidth: '85%', textAlign: 'right' }}>
                    {m.attachedFileName && (
                      <div style={{ marginBottom: 6, display: 'flex', justifyContent: 'flex-end' }}>
                        <span style={{ fontSize: 11, padding: '3px 10px', borderRadius: 12, background: 'rgba(43,92,224,0.15)', color: '#5B8CFF' }}>
                          📄 {m.attachedFileName}
                        </span>
                      </div>
                    )}
                    {editingKey === m.key ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-end' }}>
                        <textarea
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          rows={2}
                          autoFocus
                          style={{ width: '100%', maxWidth: 280, padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(184,146,90,0.4)', background: 'rgba(255,255,255,0.05)', color: '#F7F5F0', resize: 'vertical', boxSizing: 'border-box' }}
                        />
                        <div style={{ display: 'flex', gap: 6 }}>
                          <button onClick={cancelEdit} style={{ fontSize: 11, padding: '4px 10px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.2)', background: 'transparent', color: 'rgba(247,245,240,0.7)', cursor: 'pointer' }}>Cancel</button>
                          <button onClick={() => saveEdit(m.key)} style={{ fontSize: 11, padding: '4px 10px', borderRadius: 6, border: 'none', background: '#B8925A', color: '#0A0A0B', cursor: 'pointer' }}>Save & Resend</button>
                        </div>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end' }}>
                        <button onClick={() => startEdit(m.key, m.content)} title="Edit & resend" style={{ background: 'none', border: 'none', color: 'rgba(247,245,240,0.35)', cursor: 'pointer', fontSize: 13 }}>✏️</button>
                        <div style={{ padding: '10px 14px', borderRadius: 10, background: '#2B5CE0', fontSize: 14, textAlign: 'left', wordBreak: 'break-word' }}>
                          {m.content}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ display: 'inline-block', maxWidth: '100%', textAlign: 'left' }}>
                    <button onClick={() => speak(m.key, m.content)} title="Listen to this answer" style={{ marginBottom: 4, background: 'none', border: 'none', color: speakingId === m.key ? '#B8862E' : 'rgba(247,245,240,0.4)', cursor: 'pointer', fontSize: 13 }}>
                      {speakingId === m.key ? '🔊 Stop' : '🔈 Listen'}
                    </button>
                    <AnswerCard
                      answer={m.content}
                      conclusion={m.conclusion}
                      usefulness={m.usefulness}
                      sources={m.sources}
                      pramaanCards={m.pramaanCards}
                      qualityNote={m.qualityNote}
                      departmentSuggestion={m.departmentSuggestion}
                      verified={m.verified}
                      verdictState={m.verdictState}
                    />
                  </div>
                )}
              </div>
            ))}
            {loading && <TypingIndicator />}
            {suggestions.length > 0 && !loading && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
                {suggestions.map((s, i) => (
                  <button key={i} onClick={() => sendQuery(s)} style={{ fontSize: 12, padding: '6px 12px', borderRadius: 16, border: '1px solid rgba(255,255,255,0.2)', background: 'transparent', color: 'rgba(247,245,240,0.7)', cursor: 'pointer' }}>
                    {s}
                  </button>
                ))}
              </div>
            )}
            {!showWelcome && !loading && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 12, paddingBottom: 8 }}>
                {TOPIC_CHIPS.slice(0, 4).map((chip, i) => (
                  <button key={i} onClick={() => sendQuery(chip.query)} style={{
                    fontSize: 11, padding: '5px 10px', borderRadius: 14,
                    border: '1px solid rgba(255,255,255,0.1)', background: 'transparent',
                    color: 'rgba(247,245,240,0.45)', cursor: 'pointer',
                  }}>
                    {chip.icon} {chip.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div style={{ flexShrink: 0, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
          <div style={{ maxWidth: 700, margin: '0 auto', padding: '10px 20px 0' }}>
            {activeDoc && (
              <div style={{ marginBottom: 8, display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 6, padding: '6px 12px', borderRadius: 8, background: 'rgba(43,92,224,0.08)', border: '1px solid rgba(43,92,224,0.2)' }}>
                <span style={{ fontSize: 12, color: '#5B8CFF', wordBreak: 'break-word' }}>💬 Continuing conversation about: {activeDoc.fileName}</span>
                <button onClick={clearActiveDocument} title="Stop referencing this document" style={{ background: 'none', border: 'none', color: 'rgba(247,245,240,0.5)', cursor: 'pointer', fontSize: 13, flexShrink: 0 }}>✕</button>
              </div>
            )}

            {uploadingFileName && (
              <div style={{ marginBottom: 8, padding: '6px 12px', borderRadius: 8, background: 'rgba(255,255,255,0.05)', fontSize: 12, color: 'rgba(247,245,240,0.6)' }}>
                📄 Uploading & reading {uploadingFileName}...
              </div>
            )}

            {documentIndexing && (
              <div role="status" style={{ marginBottom: 8, padding: '6px 12px', borderRadius: 8, background: 'rgba(43,92,224,0.08)', border: '1px solid rgba(43,92,224,0.2)', fontSize: 12, color: '#8CAEFF' }}>
                📄 Indexing document pages for follow-up questions...
              </div>
            )}

            {uploadError && (
              <div style={{ marginBottom: 8, padding: '6px 12px', borderRadius: 8, background: 'rgba(224,106,71,0.1)', border: '1px solid rgba(224,106,71,0.3)', fontSize: 12, color: '#E06A47', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                <span>⚠️ {uploadError}</span>
                <button onClick={() => setUploadError(null)} title="Dismiss" style={{ background: 'none', border: 'none', color: '#E06A47', cursor: 'pointer', fontSize: 13, flexShrink: 0 }}>✕</button>
              </div>
            )}

            {micError && (
              <div style={{ marginBottom: 8, padding: '6px 12px', borderRadius: 8, background: 'rgba(224,106,71,0.1)', border: '1px solid rgba(224,106,71,0.3)', fontSize: 12, color: '#E06A47' }}>
                🎤 {micError}
              </div>
            )}

            {speechError && (
              <div style={{ marginBottom: 8, padding: '6px 12px', borderRadius: 8, background: 'rgba(224,106,71,0.1)', border: '1px solid rgba(224,106,71,0.3)', fontSize: 12, color: '#E06A47' }}>
                🔊 {speechError}
              </div>
            )}
          </div>

          <div style={{ maxWidth: 700, margin: '0 auto', padding: '0 20px 20px', display: 'flex', gap: 8 }}>
            <input ref={fileInputRef} type="file" accept=".pdf" onChange={handleFileSelect} style={{ display: 'none' }} />
            <button onClick={() => fileInputRef.current?.click()} disabled={!!uploadingFileName} title="Attach a document" style={{ flexShrink: 0, padding: isMobile ? '10px 10px' : '10px 14px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.15)', background: 'transparent', color: '#F7F5F0', cursor: 'pointer' }}>
              {uploadingFileName ? '...' : '📎'}
            </button>
            <button onClick={startListening} disabled={loading} title="Voice input" style={{
              flexShrink: 0, padding: isMobile ? '10px 10px' : '10px 14px', borderRadius: 8,
              border: `1px solid ${listening ? '#B8862E' : 'rgba(255,255,255,0.15)'}`,
              background: listening ? 'rgba(184,134,46,0.15)' : 'transparent', color: '#F7F5F0', cursor: 'pointer',
            }}>
              {listening ? '🔴' : '🎤'}
            </button>
            <button onClick={() => setWizardOpen(true)} title="Guided help (FIR, bail, cheque bounce, scam check)" style={{
              flexShrink: 0, padding: isMobile ? '10px 10px' : '10px 14px', borderRadius: 8,
              border: '1px solid rgba(255,255,255,0.15)', background: 'transparent', color: '#F7F5F0', cursor: 'pointer',
            }}>
              🧭
            </button>
            <textarea
              value={query}
              disabled={documentIndexing}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  if (!loading) sendQuery(query)
                }
              }}
              rows={1}
              placeholder="Ask a legal question..."
              style={{ flex: 1, minWidth: 0, padding: '10px 14px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.03)', color: '#F7F5F0', resize: 'none', boxSizing: 'border-box' }}
            />
            <button onClick={() => sendQuery(query)} disabled={loading || documentIndexing} style={{ flexShrink: 0, padding: isMobile ? '10px 12px' : '10px 18px', borderRadius: 8, border: 'none', background: '#B8925A', color: '#0A0A0B', fontWeight: 500, cursor: loading || documentIndexing ? 'default' : 'pointer', opacity: loading || documentIndexing ? 0.6 : 1 }}>
              Ask
            </button>
          </div>
        </div>
      </main>

      <WizardModal open={wizardOpen} onClose={() => setWizardOpen(false)} />
    </div>
  )
}