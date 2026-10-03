'use client'
import { useState, useRef, useEffect, useCallback } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { RoleGuard } from '@/components/auth/RoleGuard'
import { useVoiceInput } from '@/hooks/useVoiceInput'
import { uploadDocument, getCaseStatus, deleteDocument, UploadResponse, ACCEPTED_FORMATS, validateFileType } from '@/services/documentService'
import { askQuestion, listSessions, getSessionMessages, renameSession, deleteSession, togglePin } from '@/services/chatService'
import { AnswerCard } from '@/components/chat/AnswerCard'
import { TypingIndicator } from '@/components/chat/TypingIndicator'
import { ChatSidebar } from '@/components/chat/ChatSidebar'

type Message = {
  role: 'user' | 'assistant'
  content: string
  attachedFileNames?: string[]
  conclusion?: string
  usefulness?: string
  sources?: any[]
  qualityNote?: string
  departmentSuggestion?: string | null
  confidenceScore?: number
  isError?: boolean
}

type DocState = {
  caseId: string
  fileName: string
  status: 'processing' | 'ready' | 'failed' | 'cancelled' | 'rejected'
  pagesProcessed?: number
  totalPages?: number
  rejectionReason?: string
}

type PendingUpload = {
  fileName: string
  controller: AbortController
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
    title: "Document Analysis",
    desc: "Attach your case file (PDF, DOCX, image) to extract citations, timeline and key rulings.",
    icon: "📄",
  },
]

