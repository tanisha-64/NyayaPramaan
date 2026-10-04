
'use client'

import { useState, useRef, useEffect } from 'react'

import { useRouter } from 'next/navigation'

import { useAuth } from '@/hooks/useAuth'

import { useVoiceInput } from '@/hooks/useVoiceInput'

import { uploadDocument, UploadResponse } from '@/services/documentService'

import { askQuestion, listSessions, getSessionMessages, renameSession, deleteSession, togglePin } from '@/services/chatService'

import { AnswerCard } from '@/components/chat/AnswerCard'

import { TypingIndicator } from '@/components/chat/TypingIndicator'

import { ChatSidebar } from '@/components/chat/ChatSidebar'



type Message = {

  role: 'user' | 'assistant'; content: string; attachedFileName?: string

  conclusion?: string; usefulness?: string; sources?: any[]; qualityNote?: string; departmentSuggestion?: string | null

}

type ActiveDoc = { caseId: string; fileName: string }



export default function PublicChat() {

  const { user, loading: authLoading, signOut } = useAuth()

  const router = useRouter()



  useEffect(() => {

    if (!authLoading && !user) router.push('/login')

  }, [authLoading, user, router])



  const [query, setQuery] = useState('')

  const [messages, setMessages] = useState<Message[]>([])

  const [loading, setLoading] = useState(false)

  const [suggestions, setSuggestions] = useState<string[]>([])

  const [sessions, setSessions] = useState<any[]>([])

  const [activeSession, setActiveSession] = useState<string | null>(null)

  const [isTemporary, setIsTemporary] = useState(false)



  const [activeDoc, setActiveDoc] = useState<ActiveDoc | null>(null)

  const [uploadingFileName, setUploadingFileName] = useState<string | null>(null)

  const [uploadError, setUploadError] = useState<string | null>(null)



  const fileInputRef = useRef<HTMLInputElement>(null)

  const { listening, startListening } = useVoiceInput((text) => setQuery((prev) => (prev ? prev + ' ' + text : text)))



  useEffect(() => { if (user) refreshSessions() }, [user])



  async function refreshSessions() {

    try {

      const list = await listSessions()

      setSessions(Array.isArray(list) ? list : [])

    } catch (err) { console.error(err) }

  }



  function handleNewChat() {

    setActiveSession(null); setMessages([]); setSuggestions([])

    setIsTemporary(false); setActiveDoc(null); setUploadError(null)

  }



  function handleToggleTemporary() {

    const next = !isTemporary

    setIsTemporary(next)

    if (next) {

      setActiveSession(null); setMessages([]); setSuggestions([]); setActiveDoc(null)

    }

  }



  async function handleSelectSession(id: string) {

    setActiveSession(id); setIsTemporary(false); setUploadError(null)

    try {

      const { messages: msgs, case_id, case_filename } = await getSessionMessages(id)

      setMessages(msgs.map((m: any) => ({ role: m.role, content: m.content, sources: m.sources })))

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

    setUploadingFileName(file.name)

    try {

      const result: UploadResponse = await uploadDocument(file)

      setActiveDoc({ caseId: result.case_id, fileName: result.filename })

    } catch (err: any) {

      setUploadError(err?.message || "This document couldn't be processed. Please try a different legal document.")

    }

    setUploadingFileName(null)

    if (fileInputRef.current) fileInputRef.current.value = ''

  }



  function clearActiveDocument() {

    setActiveDoc(null)

  }



  async function sendQuery(text: string) {

    if (!text.trim() || loading) return



    setMessages((prev) => [...prev, { role: 'user', content: text, attachedFileName: activeDoc?.fileName }])

    setQuery(''); setSuggestions([]); setLoading(true)



    try {

      const result = await askQuestion(text, activeDoc?.caseId, activeSession ?? undefined, isTemporary)

      if (!isTemporary && result.session_id && result.session_id !== activeSession) {

        setActiveSession(result.session_id); refreshSessions()

      }

      setMessages((prev) => [...prev, {

        role: 'assistant', content: result.answer, conclusion: result.conclusion,

        usefulness: result.usefulness, sources: result.sources,

        qualityNote: result.quality_note, departmentSuggestion: result.department_suggestion,

      }])

      setSuggestions(result.suggestions || [])

    } catch (err: any) {

      setMessages((prev) => [...prev, { role: 'assistant', content: err?.message || 'Something went wrong. Please try again.' }])

    }

    setLoading(false)

  }



  if (authLoading || !user) {

    return <div style={{ height: '100vh', background: '#0A0A0B', color: '#F7F5F0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Loading...</div>

  }



  return (

    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: '#0A0A0B', color: '#F7F5F0', fontFamily: 'sans-serif' }}>

      <ChatSidebar sessions={sessions} activeId={activeSession} onSelect={handleSelectSession}

        onNew={handleNewChat} onRename={handleRename} onDelete={handleDelete} onTogglePin={handleTogglePin}

        onLogout={signOut} />



      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

        <div style={{ flexShrink: 0, borderBottom: '1px solid rgba(255,255,255,0.08)' }}>

          <div style={{ maxWidth: 700, margin: '0 auto', padding: '20px 20px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>

            <div>

              <h1 style={{ fontSize: 20, margin: 0 }}>NyayaPramaan — Ask a Legal Question</h1>

              <p style={{ color: 'rgba(247,245,240,0.5)', fontSize: 12, marginTop: 4 }}>

                General legal information, not professional advice. English, Hindi, or Hinglish.

              </p>

            </div>

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



        <div style={{ flex: 1, overflowY: 'auto' }}>

          <div style={{ maxWidth: 700, margin: '0 auto', padding: '16px 20px' }}>

            {messages.map((m, i) => (

              <div key={i} style={{ marginBottom: 20, textAlign: m.role === 'user' ? 'right' : 'left' }}>

                {m.role === 'user' ? (

                  <div style={{ display: 'inline-block', maxWidth: '85%', textAlign: 'right' }}>

                    {m.attachedFileName && (

                      <div style={{ marginBottom: 6, display: 'flex', justifyContent: 'flex-end' }}>

                        <span style={{ fontSize: 11, padding: '3px 10px', borderRadius: 12, background: 'rgba(43,92,224,0.15)', color: '#5B8CFF' }}>

                          📄 {m.attachedFileName}

                        </span>

                      </div>

                    )}

                    <div style={{ padding: '10px 14px', borderRadius: 10, background: '#2B5CE0', fontSize: 14, textAlign: 'left' }}>

                      {m.content}

                    </div>

                  </div>

                ) : (

                  <div style={{ display: 'inline-block', textAlign: 'left' }}>

                    <AnswerCard

                      answer={m.content}

                      conclusion={m.conclusion}

                      usefulness={m.usefulness}

                      sources={m.sources}

                      qualityNote={m.qualityNote}

                      departmentSuggestion={m.departmentSuggestion}

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

          </div>

        </div>



        <div style={{ flexShrink: 0, borderTop: '1px solid rgba(255,255,255,0.1)' }}>

          <div style={{ maxWidth: 700, margin: '0 auto', padding: '10px 20px 0' }}>



            {activeDoc && (

              <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 12px', borderRadius: 8, background: 'rgba(43,92,224,0.08)', border: '1px solid rgba(43,92,224,0.2)' }}>

                <span style={{ fontSize: 12, color: '#5B8CFF' }}>💬 Continuing conversation about: {activeDoc.fileName}</span>

                <button onClick={clearActiveDocument} title="Stop referencing this document" style={{ background: 'none', border: 'none', color: 'rgba(247,245,240,0.5)', cursor: 'pointer', fontSize: 13 }}>✕</button>

              </div>

            )}



            {uploadingFileName && (

              <div style={{ marginBottom: 8, padding: '6px 12px', borderRadius: 8, background: 'rgba(255,255,255,0.05)', fontSize: 12, color: 'rgba(247,245,240,0.6)' }}>

                📄 Uploading & reading {uploadingFileName}...

              </div>

            )}



            {uploadError && (

              <div style={{ marginBottom: 8, padding: '6px 12px', borderRadius: 8, background: 'rgba(224,106,71,0.1)', border: '1px solid rgba(224,106,71,0.3)', fontSize: 12, color: '#E06A47' }}>

                ⚠️ {uploadError}

              </div>

            )}

          </div>



          <div style={{ maxWidth: 700, margin: '0 auto', padding: '0 20px 20px', display: 'flex', gap: 8 }}>

            <input ref={fileInputRef} type="file" accept=".pdf" onChange={handleFileSelect} style={{ display: 'none' }} />

            <button onClick={() => fileInputRef.current?.click()} disabled={!!uploadingFileName} title="Attach a document" style={{ padding: '10px 14px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.15)', background: 'transparent', color: '#F7F5F0', cursor: 'pointer' }}>

              {uploadingFileName ? '...' : '📎'}

            </button>

            <button onClick={startListening} disabled={loading} title="Voice input" style={{

              padding: '10px 14px', borderRadius: 8,

              border: `1px solid ${listening ? '#B8862E' : 'rgba(255,255,255,0.15)'}`,

              background: listening ? 'rgba(184,134,46,0.15)' : 'transparent', color: '#F7F5F0', cursor: 'pointer',

            }}>

              {listening ? '🔴' : '🎤'}

            </button>

            <textarea

              value={query}

              onChange={(e) => setQuery(e.target.value)}

              onKeyDown={(e) => {

                if (e.key === 'Enter' && !e.shiftKey) {

                  e.preventDefault()

                  if (!loading) sendQuery(query)

                }

              }}

              rows={1}

              placeholder="Ask a legal question..."

              style={{ flex: 1, padding: '10px 14px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.03)', color: '#F7F5F0', resize: 'none' }}

            />

            <button onClick={() => sendQuery(query)} disabled={loading} style={{ padding: '10px 18px', borderRadius: 8, border: 'none', background: '#B8925A', color: '#0A0A0B', fontWeight: 500, cursor: loading ? 'default' : 'pointer', opacity: loading ? 0.6 : 1 }}>

              Ask

            </button>

          </div>

        </div>

      </main>

    </div>

  )

}

