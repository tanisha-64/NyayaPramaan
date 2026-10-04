'use client'
import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import { useVoiceInput } from '@/hooks/useVoiceInput'
import { uploadDocument, getCaseStatus, deleteDocument, UploadResponse, validateFileType } from '@/services/documentService'
import { askQuestion, listSessions, getSessionMessages, renameSession, deleteSession, togglePin, LegalClaim, VerificationSummary, LegalSource } from '@/services/chatService'
import { AnswerCard } from '@/components/chat/AnswerCard'
import { TypingIndicator } from '@/components/chat/TypingIndicator'
import { ChatSidebar } from '@/components/chat/ChatSidebar'
import { AttachmentComposerCard, ComposerDoc } from '@/components/chat/AttachmentComposerCard'
import { AttachmentMessageCard } from '@/components/chat/AttachmentMessageCard'
import { SourceDetailModal } from '@/components/chat/SourceDetailModal'

type Message = {
  role: 'user' | 'assistant'
  content: string
  attachedFiles?: { fileName: string; pageCount?: number }[]
  conclusion?: string
  usefulness?: string
  sources?: LegalSource[]
  claims?: LegalClaim[]
  verificationSummary?: VerificationSummary
  qualityNote?: string
  departmentSuggestion?: string | null
  confidenceScore?: number
  isError?: boolean
  mode?: 'professional' | 'student' | 'citizen'
}

type StoredSession = {
  id: string
  title: string
  created_at: string
  updated_at: string
  pinned?: boolean
}

const STARTER_PROMPTS = [
  {
    title: "Bharatiya Nyaya Sanhita (BNS)",
    desc: "Compare Section 106 of BNS vs Section 304A IPC for medical negligence.",
    icon: "📜",
  },
  {
    title: "Bail & Criminal Procedure",
    desc: "What are the mandatory grounds for regular bail under Section 437/439 CrPC?",
    icon: "⚖️",
  },
  {
    title: "Document Analysis & Contract Review",
    desc: "Attach your legal case file (PDF, DOCX, scan) to extract clauses, timeline, and precedent citations.",
    icon: "📄",
  },
]

