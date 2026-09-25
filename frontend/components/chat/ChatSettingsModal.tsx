'use client'
import React, { useState, useEffect } from 'react'
import { listCases, deleteCase, clearAllCases, CaseSummary } from '@/services/caseService'
import { clearAllSessions, listSessions } from '@/services/chatService'

type SettingsTab = 'documents' | 'data' | 'preferences'

interface ChatSettingsModalProps {
  open: boolean
  onClose: () => void
  onChatsCleared?: () => void
  onDocsUpdated?: () => void
}

export function ChatSettingsModal({
  open,
  onClose,
  onChatsCleared,
  onDocsUpdated,
}: ChatSettingsModalProps) {
  const [tab, setTab] = useState<SettingsTab>('documents')
  const [docs, setDocs] = useState<CaseSummary[]>([])
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  // Confirm states
  const [confirmClearDocs, setConfirmClearDocs] = useState(false)
  const [confirmClearChats, setConfirmClearChats] = useState(false)
  const [confirmClearBookmarks, setConfirmClearBookmarks] = useState(false)

  // Preferences
  const [languagePref, setLanguagePref] = useState('auto')
  const [audiencePref, setAudiencePref] = useState('citizen')

  useEffect(() => {
    if (open) {
      loadDocs()
      const savedLang = localStorage.getItem('nyaya_pref_language') || 'auto'
      const savedAud = localStorage.getItem('nyaya_pref_audience') || 'citizen'
      setLanguagePref(savedLang)
      setAudiencePref(savedAud)
    }
  }, [open])

  async function loadDocs() {
    setLoadingDocs(true)
    try {
      const data = await listCases()
      setDocs(Array.isArray(data) ? data : [])
    } catch (e) {
      console.error('[ChatSettingsModal] Failed to load documents:', e)
    } finally {
      setLoadingDocs(false)
    }
  }

  function showToast(msg: string) {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(null), 3000)
  }

  async function handleDeleteSingleDoc(id: string) {
    setDeletingId(id)
    try {
      await deleteCase(id)
      setDocs((prev) => prev.filter((d) => d.id !== id))
      showToast('Document deleted from library')
      if (onDocsUpdated) onDocsUpdated()
    } catch (e) {
      showToast('Failed to delete document')
    } finally {
      setDeletingId(null)
    }
  }

  async function handleClearAllDocs() {
    setActionLoading(true)
    try {
      await clearAllCases()
      setDocs([])
      setConfirmClearDocs(false)
      showToast('All uploaded documents deleted')
      if (onDocsUpdated) onDocsUpdated()
    } catch (e) {
      showToast('Failed to clear documents')
    } finally {
      setActionLoading(false)
    }
  }

  async function handleClearAllChats() {
    setActionLoading(true)
    try {
      await clearAllSessions()
      setConfirmClearChats(false)
      showToast('All chat conversations cleared')
      if (onChatsCleared) onChatsCleared()
    } catch (e) {
      showToast('Failed to clear chat sessions')
    } finally {
      setActionLoading(false)
    }
  }

  function handleClearBookmarks() {
    try {
      localStorage.removeItem('nyayapramaan_saved_answers')
      setConfirmClearBookmarks(false)
      showToast('All saved answers cleared')
    } catch (e) {
      showToast('Failed to clear bookmarks')
    }
  }

  async function handleExportData() {
    try {
      const sessions = await listSessions()
      const savedAnswers = localStorage.getItem('nyayapramaan_saved_answers')
      const exportObj = {
        exportedAt: new Date().toISOString(),
        platform: 'NyayaPramaan Legal Intelligence',
        documentsCount: docs.length,
        documents: docs.map((d) => ({ id: d.id, filename: d.filename, created_at: d.created_at })),
        chatSessionsCount: Array.isArray(sessions) ? sessions.length : 0,
        chatSessions: sessions,
        savedAnswers: savedAnswers ? JSON.parse(savedAnswers) : [],
      }

      const blob = new Blob([JSON.stringify(exportObj, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `nyayapramaan-data-export-${new Date().toISOString().slice(0, 10)}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      showToast('Data exported successfully')
    } catch (e) {
      showToast('Failed to export data')
    }
  }

  function handleSavePreferences() {
    localStorage.setItem('nyaya_pref_language', languagePref)
    localStorage.setItem('nyaya_pref_audience', audiencePref)
    showToast('Preferences saved!')
  }

  if (!open) return null

  const filteredDocs = docs.filter((d) =>
    (d.filename || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (d.summary || '').toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/75 backdrop-blur-md transition-opacity"
        onClick={onClose}
      />

      {/* Modal Container */}
      <div className="relative flex flex-col w-full max-w-2xl max-h-[85vh] rounded-2xl border border-white/15 bg-[#0D0F14] text-white shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Toast alert inside modal */}
        {toastMessage && (
          <div className="absolute top-3 right-4 z-50 rounded-xl border border-amber-500/40 bg-amber-500/20 px-3.5 py-1.5 text-xs text-amber-200 shadow-lg backdrop-blur-md animate-bounce">
            {toastMessage}
          </div>
        )}

        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-white/10 px-6 py-4 bg-white/[0.02]">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/30 text-base">
              ⚙️
            </span>
            <div>
              <h2 className="text-base font-semibold text-white tracking-wide">
                Settings & Data Controls
              </h2>
              <p className="text-xs text-slate-400">
                Manage your uploaded case files, privacy, and chat storage
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-xl text-slate-400 hover:bg-white/10 hover:text-white transition-colors cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Tabs Bar */}
        <div className="flex border-b border-white/10 bg-white/[0.01] px-6 gap-2">
          <button
            onClick={() => setTab('documents')}
            className={`flex items-center gap-2 py-3 px-3 text-xs font-medium border-b-2 transition-all cursor-pointer ${
              tab === 'documents'
                ? 'border-amber-400 text-amber-300 font-semibold'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>📁</span>
            <span>Uploaded Files ({docs.length})</span>
          </button>
          <button
            onClick={() => setTab('data')}
            className={`flex items-center gap-2 py-3 px-3 text-xs font-medium border-b-2 transition-all cursor-pointer ${
              tab === 'data'
                ? 'border-amber-400 text-amber-300 font-semibold'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>🗄️</span>
            <span>Data & Storage</span>
          </button>
          <button
            onClick={() => setTab('preferences')}
            className={`flex items-center gap-2 py-3 px-3 text-xs font-medium border-b-2 transition-all cursor-pointer ${
              tab === 'preferences'
                ? 'border-amber-400 text-amber-300 font-semibold'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>🎛️</span>
            <span>AI Preferences</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 min-h-[340px]">
          {/* TAB 1: UPLOADED DOCUMENTS */}
          {tab === 'documents' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div className="relative flex-1">
                  <span className="absolute left-3 top-2.5 text-xs text-slate-500">🔍</span>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search uploaded files or case notes…"
                    className="w-full rounded-xl border border-white/10 bg-white/[0.04] pl-8 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:border-amber-500/50 focus:outline-none"
                  />
                </div>

                {docs.length > 0 && (
                  <button
                    onClick={() => setConfirmClearDocs(true)}
                    className="flex items-center gap-1.5 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs font-medium text-red-300 hover:bg-red-500/20 hover:border-red-500/50 transition-all cursor-pointer whitespace-nowrap"
                  >
                    <span>🗑️</span>
                    <span>Clear All Files</span>
                  </button>
                )}
              </div>

              {/* Confirm Clear All Docs Banner */}
              {confirmClearDocs && (
                <div className="rounded-xl border border-red-500/40 bg-red-950/40 p-3.5 text-xs space-y-2.5">
                  <div className="flex items-center gap-2 text-red-200 font-semibold">
                    <span>⚠️</span>
                    <span>Delete All {docs.length} Uploaded Documents?</span>
                  </div>
                  <p className="text-[11px] text-red-300/80 leading-relaxed">
                    This will permanently delete all your case files, extracted text, and AI vector embeddings. This action cannot be undone.
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={handleClearAllDocs}
                      disabled={actionLoading}
                      className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-500 transition-colors cursor-pointer"
                    >
                      {actionLoading ? 'Deleting…' : 'Yes, Delete All Files'}
                    </button>
                    <button
                      onClick={() => setConfirmClearDocs(false)}
                      className="rounded-lg border border-white/20 bg-white/10 px-3 py-1.5 text-xs text-slate-300 hover:bg-white/20 transition-colors cursor-pointer"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {/* Document List */}
              {loadingDocs ? (
                <div className="flex items-center justify-center py-12 text-xs text-slate-400 gap-2">
                  <span className="animate-spin text-base">⏳</span>
                  <span>Loading your document library…</span>
                </div>
              ) : filteredDocs.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-white/10 p-8 text-center space-y-2">
                  <span className="text-3xl block">📄</span>
                  <p className="text-xs text-slate-300 font-medium">No documents uploaded yet</p>
                  <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
                    When you attach PDFs, FIRs, Word documents, or court orders in chat, they will appear here and can be managed or deleted anytime.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredDocs.map((doc) => (
                    <div
                      key={doc.id}
                      className="group flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3 hover:bg-white/[0.06] hover:border-white/20 transition-all"
                    >
                      <div className="flex items-start gap-2.5 min-w-0 flex-1">
                        <span className="text-xl mt-0.5">
                          {doc.filename?.endsWith('.pdf') ? '📕' : doc.filename?.endsWith('.docx') ? '📘' : '📄'}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-medium text-white truncate max-w-[280px]" title={doc.filename}>
                              {doc.filename || 'Untitled Document'}
                            </span>
                            <span
                              className={`rounded-md border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider ${
                                doc.status === 'ready'
                                  ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                                  : doc.status === 'failed'
                                  ? 'border-red-500/30 bg-red-500/10 text-red-300'
                                  : 'border-amber-500/30 bg-amber-500/10 text-amber-300 animate-pulse'
                              }`}
                            >
                              {doc.status || 'Ready'}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">
                            {doc.summary || 'Document indexed for legal AI retrieval'}
                          </p>
                          <span className="text-[10px] text-slate-500">
                            {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'Recent'}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleDeleteSingleDoc(doc.id)}
                          disabled={deletingId === doc.id}
                          className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 text-slate-400 hover:border-red-500/40 hover:bg-red-500/10 hover:text-red-300 transition-colors cursor-pointer"
                          title="Delete document"
                        >
                          {deletingId === doc.id ? (
                            <span className="animate-spin text-xs">⏳</span>
                          ) : (
                            <span className="text-xs">🗑️</span>
                          )}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: DATA & STORAGE CONTROLS */}
          {tab === 'data' && (
            <div className="space-y-4">
              {/* Export Data */}
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-xs font-semibold text-white">Export All Research Data</h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Download a complete JSON export of your legal chat sessions, saved answers, and document records.
                  </p>
                </div>
                <button
                  onClick={handleExportData}
                  className="flex items-center gap-1.5 rounded-xl border border-white/20 bg-white/10 px-3.5 py-2 text-xs font-medium text-white hover:bg-white/20 transition-all cursor-pointer whitespace-nowrap"
                >
                  <span>📥</span>
                  <span>Export JSON</span>
                </button>
              </div>

              {/* Clear Saved Bookmarks */}
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-xs font-semibold text-white">Clear Saved Answers</h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Remove all bookmarked legal conclusions from your local storage.
                  </p>
                </div>
                {confirmClearBookmarks ? (
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={handleClearBookmarks}
                      className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-500 transition-colors cursor-pointer"
                    >
                      Confirm
                    </button>
                    <button
                      onClick={() => setConfirmClearBookmarks(false)}
                      className="rounded-lg border border-white/20 px-2 py-1.5 text-xs text-slate-400 hover:text-white"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setConfirmClearBookmarks(true)}
                    className="flex items-center gap-1.5 rounded-xl border border-white/15 bg-white/[0.05] px-3.5 py-2 text-xs font-medium text-slate-300 hover:border-red-500/40 hover:bg-red-500/10 hover:text-red-300 transition-all cursor-pointer whitespace-nowrap"
                  >
                    <span>★</span>
                    <span>Clear Bookmarks</span>
                  </button>
                )}
              </div>

              {/* Clear All Chat Conversations */}
              <div className="rounded-xl border border-red-500/20 bg-red-950/20 p-4 flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-xs font-semibold text-red-300">Clear All Chat Conversations</h3>
                  <p className="text-[11px] text-red-400/70 mt-0.5">
                    Permanently delete all previous conversation threads and history messages.
                  </p>
                </div>
                {confirmClearChats ? (
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={handleClearAllChats}
                      disabled={actionLoading}
                      className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-500 transition-colors cursor-pointer"
                    >
                      {actionLoading ? 'Clearing…' : 'Yes, Delete All'}
                    </button>
                    <button
                      onClick={() => setConfirmClearChats(false)}
                      className="rounded-lg border border-white/20 px-2 py-1.5 text-xs text-slate-400 hover:text-white"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setConfirmClearChats(true)}
                    className="flex items-center gap-1.5 rounded-xl border border-red-500/30 bg-red-500/10 px-3.5 py-2 text-xs font-medium text-red-300 hover:bg-red-500/20 transition-all cursor-pointer whitespace-nowrap"
                  >
                    <span>🗑️</span>
                    <span>Clear All Chats</span>
                  </button>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: AI PREFERENCES */}
          {tab === 'preferences' && (
            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-xs font-semibold text-slate-200">
                  Response Language Style
                </label>
                <select
                  value={languagePref}
                  onChange={(e) => setLanguagePref(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-[#141820] px-3.5 py-2.5 text-xs text-white focus:border-amber-500/50 focus:outline-none cursor-pointer"
                >
                  <option value="auto">Auto-Detect (Respond in the query's language)</option>
                  <option value="hinglish">Hinglish (Conversational Hindi + English legal terms)</option>
                  <option value="hindi">Pure Hindi (हिंदी - विधिक शब्दावली)</option>
                  <option value="english">Formal English (High Court / Supreme Court style)</option>
                </select>
                <p className="text-[11px] text-slate-500 mt-1">
                  Controls how the AI translates statutes and explains complex legal provisions.
                </p>
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-semibold text-slate-200">
                  Target Audience & Depth
                </label>
                <select
                  value={audiencePref}
                  onChange={(e) => setAudiencePref(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-[#141820] px-3.5 py-2.5 text-xs text-white focus:border-amber-500/50 focus:outline-none cursor-pointer"
                >
                  <option value="citizen">Citizen & Student (Plain language, clear examples)</option>
                  <option value="professional">Legal Professional (Dense, citations & procedural nuance)</option>
                </select>
              </div>

              <div className="pt-2">
                <button
                  onClick={handleSavePreferences}
                  className="flex items-center gap-2 rounded-xl bg-amber-500/20 border border-amber-500/40 px-4 py-2 text-xs font-semibold text-amber-300 hover:bg-amber-500/30 transition-all cursor-pointer"
                >
                  <span>✓</span>
                  <span>Save Preferences</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between border-t border-white/10 px-6 py-3.5 bg-white/[0.02]">
          <span className="text-[11px] text-slate-500">
            🔒 All uploads are private and accessible only to your account
          </span>
          <button
            onClick={onClose}
            className="rounded-xl border border-white/15 bg-white/[0.05] px-4 py-1.5 text-xs font-medium text-slate-300 hover:bg-white/10 hover:text-white transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