function CitizenChatContent() {
  const { user, signOut } = useAuth()

  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [isSessionLoading, setIsSessionLoading] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [sessions, setSessions] = useState<any[]>([])
  const [activeSession, setActiveSession] = useState<string | null>(null)
  const [isTemporary, setIsTemporary] = useState(false)

  // In-composer attached documents
  const [documents, setDocuments] = useState<DocState[]>([])
  const [pendingUploads, setPendingUploads] = useState<PendingUpload[]>([])
  const [composerNotice, setComposerNotice] = useState<string | null>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  const handleVoiceResult = useCallback((text: string) => {
    setQuery((prev) => {
      const clean = prev.replace(/\s*⋯.*$/, '').trim()
      return clean ? `${clean} ${text}` : text
    })
  }, [])

  const handleVoiceInterim = useCallback((_interim: string) => {}, [])

  const { listening, micStatus, micError, interimText, toggleListening } = useVoiceInput(handleVoiceResult, handleVoiceInterim)

  const refreshSessions = useCallback(async () => {
    try {
      const list = await listSessions()
      setSessions(Array.isArray(list) ? list : [])
    } catch (err) {
      console.error(err)
    }
  }, [])

  useEffect(() => {
    if (user) refreshSessions()
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

  // Poll status for any document still processing
  useEffect(() => {
    const processing = documents.filter((d) => d.status === 'processing')
    if (!processing.length) return

    const interval = setInterval(async () => {
      for (const doc of processing) {
        try {
          const s = await getCaseStatus(doc.caseId)
          setDocuments((prev) =>
            prev.map((d) => {
              if (d.caseId !== doc.caseId) return d
              const updated: DocState = {
                ...d,
                status: s.status as any,
                pagesProcessed: s.pages_processed ?? d.pagesProcessed,
                totalPages: s.total_pages ?? d.totalPages,
                rejectionReason: s.rejection_reason ?? d.rejectionReason,
              }
              return updated
            })
          )
          if (s.status === 'rejected' && s.rejection_reason) {
            setComposerNotice(`Upload Notice for "${doc.fileName}": ${s.rejection_reason}`)
          }
        } catch {
          // ignore transient polling errors
        }
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [documents])

  function handleNewChat() {
    setActiveSession(null)
    setMessages([])
    setSuggestions([])
    setIsTemporary(false)
    setDocuments([])
    setPendingUploads([])
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
      setDocuments([])
      setPendingUploads([])
      setComposerNotice(null)
    }
  }

  async function handleSelectSession(id: string) {
    if (activeSession === id && !isSessionLoading) return
    setActiveSession(id)
    setIsTemporary(false)
    setPendingUploads([])
    setComposerNotice(null)
    setIsSessionLoading(true)
    try {
      const { messages: msgs, documents: docs } = await getSessionMessages(id)
      setMessages(
        (msgs || []).map((m: any) => ({
          role: m.role,
          content: m.content,
          sources: m.sources,
        }))
      )
      setDocuments(
        (docs || []).map((d: any) => ({
          caseId: d.case_id,
          fileName: d.filename,
          status: 'ready',
        }))
      )
      setSuggestions([])
    } catch (err) {
      console.error('Failed to load session messages:', err)
    } finally {
      setIsSessionLoading(false)
    }
  }

  async function handleRename(id: string, title: string) {
    if (!title.trim()) return
    setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, title: title.trim() } : s)))
    try {
      await renameSession(id, title.trim())
    } catch (err) {
      console.error('Rename failed:', err)
    }
    refreshSessions()
  }

  async function handleTogglePin(id: string, pinned: boolean) {
    setSessions((prev) =>
      prev
        .map((s) => (s.id === id ? { ...s, pinned } : s))
        .sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0))
    )
    try {
      await togglePin(id, pinned)
    } catch (err) {
      console.error('Toggle pin failed:', err)
    }
    refreshSessions()
  }

  async function handleDelete(id: string) {
    setSessions((prev) => prev.filter((s) => s.id !== id))
    if (activeSession === id) {
      setActiveSession(null)
      setMessages([])
      setDocuments([])
    }
    try {
      await deleteSession(id)
    } catch (err) {
      console.error('Delete session failed:', err)
    }
    refreshSessions()
  }

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

      const controller = new AbortController()
      setPendingUploads((prev) => [...prev, { fileName: file.name, controller }])

      try {
        const result: UploadResponse = await uploadDocument(file, controller.signal)
        setPendingUploads((prev) => prev.filter((p) => p.fileName !== file.name))
        setDocuments((prev) => [
          ...prev,
          { caseId: result.case_id, fileName: result.filename, status: 'processing' },
        ])
      } catch (err: any) {
        setPendingUploads((prev) => prev.filter((p) => p.fileName !== file.name))
        if (err?.name !== 'AbortError' && !controller.signal.aborted) {
          const rawMsg: string = err?.message || 'Failed to process document.'
          let detailMsg = rawMsg
          if (rawMsg.includes('Cannot reach the server') || rawMsg.includes('fetch')) {
            detailMsg = 'Backend server is unreachable. Please verify that the backend API is running.'
          } else if (rawMsg.includes('not appear to be a legal')) {
            detailMsg = 'File does not appear to be a legal document. Please upload court judgments, FIRs, petitions, contracts, or statutory texts.'
          }
          setComposerNotice(`Upload failed for "${file.name}": ${detailMsg}`)
        }
      }
    }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  function cancelPendingUpload(fileName: string) {
    setPendingUploads((prev) => {
      const target = prev.find((p) => p.fileName === fileName)
      if (target) target.controller.abort()
      return prev.filter((p) => p.fileName !== fileName)
    })
  }

  async function removeDocument(caseId: string) {
    try {
      await deleteDocument(caseId)
    } catch (e) {
      console.error('Failed to delete document from backend:', e)
    }
    setDocuments((prev) => prev.filter((d) => d.caseId !== caseId))
  }

  const hasProcessingDocs = documents.some((d) => d.status === 'processing') || pendingUploads.length > 0
  const readyDocIds = documents.map((d) => d.caseId)

  async function sendQuery(text: string) {
    if (!text.trim() || loading) return
    setComposerNotice(null)

    const attachedNames = documents.length ? documents.map((d) => d.fileName) : undefined
    const currentDocIds = [...readyDocIds]

    setMessages((prev) => [...prev, { role: 'user', content: text, attachedFileNames: attachedNames }])
    setQuery('')
    setSuggestions([])
    setLoading(true)

    try {
      const result = await askQuestion(text, currentDocIds, activeSession ?? undefined, isTemporary)
      if (!isTemporary && result.session_id && result.session_id !== activeSession) {
        setActiveSession(result.session_id)
        refreshSessions()
      }
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: result.answer,
          conclusion: result.conclusion,
          usefulness: result.usefulness,
          sources: result.sources,
          qualityNote: result.quality_note,
          departmentSuggestion: result.department_suggestion,
        },
      ])
      setSuggestions(result.suggestions || [])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Unable to connect to the legal AI gateway. Please ensure the backend server is active and try again.',
          isError: true,
        },
      ])
    }
    setLoading(false)
  }

  return (
    <div className="citizen-chat-shell relative flex h-screen w-full overflow-hidden text-slate-100 font-sans antialiased">
      <div className="bloom-orb-citizen-1" />
      <div className="bloom-orb-citizen-2" />

      {/* Sidebar */}
      <ChatSidebar
        sessions={sessions}
        activeId={activeSession}
        onSelect={handleSelectSession}
        onNew={handleNewChat}
        onRename={handleRename}
        onDelete={handleDelete}
        onTogglePin={handleTogglePin}
        onLogout={signOut}
      />

      {/* Main Workspace */}
      <main className="relative flex flex-1 flex-col h-full overflow-hidden bg-transparent">
        {/* Top Header */}
        <header className="flex-shrink-0 border-b border-[#B8925A]/15 bg-[#0A0A0B]/85 backdrop-blur-2xl z-20">
          <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-3.5">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-[#B8925A]/25 via-[#D4A368]/15 to-transparent border border-[#B8925A]/20 text-sm shadow-inner">
                ⚖️
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-sm font-semibold tracking-tight text-white">
                    NyayaPramaan AI Research
                  </h1>
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/25 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse-dot" />
                    Verified RAG
                  </span>
                </div>
                <p className="text-[11px] text-[#B8925A]/70">
                  Statutory Provisions • Case Law • Real-Time Evidence Verification
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handleToggleTemporary}
                title="Temporary sessions are never persisted"
                className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-all cursor-pointer border ${
                  isTemporary
                    ? 'border-amber-500/40 bg-amber-500/15 text-amber-300 shadow-sm'
                    : 'border-white/10 bg-white/[0.04] text-slate-300 hover:border-white/20 hover:text-white'
                }`}
              >
                <span>{isTemporary ? '⏳ Temporary Active' : '⏳ Incognito'}</span>
              </button>
            </div>
          </div>
        </header>

        {/* Conversation Stream */}
        <div ref={messagesContainerRef} className="flex-1 overflow-y-auto px-4 py-6 md:px-6">
          <div className="mx-auto max-w-3xl space-y-6">
            {isSessionLoading ? (
              <div className="my-16 flex flex-col items-center justify-center text-center">
                <div className="flex items-center gap-3 text-sm text-slate-400">
                  <span className="h-2 w-2 rounded-full bg-[#B8925A] animate-pulse-dot" />
                  <span>Loading conversation history...</span>
                </div>
              </div>
            ) : messages.length === 0 ? (
              <div className="my-8 flex flex-col items-center justify-center text-center">
                <div className="animate-text-float flex h-16 w-16 items-center justify-center rounded-3xl bg-gradient-to-tr from-[#B8925A]/30 via-[#D4A368]/20 to-[#C89B59]/15 border border-[#B8925A]/25 text-3xl shadow-2xl">
                  ⚖️
                </div>
                <h2 className="mt-5 text-2xl font-medium tracking-tight text-white">
                  Where evidence meets legal intelligence.
                </h2>
                <p className="mt-2 max-w-md text-xs text-slate-400 leading-relaxed">
                  Every query is cross-checked against authoritative statutes and judgment chunks with transparent verification badges.
                </p>

                <div className="mt-8 grid w-full gap-3 sm:grid-cols-3 text-left">
                  {STARTER_PROMPTS.map((p, idx) => (
                    <button
                      key={idx}
                      onClick={() => sendQuery(p.desc)}
                      className="group flex flex-col justify-between rounded-2xl border border-white/10 bg-[#0E121B]/70 p-4 transition-all hover:border-[#B8925A]/40 hover:bg-[#B8925A]/[0.08] hover:shadow-xl cursor-pointer"
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
            {!isSessionLoading &&
              messages.map((m, i) => (
                <div
                  key={i}
                  className={`flex w-full flex-col ${
                    m.role === 'user' ? 'items-end' : 'items-start'
                  }`}
                >
                  {m.role === 'user' ? (
                    <div className="flex flex-col items-end max-w-[85%]">
                      {/* Attached document badge docked with user prompt */}
                      {m.attachedFileNames && m.attachedFileNames.length > 0 && (
                        <div className="mb-2 flex flex-wrap gap-1.5 justify-end">
                          {m.attachedFileNames.map((name, j) => (
                            <span
                              key={j}
                              className="flex items-center gap-1.5 rounded-xl bg-[#B8925A]/25 border border-[#B8925A]/40 px-3 py-1 text-xs font-medium text-[#F7E7CE] shadow-sm"
                            >
                              <span>📄</span>
                              <span className="truncate max-w-[220px] font-semibold">{name}</span>
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="rounded-2xl bg-gradient-to-br from-[#B8925A] via-[#C89B59] to-[#D4A368] px-4 py-3 text-sm text-slate-950 font-medium shadow-xl leading-relaxed border border-[#B8925A]/30">
                        {m.content}
                      </div>
                    </div>
                  ) : (
                    <div className="w-full">
                      <AnswerCard
                        answer={m.content}
                        conclusion={m.conclusion}
                        usefulness={m.usefulness}
                        sources={m.sources}
                        qualityNote={m.qualityNote}
                        departmentSuggestion={m.departmentSuggestion}
                        confidenceScore={m.confidenceScore}
                        messageIndex={i}
                      />
                    </div>
                  )}
                </div>
              ))}

            {loading && (
              <div className="flex items-start">
                <TypingIndicator />
              </div>
            )}

            {/* Suggestions Chips */}
            {suggestions.length > 0 && !loading && (
              <div className="flex flex-wrap items-center gap-2 pt-2">
                <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                  Follow-up Suggestions:
                </span>
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => sendQuery(s)}
                    className="flex items-center gap-1.5 rounded-full border border-[#B8925A]/20 bg-[#B8925A]/[0.06] px-3.5 py-1 text-xs text-slate-200 hover:border-[#B8925A]/40 hover:bg-[#B8925A]/15 hover:text-white transition-all cursor-pointer shadow-xs"
                  >
                    <span>{s}</span>
                    <span className="text-[#B8925A] text-[10px]">↗</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Floating Input Command Dock (ChatGPT Style Composer) */}
        <div className="flex-shrink-0 border-t border-[#B8925A]/10 bg-[#0A0A0B]/90 p-4 backdrop-blur-2xl">
          <div className="mx-auto max-w-3xl">
            {/* Inline Composer Alert / Error Banner */}
            {composerNotice && (
              <div className="mb-2.5 flex items-center justify-between rounded-xl border border-amber-500/30 bg-amber-500/10 px-3.5 py-2 text-xs text-amber-300 backdrop-blur-md">
                <div className="flex items-center gap-2">
                  <span>⚠️</span>
                  <span>{composerNotice}</span>
                </div>
                <button
                  onClick={() => setComposerNotice(null)}
                  className="ml-3 text-amber-300 hover:text-white cursor-pointer font-bold"
                  title="Dismiss notice"
                >
                  ✕
                </button>
              </div>
            )}

            {/* Unified ChatGPT-style Input Container with Embedded Attachment Chips */}
            <div className="glass-jelly relative flex flex-col gap-2 p-3 focus-within:border-[#B8925A]/50 focus-within:ring-2 focus-within:ring-[#B8925A]/20 transition-all rounded-2xl border border-white/10 bg-[#121622]/90 shadow-2xl">
              <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPTED_FORMATS}
                multiple
                onChange={handleFileSelect}
                className="hidden"
              />

              {/* Embedded Document Attachment Cards Inside Box */}
              {(documents.length > 0 || pendingUploads.length > 0) && (
                <div className="flex flex-wrap items-center gap-2 pb-1.5 border-b border-white/[0.08]">
                  {pendingUploads.map((p) => (
                    <div
                      key={p.fileName}
                      className="flex items-center gap-2 rounded-xl border border-amber-500/40 bg-amber-500/15 px-3 py-1.5 text-xs text-amber-300 shadow-sm"
                    >
                      <span className="text-sm">📄</span>
                      <span className="truncate max-w-[160px] font-medium">{p.fileName}</span>
                      <span className="text-[10px] text-amber-400 animate-pulse font-semibold">Uploading...</span>
                      <button
                        onClick={() => cancelPendingUpload(p.fileName)}
                        className="ml-1 text-xs text-white/60 hover:text-white cursor-pointer"
                        title="Cancel upload"
                      >
                        ✕
                      </button>
                    </div>
                  ))}

                  {documents.map((doc) => (
                    <div
                      key={doc.caseId}
                      className={`flex items-center gap-2 rounded-xl border px-3 py-1.5 text-xs shadow-sm transition-all ${
                        doc.status === 'processing'
                          ? 'border-[#B8925A]/40 bg-[#B8925A]/15 text-[#D4A368]'
                          : doc.status === 'ready'
                          ? 'border-emerald-500/40 bg-emerald-500/15 text-emerald-300'
                          : doc.status === 'rejected'
                          ? 'border-amber-500/40 bg-amber-500/15 text-amber-300'
                          : 'border-red-500/40 bg-red-500/15 text-red-300'
                      }`}
                    >
                      <span className="text-sm">📄</span>
                      <span className="truncate max-w-[180px] font-medium">{doc.fileName}</span>
                      <span className="text-[10px] font-semibold">
                        {doc.status === 'processing' ? (
                          <span className="flex items-center gap-1 text-[#B8925A]">
                            <span className="h-1.5 w-1.5 rounded-full bg-[#B8925A] animate-pulse-dot" />
                            {doc.totalPages && doc.totalPages > 0
                              ? `Indexing ${doc.pagesProcessed ?? 0}/${doc.totalPages} pages`
                              : 'Analyzing document...'}
                          </span>
                        ) : doc.status === 'ready' ? (
                          <span className="text-emerald-300 font-bold">✓ Attached & Indexed</span>
                        ) : doc.status === 'rejected' ? (
                          '⚠ Non-legal file'
                        ) : (
                          'Failed'
                        )}
                      </span>
                      <button
                        onClick={() => removeDocument(doc.caseId)}
                        className="ml-1 text-xs text-white/50 hover:text-white cursor-pointer"
                        title="Remove document"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Textarea & Controls Row */}
              <div className="flex items-end gap-2">
                <div className="flex items-center gap-1 pb-0.5">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={loading}
                    className="flex h-8 w-8 items-center justify-center rounded-xl text-slate-300 hover:bg-white/[0.08] hover:text-[#B8925A] transition-all cursor-pointer"
                    title="Attach Document (PDF, DOCX, Image, TXT)"
                  >
                    📎
                  </button>
                  <button
                    type="button"
                    onClick={toggleListening}
                    disabled={loading}
                    title={
                      micError === 'not-allowed'
                        ? 'Microphone access denied. Allow mic in browser settings.'
                        : listening
                        ? 'Stop listening'
                        : 'Click to start voice input (Hindi + English)'
                    }
                    className={`relative flex h-8 w-8 items-center justify-center rounded-xl transition-all cursor-pointer ${
                      micError
                        ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                        : listening
                        ? 'bg-[#B8925A]/20 text-[#B8925A] border border-[#B8925A]/40'
                        : 'text-slate-300 hover:bg-white/[0.08] hover:text-white'
                    }`}
                  >
                    {listening && (
                      <span className="absolute inset-0 rounded-xl border-2 border-[#B8925A]/60 animate-ping opacity-60 pointer-events-none" />
                    )}
                    <span className="text-sm">{listening ? '🔴' : '🎤'}</span>
                  </button>
                </div>

                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      if (!loading && !hasProcessingDocs) sendQuery(query)
                    }
                  }}
                  rows={1}
                  placeholder={
                    listening
                      ? '🎤 Listening... speak now (Hindi or English)'
                      : hasProcessingDocs
                      ? 'Indexing attached document chunks...'
                      : documents.length > 0
                      ? 'Ask questions about the attached document, or legal statutes...'
                      : 'Ask about IPC, BNS, court precedents, or attach any case file...'
                  }
                  disabled={loading}
                  className={`max-h-32 flex-1 resize-none bg-transparent px-2.5 py-1.5 text-sm outline-none leading-relaxed ${
                    listening ? 'text-[#D4A368] placeholder:text-[#B8925A]/70' : 'text-slate-100 placeholder:text-slate-400'
                  }`}
                />

                {/* Voice Bar */}
                {listening && interimText && (
                  <div className="px-2.5 pb-1 flex items-center gap-2 text-xs text-[#B8925A]/80 italic">
                    <span className="truncate max-w-[200px]">{interimText}</span>
                  </div>
                )}

                <div className="pb-0.5 pr-0.5">
                  <button
                    type="button"
                    onClick={() => sendQuery(query)}
                    disabled={loading || hasProcessingDocs || !query.trim()}
                    className="flex h-9 items-center justify-center gap-1.5 rounded-xl bg-gradient-to-r from-[#B8925A] via-[#C89B59] to-[#D4A368] px-4 text-xs font-semibold text-slate-950 transition-all hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed shadow-md cursor-pointer"
                  >
                    <span>Ask</span>
                    <span>→</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Mic error notice */}
            {micError && (
              <div className="mt-2 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-3.5 py-2 text-xs">
                <span className="text-red-400">🚫</span>
                <span className="flex-1 text-red-300">
                  Microphone access blocked. Click the lock icon in the browser address bar to allow microphone.
                </span>
                <button
                  onClick={() => toggleListening()}
                  className="rounded-lg border border-red-500/30 bg-red-500/15 px-2.5 py-1 text-xs text-red-300 hover:bg-red-500/25 cursor-pointer"
                >
                  Retry
                </button>
              </div>
            )}

            <div className="mt-2 flex items-center justify-between px-1 text-[11px] text-slate-400">
              {listening ? (
                <span className="flex items-center gap-1.5 text-[#B8925A]">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#B8925A] animate-pulse" />
                  Listening — speak clearly in Hindi or English. Click 🔴 to stop.
                </span>
              ) : (
                <span>NyayaPramaan AI • Multi-document citations • PDF, DOCX, Image, TXT</span>
              )}
              <span>Press Enter to send, Shift+Enter for new line</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default function PublicChat() {
  return (
    <RoleGuard allowedRole="public">
      <CitizenChatContent />
    </RoleGuard>
  )
}