export default function LegalChatPage() {
  const { user, signOut } = useAuth()

  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [isSessionLoading, setIsSessionLoading] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [sessions, setSessions] = useState<StoredSession[]>([])
  const [activeSession, setActiveSession] = useState<string | null>(null)
  const [isTemporary, setIsTemporary] = useState(false)
  const [personaMode, setPersonaMode] = useState<'professional' | 'student' | 'citizen'>('professional')

  // In-composer attached documents (displayed inside composer before send)
  const [composerDocs, setComposerDocs] = useState<ComposerDoc[]>([])
  const [composerNotice, setComposerNotice] = useState<string | null>(null)

  // Selected citation for modal inspection
  const [selectedSource, setSelectedSource] = useState<LegalSource | null>(null)

  // Abort controller for stopping generation
  const queryAbortController = useRef<AbortController | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Voice speech input
  const handleVoiceResult = useCallback((text: string) => {
    setQuery((prev) => {
      const clean = prev.trim()
      return clean ? `${clean} ${text}` : text
    })
  }, [])

  const { listening, toggleListening, interimText } = useVoiceInput(handleVoiceResult)

  // Local storage storage key for sessions
  const userStorageKey = useMemo(() => `np_sessions_${user?.id || 'guest_user'}`, [user?.id])

  // Save session list to local storage
  const saveLocalSessions = useCallback((newSessions: StoredSession[]) => {
    if (typeof window === 'undefined') return
    try {
      localStorage.setItem(userStorageKey, JSON.stringify(newSessions))
    } catch {}
  }, [userStorageKey])

  // Save messages for a session to local storage
  const saveLocalMessages = useCallback((sessionId: string, msgs: Message[]) => {
    if (typeof window === 'undefined' || !sessionId) return
    try {
      localStorage.setItem(`np_msgs_${sessionId}`, JSON.stringify(msgs))
    } catch {}
  }, [])

  // Load sessions from local storage + backend
  const refreshSessions = useCallback(async () => {
    let localList: StoredSession[] = []
    if (typeof window !== 'undefined') {
      try {
        const raw = localStorage.getItem(userStorageKey)
        if (raw) localList = JSON.parse(raw)
      } catch {}
    }

    try {
      const cloudList = await listSessions()
      if (Array.isArray(cloudList) && cloudList.length > 0) {
        // Merge cloud with local, avoiding duplicates
        const cloudIds = new Set(cloudList.map((s) => s.id))
        const merged = [...cloudList, ...localList.filter((s) => !cloudIds.has(s.id))]
        setSessions(merged)
        saveLocalSessions(merged)
        return
      }
    } catch (err) {
      console.warn('Cloud session list notice:', err)
    }

    setSessions(localList)
  }, [userStorageKey, saveLocalSessions])

  useEffect(() => {
    refreshSessions()
  }, [user, refreshSessions])

  const scrollToBottom = useCallback(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: messagesContainerRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [])

  useEffect(() => {
    if (messages.length > 0 || loading) {
      scrollToBottom()
    }
  }, [messages.length, loading, scrollToBottom])

  // Polling for processing documents
  useEffect(() => {
    const processing = composerDocs.filter(
      (d) => d.status === 'uploading' || d.status === 'processing' || d.status === 'ocr' || d.status === 'indexing'
    )
    if (!processing.length) return

    const interval = setInterval(async () => {
      for (const doc of processing) {
        try {
          const s = await getCaseStatus(doc.caseId)
          setComposerDocs((prev) =>
            prev.map((d) => {
              if (d.caseId !== doc.caseId) return d
              const statusVal = (s.status || 'ready') as any
              return {
                ...d,
                status: statusVal === 'ready' ? 'ready' : statusVal === 'rejected' ? 'rejected' : 'indexing',
                pagesProcessed: s.pages_processed ?? d.pagesProcessed,
                totalPages: s.total_pages ?? d.totalPages,
                rejectionReason: s.rejection_reason || undefined,
              }
            })
          )
          if (s.status === 'rejected' && s.rejection_reason) {
            setComposerNotice(`Document Rejected: ${s.rejection_reason}`)
          }
        } catch {
          // ignore transient polling error
        }
      }
    }, 1500)

    return () => clearInterval(interval)
  }, [composerDocs])

  function handleNewChat() {
    setActiveSession(null)
    setMessages([])
    setSuggestions([])
    setIsTemporary(false)
    setComposerDocs([])
    setComposerNotice(null)
    setIsSessionLoading(false)
  }

  function handleToggleTemporary() {
    const next = !isTemporary
    setIsTemporary(next)
    if (next) {
      setActiveSession(null)
      setMessages([])
      setSuggestions([])
      setComposerDocs([])
      setComposerNotice(null)
    }
  }

  async function handleSelectSession(id: string) {
    if (activeSession === id && !isSessionLoading) return
    setActiveSession(id)
    setIsTemporary(false)
    setComposerNotice(null)
    setIsSessionLoading(true)

    // Check local storage first for instant load
    let localMsgs: Message[] = []
    if (typeof window !== 'undefined') {
      try {
        const raw = localStorage.getItem(`np_msgs_${id}`)
        if (raw) localMsgs = JSON.parse(raw)
      } catch {}
    }

    if (localMsgs.length > 0) {
      setMessages(localMsgs)
    }

    try {
      const { messages: msgs } = await getSessionMessages(id)
      if (msgs && msgs.length > 0) {
        const loaded: Message[] = msgs.map((m: any) => ({
          role: m.role,
          content: m.content,
          sources: m.sources,
        }))
        setMessages(loaded)
        saveLocalMessages(id, loaded)
      }
      setSuggestions([])
    } catch (err) {
      console.warn('Backend loadSession notice:', err)
    } finally {
      setIsSessionLoading(false)
    }
  }

  async function handleRename(id: string, title: string) {
    if (!title.trim()) return
    const updated = sessions.map((s) => (s.id === id ? { ...s, title: title.trim(), updated_at: new Date().toISOString() } : s))
    setSessions(updated)
    saveLocalSessions(updated)
    try {
      await renameSession(id, title.trim())
    } catch {}
  }

  async function handleTogglePin(id: string, pinned: boolean) {
    const updated = sessions
      .map((s) => (s.id === id ? { ...s, pinned } : s))
      .sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0))
    setSessions(updated)
    saveLocalSessions(updated)
    try {
      await togglePin(id, pinned)
    } catch {}
  }

  async function handleDelete(id: string) {
    const updated = sessions.filter((s) => s.id !== id)
    setSessions(updated)
    saveLocalSessions(updated)
    if (typeof window !== 'undefined') {
      try { localStorage.removeItem(`np_msgs_${id}`) } catch {}
    }
    if (activeSession === id) {
      setActiveSession(null)
      setMessages([])
      setComposerDocs([])
    }
    try {
      await deleteSession(id)
    } catch {}
  }

  // Handle File Selection
  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || [])
    if (!files.length) return
    setComposerNotice(null)

    for (const file of files) {
      const validationError = validateFileType(file)
      if (validationError) {
        setComposerNotice(validationError)
        continue
      }

      const tempId = `doc_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
      const newDoc: ComposerDoc = {
        caseId: tempId,
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type,
        status: 'uploading',
        progress: 10,
      }

      setComposerDocs((prev) => [...prev, newDoc])

      try {
        const result: UploadResponse = await uploadDocument(file)
        setComposerDocs((prev) =>
          prev.map((d) =>
            d.caseId === tempId
              ? {
                  ...d,
                  caseId: result.case_id,
                  status: 'indexing',
                  progress: 100,
                  totalPages: result.total_pages || d.totalPages || 1,
                }
              : d
          )
        )
      } catch (err: any) {
        const errorMsg = err?.message || 'Failed to upload document.'
        setComposerDocs((prev) =>
          prev.map((d) =>
            d.caseId === tempId
              ? { ...d, status: 'failed', errorMessage: errorMsg }
              : d
          )
        )
        setComposerNotice(`Upload failed for "${file.name}": ${errorMsg}`)
      }
    }

    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  function handleRemoveComposerDoc(caseId: string) {
    setComposerDocs((prev) => prev.filter((d) => d.caseId !== caseId))
    deleteDocument(caseId).catch(() => {})
  }

  // Document processing state checks
  const isAnyDocBusy = composerDocs.some(
    (d) => d.status === 'uploading' || d.status === 'processing' || d.status === 'ocr' || d.status === 'indexing'
  )
  const hasRejectedDoc = composerDocs.some((d) => d.status === 'rejected')

  // Submit Query + Attached Documents
  async function sendQuery(textToSend?: string) {
    const text = (textToSend ?? query).trim()
    if (!text || loading) return

    setComposerNotice(null)

    // Block submission if document is still indexing
    if (isAnyDocBusy) {
      setComposerNotice('Document is still indexing pages. Please wait until status is Ready before sending.')
      return
    }

    if (hasRejectedDoc) {
      setComposerNotice('Please remove rejected non-legal files before sending your legal question.')
      return
    }

    // Capture ready documents for this message
    const attachedForMessage = composerDocs.map((d) => ({
      fileName: d.fileName,
      pageCount: d.totalPages || 1,
    }))
    const activeCaseIds = composerDocs.filter((d) => d.status === 'ready').map((d) => d.caseId)

    const userMessage: Message = {
      role: 'user',
      content: text,
      attachedFiles: attachedForMessage.length ? attachedForMessage : undefined,
    }

    const updatedMessages = [...messages, userMessage]
    setMessages(updatedMessages)

    // Clear composer input and composer attachments
    setQuery('')
    setComposerDocs([])
    setSuggestions([])
    setLoading(true)

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    // Determine or generate current session ID
    let currentSessionId = activeSession
    if (!currentSessionId && !isTemporary) {
      currentSessionId = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
      setActiveSession(currentSessionId)

      // Add to session list immediately
      const newSession: StoredSession = {
        id: currentSessionId,
        title: text.length > 38 ? `${text.slice(0, 35)}...` : text,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }
      const newSessionList = [newSession, ...sessions]
      setSessions(newSessionList)
      saveLocalSessions(newSessionList)
    }

    if (currentSessionId && !isTemporary) {
      saveLocalMessages(currentSessionId, updatedMessages)
    }

    queryAbortController.current = new AbortController()

    try {
      const result = await askQuestion(
        text,
        activeCaseIds,
        currentSessionId ?? undefined,
        isTemporary,
        personaMode
      )

      const assistantMessage: Message = {
        role: 'assistant',
        content: result.answer,
        conclusion: result.conclusion,
        usefulness: result.usefulness,
        sources: result.sources,
        claims: result.claims,
        verificationSummary: result.verification_summary,
        qualityNote: result.quality_note,
        departmentSuggestion: result.department_suggestion,
        mode: personaMode,
      }

      const finalMessages = [...updatedMessages, assistantMessage]
      setMessages(finalMessages)

      if (currentSessionId && !isTemporary) {
        saveLocalMessages(currentSessionId, finalMessages)

        // Update session title if first message
        if (messages.length === 0) {
          const autoTitle = text.length > 38 ? `${text.slice(0, 35)}...` : text
          const updatedSessions = sessions.map((s) =>
            s.id === currentSessionId ? { ...s, title: autoTitle, updated_at: new Date().toISOString() } : s
          )
          setSessions(updatedSessions)
          saveLocalSessions(updatedSessions)
        }
      }

      setSuggestions(result.suggestions || [])
    } catch (err: any) {
      if (err?.name !== 'AbortError') {
        const errorMsg: Message = {
          role: 'assistant',
          content: 'Unable to connect to the legal AI gateway. Please ensure the backend server is active and try again.',
          isError: true,
        }
        const errorMessages = [...updatedMessages, errorMsg]
        setMessages(errorMessages)
        if (currentSessionId && !isTemporary) {
          saveLocalMessages(currentSessionId, errorMessages)
        }
      }
    } finally {
      setLoading(false)
      queryAbortController.current = null
    }
  }

  function handleStopGeneration() {
    if (queryAbortController.current) {
      queryAbortController.current.abort()
      queryAbortController.current = null
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (isAnyDocBusy) {
        setComposerNotice('Document is still indexing pages. Please wait until status is Ready before sending.')
        return
      }
      sendQuery()
    }
  }

  const activeDocCount = composerDocs.length

  return (
    <div className="citizen-chat-shell relative flex h-screen w-full overflow-hidden text-slate-100 font-sans antialiased bg-[#07090E]">
      {/* Background Ambience Orbs */}
      <div className="bloom-orb-citizen-1 opacity-25" />
      <div className="bloom-orb-citizen-2 opacity-25" />

      {/* ChatGPT-Style Sidebar */}
      <ChatSidebar
        sessions={sessions}
        activeId={activeSession}
        mode={personaMode}
        onSelect={handleSelectSession}
        onNew={handleNewChat}
        onRename={handleRename}
        onDelete={handleDelete}
        onTogglePin={handleTogglePin}
        onModeChange={setPersonaMode}
        onLogout={signOut}
      />

      {/* Main Legal Workspace */}
      <main className="relative flex flex-1 flex-col h-full overflow-hidden bg-transparent">
        {/* Top Header Bar */}
        <header className="flex-shrink-0 border-b border-white/[0.08] bg-[#0A0D14]/90 backdrop-blur-2xl z-10">
          <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-3.5">
            <div className="flex items-center gap-3">
              <Link
                href="/"
                className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.04] px-2.5 py-1.5 text-xs text-slate-300 hover:bg-white/[0.08] hover:text-white transition-all font-medium"
                title="Return to Main Portal"
              >
                <span>←</span>
                <span className="hidden sm:inline">Portal Home</span>
              </Link>

              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-[#B8925A]/30 via-blue-600/20 to-indigo-600/20 border border-[#B8925A]/30 text-sm shadow-inner font-bold">
                ⚖️
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-sm font-semibold tracking-tight text-white">
                    NyayaPramaan Legal Assistant
                  </h1>
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/25 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse-dot" />
                    Strict Legal Domain
                  </span>
                </div>
                <p className="text-[11px] text-[#B8925A]/80 font-medium">
                  {activeDocCount > 0
                    ? `Context: ${activeDocCount} Document${activeDocCount > 1 ? 's' : ''} Attached in Composer`
                    : 'Context: Indian Statutes (BNS / IPC / CrPC / BSA) & Supreme Court Precedents'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="hidden md:flex items-center gap-1.5 mr-2">
                <Link
                  href="/quiz"
                  className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-2.5 py-1 text-[11px] font-medium text-amber-300 hover:bg-amber-500/20 transition-all"
                >
                  🎯 Quiz
                </Link>
                <Link
                  href="/game"
                  className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-300 hover:bg-emerald-500/20 transition-all"
                >
                  🎮 Rights Game
                </Link>
                <Link
                  href="/news"
                  className="rounded-lg border border-blue-500/20 bg-blue-500/10 px-2.5 py-1 text-[11px] font-medium text-blue-300 hover:bg-blue-500/20 transition-all"
                >
                  📰 News
                </Link>
              </div>

              <button
                onClick={handleToggleTemporary}
                title="Temporary sessions are never saved"
                className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-all cursor-pointer border ${
                  isTemporary
                    ? 'border-amber-500/40 bg-amber-500/15 text-amber-300 shadow-sm'
                    : 'border-white/10 bg-white/[0.04] text-slate-300 hover:border-white/20 hover:text-white'
                }`}
              >
                <span>{isTemporary ? '⏳ Incognito Active' : '⏳ Incognito'}</span>
              </button>
            </div>
          </div>
        </header>

        {/* Conversation Message Stream */}
        <div ref={messagesContainerRef} className="flex-1 overflow-y-auto px-4 py-6 md:px-6">
          <div className="mx-auto max-w-3xl space-y-6">
            {isSessionLoading ? (
              <div className="my-16 flex flex-col items-center justify-center text-center">
                <div className="flex items-center gap-3 text-sm text-slate-400">
                  <span className="h-2.5 w-2.5 rounded-full bg-[#B8925A] animate-pulse-dot" />
                  <span>Loading legal session history...</span>
                </div>
              </div>
            ) : messages.length === 0 ? (
              <div className="my-8 flex flex-col items-center justify-center text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-gradient-to-tr from-[#B8925A]/30 via-blue-600/20 to-indigo-600/20 border border-[#B8925A]/30 text-3xl shadow-2xl">
                  ⚖️
                </div>
                <h2 className="mt-5 text-2xl font-semibold tracking-tight text-white">
                  Evidence-Oriented Legal Intelligence
                </h2>
                <p className="mt-2 max-w-lg text-xs text-slate-400 leading-relaxed">
                  Strictly dedicated to Indian legal research, statutory codes (BNS, IPC, CrPC, CPC), case analysis, and document reasoning with verified citations.
                </p>

                {/* Starter Prompts */}
                <div className="mt-8 grid w-full gap-3 sm:grid-cols-3 text-left">
                  {STARTER_PROMPTS.map((p, idx) => (
                    <button
                      key={idx}
                      onClick={() => sendQuery(p.desc)}
                      className="group flex flex-col justify-between rounded-2xl border border-white/10 bg-[#0E121B]/80 p-4 transition-all hover:border-[#B8925A]/50 hover:bg-[#B8925A]/[0.08] hover:shadow-xl cursor-pointer"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-xl">{p.icon}</span>
                        <span className="text-xs font-semibold text-white group-hover:text-[#D4A368] transition-colors">
                          {p.title}
                        </span>
                      </div>
                      <p className="mt-2.5 text-[11px] text-slate-400 leading-relaxed group-hover:text-slate-300 transition-colors">
                        {p.desc}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {/* Messages Feed */}
            {messages.map((m, idx) => (
              <div key={idx} className="space-y-3 animate-fadeIn">
                {m.role === 'user' ? (
                  <div className="flex flex-col items-end gap-2">
                    {/* Attached files inside message */}
                    {m.attachedFiles && m.attachedFiles.length > 0 && (
                      <div className="flex flex-wrap gap-2 justify-end">
                        {m.attachedFiles.map((af, fIdx) => (
                          <AttachmentMessageCard
                            key={fIdx}
                            fileName={af.fileName}
                            pageCount={af.pageCount}
                          />
                        ))}
                      </div>
                    )}

                    {/* User Text Bubble */}
                    <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-3 text-sm text-white shadow-md leading-relaxed whitespace-pre-wrap font-medium">
                      {m.content}
                    </div>
                  </div>
                ) : (
                  <div className="flex w-full items-start gap-3">
                    <AnswerCard
                      answer={m.content}
                      conclusion={m.conclusion}
                      usefulness={m.usefulness}
                      sources={m.sources}
                      claims={m.claims}
                      verificationSummary={m.verificationSummary}
                      qualityNote={m.qualityNote}
                      departmentSuggestion={m.departmentSuggestion}
                      confidenceScore={m.confidenceScore}
                      messageIndex={idx}
                      mode={m.mode || personaMode}
                      onSelectSource={(source) => setSelectedSource(source)}
                    />
                  </div>
                )}
              </div>
            ))}

            {/* Typing Indicator */}
            {loading && (
              <div className="flex items-start gap-3">
                <TypingIndicator />
              </div>
            )}
          </div>
        </div>

        {/* Fixed Bottom Composer Area */}
        <div className="flex-shrink-0 border-t border-white/[0.08] bg-[#0A0D14]/95 backdrop-blur-2xl p-4 z-20">
          <div className="mx-auto max-w-3xl space-y-3">
            {/* Suggested Follow-ups */}
            {suggestions.length > 0 && !loading && (
              <div className="flex flex-wrap gap-2 overflow-x-auto pb-1">
                {suggestions.map((s, idx) => (
                  <button
                    key={idx}
                    onClick={() => sendQuery(s)}
                    className="flex items-center gap-1.5 rounded-full border border-blue-500/25 bg-blue-500/10 px-3 py-1 text-xs text-blue-300 hover:border-blue-400 hover:bg-blue-500/20 hover:text-white transition-all cursor-pointer shadow-xs"
                  >
                    <span>💡</span>
                    <span className="truncate max-w-[280px]">{s}</span>
                  </button>
                ))}
              </div>
            )}

            {/* Live Voice Interim Speech Bubble */}
            {listening && interimText && (
              <div className="flex items-center gap-2 rounded-xl border border-indigo-500/30 bg-indigo-950/40 px-3.5 py-1.5 text-xs text-indigo-300 animate-pulse">
                <span>🎙️</span>
                <span className="italic truncate">{interimText}...</span>
              </div>
            )}

            {/* Composer Notice / Error Alert */}
            {composerNotice && (
              <div className="flex items-center justify-between rounded-xl border border-amber-500/30 bg-amber-950/40 px-3.5 py-2 text-xs text-amber-200 animate-fadeIn">
                <div className="flex items-center gap-2">
                  <span>⚠️</span>
                  <span>{composerNotice}</span>
                </div>
                <button
                  onClick={() => setComposerNotice(null)}
                  className="text-amber-400 hover:text-white cursor-pointer ml-2"
                >
                  ✕
                </button>
              </div>
            )}

            {/* Attached Documents inside Composer (Before Send) */}
            {composerDocs.length > 0 && (
              <div className="flex flex-wrap gap-2.5 rounded-2xl border border-white/[0.08] bg-white/[0.02] p-2.5 animate-fadeIn">
                {composerDocs.map((doc) => (
                  <AttachmentComposerCard
                    key={doc.caseId}
                    doc={doc}
                    onRemove={() => handleRemoveComposerDoc(doc.caseId)}
                  />
                ))}
              </div>
            )}

            {/* Input Form Box */}
            <div className="relative flex items-end gap-2 rounded-2xl border border-white/10 bg-[#121622] p-2 shadow-2xl focus-within:border-blue-500/50 transition-all">
              {/* File Upload Button */}
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.doc,.txt,.jpg,.jpeg,.png,.webp,.tiff,.bmp"
                onChange={handleFileSelect}
                className="hidden"
                id="file-upload-input"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-slate-400 hover:bg-white/10 hover:text-white transition-all cursor-pointer border border-transparent hover:border-white/10"
                title="Attach legal document (PDF, DOCX, scan)"
              >
                📎
              </button>

              {/* Speech-to-Text Microphone Button */}
              <button
                type="button"
                onClick={toggleListening}
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-all cursor-pointer border ${
                  listening
                    ? 'border-rose-500 bg-rose-500/20 text-rose-400 animate-pulse'
                    : 'text-slate-400 hover:bg-white/10 hover:text-white border-transparent'
                }`}
                title={listening ? 'Listening... click to stop' : 'Voice input'}
              >
                🎤
              </button>

              {/* Text Input Area */}
              <textarea
                ref={textareaRef}
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value)
                  e.target.style.height = 'auto'
                  e.target.style.height = `${Math.min(e.target.scrollHeight, 140)}px`
                }}
                onKeyDown={handleKeyDown}
                rows={1}
                placeholder={
                  isAnyDocBusy
                    ? `Indexing attached document (${composerDocs[0]?.totalPages || 'multi'} pages)... please wait`
                    : composerDocs.length > 0
                    ? `Ask anything about ${composerDocs[0]?.fileName}...`
                    : 'Ask any Indian legal question, section comparison, or case law...'
                }
                className="max-h-[140px] min-h-[40px] flex-1 resize-none bg-transparent px-2 py-2 text-sm text-white placeholder-slate-400 outline-none leading-relaxed"
              />

              {/* Send / Stop Button */}
              {loading ? (
                <button
                  type="button"
                  onClick={handleStopGeneration}
                  className="flex h-10 shrink-0 items-center gap-1.5 rounded-xl bg-rose-600/30 border border-rose-500/40 px-3.5 text-xs font-semibold text-rose-300 hover:bg-rose-600/40 transition-all cursor-pointer shadow-md"
                  title="Stop generation"
                >
                  <span>⏹</span>
                  <span>Stop</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => sendQuery()}
                  disabled={isAnyDocBusy || hasRejectedDoc || (!query.trim() && composerDocs.length === 0)}
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white shadow-lg shadow-blue-600/30 hover:bg-blue-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all cursor-pointer"
                  title={isAnyDocBusy ? 'Please wait for document indexing to complete' : 'Send message'}
                >
                  ➔
                </button>
              )}
            </div>

            <div className="flex items-center justify-between text-[10px] text-slate-400 px-1">
              <span>NyayaPramaan • Strict Indian Legal Intelligence</span>
              <span>Press Shift + Enter for new line</span>
            </div>
          </div>
        </div>
      </main>

      {/* Interactive Citation / Source Inspector Modal */}
      <SourceDetailModal
        source={selectedSource}
        onClose={() => setSelectedSource(null)}
      />
    </div>
  )
}