'use client'
import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { listCases, deleteCase, clearAllCases, CaseSummary } from '@/services/caseService'
import { clearAllSessions, listSessions } from '@/services/chatService'
import { useAuth } from '@/hooks/useAuth'

export default function PublicSettingsPage() {
  const { user, signOut } = useAuth()
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
    loadDocs()
    const savedLang = localStorage.getItem('nyaya_pref_language') || 'auto'
    const savedAud = localStorage.getItem('nyaya_pref_audience') || 'citizen'
    setLanguagePref(savedLang)
    setAudiencePref(savedAud)
  }, [])

  async function loadDocs() {
    setLoadingDocs(true)
    try {
      const data = await listCases()
      setDocs(Array.isArray(data) ? data : [])
    } catch (e) {
      console.error('[PublicSettingsPage] Failed to load documents:', e)
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
      showToast('Document deleted from your library')
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
      showToast('All uploaded documents cleared')
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
      showToast('All chat sessions cleared')
    } catch (e) {
      showToast('Failed to clear chats')
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
        userEmail: user?.email,
        platform: 'NyayaPramaan Legal Intelligence',
        documentsCount: docs.length,
        documents: docs.map((d) => ({ id: d.id, filename: d.filename, created_at: d.created_at, summary: d.summary })),
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
    showToast('Preferences updated successfully!')
  }

  const filteredDocs = docs.filter((d) =>
    (d.filename || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (d.summary || '').toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#E8E6E1] p-4 md:p-8 font-sans">
      {/* Toast */}
      {toastMessage && (
        <div className="fixed top-6 right-6 z-50 rounded-xl border border-amber-500/40 bg-[#141414] px-4 py-2.5 text-xs font-semibold text-amber-300 shadow-2xl backdrop-blur-xl animate-bounce">
          {toastMessage}
        </div>
      )}

      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-5">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Link
                href="/public/chat"
                className="text-xs text-slate-400 hover:text-amber-300 transition-colors no-underline flex items-center gap-1"
              >
                <span>← Back to AI Chat</span>
              </Link>
            </div>
            <h1 className="text-xl md:text-2xl font-bold text-white tracking-wide">
              Settings & Uploaded Document Library
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Manage your uploaded case files, privacy data, storage controls, and AI behavior.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleExportData}
              className="flex items-center gap-1.5 rounded-xl border border-white/15 bg-white/[0.04] px-3.5 py-2 text-xs font-medium text-slate-200 hover:bg-white/10 transition-all cursor-pointer"
            >
              <span>📥</span>
              <span>Export My Data</span>
            </button>
          </div>
        </div>

        {/* Section 1: Uploaded Document Library */}
        <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 md:p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-4">
            <div>
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <span>📁</span>
                <span>My Uploaded Case Documents ({docs.length})</span>
              </h2>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Files you uploaded for case analysis, court brief extraction, or citation verification.
              </p>
            </div>

            {docs.length > 0 && (
              <button
                onClick={() => setConfirmClearDocs(true)}
                className="flex items-center gap-1.5 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-300 hover:bg-red-500/20 transition-all cursor-pointer self-start sm:self-auto"
              >
                <span>🗑️</span>
                <span>Delete All Documents</span>
              </button>
            )}
          </div>

          {/* Confirm Clear All Banner */}
          {confirmClearDocs && (
            <div className="rounded-xl border border-red-500/40 bg-red-950/40 p-4 text-xs space-y-2.5">
              <div className="flex items-center gap-2 text-red-200 font-semibold">
                <span>⚠️</span>
                <span>Permanently Delete All {docs.length} Uploaded Files?</span>
              </div>
              <p className="text-[11px] text-red-300/80 leading-relaxed">
                This action will wipe all your documents, case summaries, and extracted text embeddings from our secure database.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={handleClearAllDocs}
                  disabled={actionLoading}
                  className="rounded-lg bg-red-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-red-500 transition-colors cursor-pointer"
                >
                  {actionLoading ? 'Deleting…' : 'Yes, Delete Everything'}
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

          {/* Search bar */}
          <div className="relative">
            <span className="absolute left-3 top-2.5 text-xs text-slate-500">🔍</span>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search uploaded files by name or content…"
              className="w-full rounded-xl border border-white/10 bg-[#141820] pl-8 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:border-amber-500/50 focus:outline-none"
            />
          </div>

          {/* Document List */}
          {loadingDocs ? (
            <div className="flex items-center justify-center py-12 text-xs text-slate-400 gap-2">
              <span className="animate-spin text-base">⏳</span>
              <span>Loading library…</span>
            </div>
          ) : filteredDocs.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 p-8 text-center space-y-2">
              <span className="text-3xl block">📄</span>
              <p className="text-xs text-slate-300 font-medium">No documents in your library</p>
              <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
                Attach case files in AI Chat or upload documents to query them and manage them here.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {filteredDocs.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3.5 hover:bg-white/[0.05] hover:border-white/20 transition-all"
                >
                  <div className="flex items-start gap-3 min-w-0 flex-1">
                    <span className="text-2xl mt-0.5">
                      {doc.filename?.endsWith('.pdf') ? '📕' : doc.filename?.endsWith('.docx') ? '📘' : '📄'}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-white truncate max-w-[340px]" title={doc.filename}>
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
                      <p className="text-[11px] text-slate-400 line-clamp-2 mt-1 leading-relaxed">
                        {doc.summary || 'Indexed for evidence grounding and citation retrieval'}
                      </p>
                      <span className="text-[10px] text-slate-500 mt-1 block">
                        Uploaded on: {doc.created_at ? new Date(doc.created_at).toLocaleString() : 'Recent'}
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDeleteSingleDoc(doc.id)}
                    disabled={deletingId === doc.id}
                    className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 text-slate-400 hover:border-red-500/40 hover:bg-red-500/10 hover:text-red-300 transition-colors cursor-pointer"
                    title="Delete document"
                  >
                    {deletingId === doc.id ? (
                      <span className="animate-spin text-xs">⏳</span>
                    ) : (
                      <span className="text-sm">🗑️</span>
                    )}
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Section 2: Privacy, Chat & Data Storage Controls */}
        <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 md:p-6 space-y-4">
          <div className="border-b border-white/10 pb-4">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <span>🗄️</span>
              <span>Data Controls & Storage Management</span>
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Control your chat logs, local bookmarks, and session history.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Clear Chats */}
            <div className="rounded-xl border border-red-500/20 bg-red-950/20 p-4 flex flex-col justify-between gap-3">
              <div>
                <h3 className="text-xs font-semibold text-red-300">Clear All Chat Conversations</h3>
                <p className="text-[11px] text-red-300/70 mt-1 leading-relaxed">
                  Permanently wipe all legal chat history threads from your account.
                </p>
              </div>
              {confirmClearChats ? (
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleClearAllChats}
                    disabled={actionLoading}
                    className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-500 transition-colors cursor-pointer"
                  >
                    {actionLoading ? 'Wiping…' : 'Confirm Delete'}
                  </button>
                  <button
                    onClick={() => setConfirmClearChats(false)}
                    className="rounded-lg border border-white/20 px-2 py-1.5 text-xs text-slate-400 hover:text-white cursor-pointer"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmClearChats(true)}
                  className="self-start rounded-xl border border-red-500/30 bg-red-500/10 px-3.5 py-1.5 text-xs font-medium text-red-300 hover:bg-red-500/20 transition-all cursor-pointer"
                >
                  Clear Chat History
                </button>
              )}
            </div>

            {/* Clear Bookmarks */}
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 flex flex-col justify-between gap-3">
              <div>
                <h3 className="text-xs font-semibold text-white">Clear Starred Answers</h3>
                <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                  Remove all bookmarked legal conclusions saved in your browser storage.
                </p>
              </div>
              {confirmClearBookmarks ? (
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleClearBookmarks}
                    className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-500 transition-colors cursor-pointer"
                  >
                    Confirm Clear
                  </button>
                  <button
                    onClick={() => setConfirmClearBookmarks(false)}
                    className="rounded-lg border border-white/20 px-2 py-1.5 text-xs text-slate-400 hover:text-white cursor-pointer"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmClearBookmarks(true)}
                  className="self-start rounded-xl border border-white/15 bg-white/[0.05] px-3.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-white/10 transition-all cursor-pointer"
                >
                  Clear Bookmarks
                </button>
              )}
            </div>
          </div>
        </section>

        {/* Section 3: AI Language & Response Preferences */}
        <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 md:p-6 space-y-4">
          <div className="border-b border-white/10 pb-4">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <span>🎛️</span>
              <span>AI Response Style & Language</span>
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Customize how NyayaPramaan AI structures legal explanations for your needs.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="mb-1.5 block text-xs font-semibold text-slate-300">
                Language Preference
              </label>
              <select
                value={languagePref}
                onChange={(e) => setLanguagePref(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-[#141820] px-3.5 py-2.5 text-xs text-white focus:border-amber-500/50 focus:outline-none cursor-pointer"
              >
                <option value="auto">Auto-Detect Query Language</option>
                <option value="hinglish">Hinglish (Hindi + English)</option>
                <option value="hindi">Pure Hindi (हिंदी विधिक)</option>
                <option value="english">Formal Legal English</option>
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-semibold text-slate-300">
                Target Audience Depth
              </label>
              <select
                value={audiencePref}
                onChange={(e) => setAudiencePref(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-[#141820] px-3.5 py-2.5 text-xs text-white focus:border-amber-500/50 focus:outline-none cursor-pointer"
              >
                <option value="citizen">Citizen & Student (Approachable & clear)</option>
                <option value="professional">Legal Advocate (Court-level depth & citations)</option>
              </select>
            </div>
          </div>

          <button
            onClick={handleSavePreferences}
            className="flex items-center gap-2 rounded-xl bg-amber-500/20 border border-amber-500/40 px-4 py-2 text-xs font-semibold text-amber-300 hover:bg-amber-500/30 transition-all cursor-pointer"
          >
            <span>✓</span>
            <span>Save Preferences</span>
          </button>
        </section>
      </div>
    </div>
  )
}
