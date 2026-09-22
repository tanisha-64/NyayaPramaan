'use client'
import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import { getCase, saveCaseNotes, getCaseBrief, CaseDetail, CaseBriefResponse } from '@/services/caseService'

export default function CaseWorkspacePage() {
  const { user, role, loading: authLoading, signOut } = useAuth()
  const router = useRouter()
  const params = useParams()
  const caseId = params?.id as string

  useEffect(() => {
    if (!authLoading && !user) router.push('/login?redirect=/app/dashboard')
  }, [authLoading, user, router])

  const [caseData, setCaseData] = useState<CaseDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'timeline' | 'document' | 'notes' | 'brief'>('timeline')
  
  // Notes State
  const [notes, setNotes] = useState('')
  const [savingNotes, setSavingNotes] = useState(false)
  const [notesSavedNotice, setNotesSavedNotice] = useState(false)

  // Case Brief State
  const [brief, setBrief] = useState<CaseBriefResponse | null>(null)
  const [loadingBrief, setLoadingBrief] = useState(false)
  const [copiedBrief, setCopiedBrief] = useState(false)

  // Document viewer search query
  const [docSearch, setDocSearch] = useState('')

  useEffect(() => {
    if (user && caseId && (role === 'professional' || role === 'admin')) {
      loadCaseData()
    }
  }, [user, caseId, role])

  async function loadCaseData() {
    setLoading(true)
    try {
      const data = await getCase(caseId)
      setCaseData(data)
      setNotes(data.notes || '')
    } catch (err) {
      console.error('Failed to load case:', err)
    }
    setLoading(false)
  }

  async function handleSaveNotes() {
    setSavingNotes(true)
    try {
      await saveCaseNotes(caseId, notes)
      setNotesSavedNotice(true)
      setTimeout(() => setNotesSavedNotice(false), 2500)
    } catch (err) {
      console.error('Failed to save notes:', err)
    }
    setSavingNotes(false)
  }

  async function handleLoadBrief() {
    setActiveTab('brief')
    if (brief) return
    setLoadingBrief(true)
    try {
      const res = await getCaseBrief(caseId)
      setBrief(res)
    } catch (err) {
      console.error('Failed to generate case brief:', err)
    }
    setLoadingBrief(false)
  }

  function handlePrintBrief() {
    window.print()
  }

  async function handleCopyBrief() {
    if (!brief?.brief_markdown) return
    try {
      await navigator.clipboard.writeText(brief.brief_markdown)
      setCopiedBrief(true)
      setTimeout(() => setCopiedBrief(false), 2000)
    } catch (err) {
      console.error(err)
    }
  }

  // Parse timeline if it's formatted text or bullet points
  const timelineEvents = caseData?.timeline
    ? caseData.timeline
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0)
    : []

  if (authLoading || (loading && (role === 'professional' || role === 'admin'))) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#050608] text-slate-400 font-sans text-sm">
        <div className="flex items-center gap-3">
          <span className="h-2.5 w-2.5 rounded-full bg-blue-500 animate-pulse-dot" />
          <span>Loading Case Workspace...</span>
        </div>
      </div>
    )
  }

  // Strict Account Isolation Guard
  if (user && role !== 'professional' && role !== 'admin') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-[#050608] px-6 text-center font-sans text-slate-200">
        <div className="mx-auto max-w-md rounded-2xl border border-amber-500/30 bg-gradient-to-b from-[#14120D] to-[#0A0D14] p-8 shadow-2xl">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-500/20 text-3xl text-amber-400 border border-amber-500/30">
            ⚖️
          </div>
          <h2 className="text-lg font-bold text-white">Professional Advocate Suite Only</h2>
          <p className="mt-2 text-xs leading-relaxed text-slate-400">
            Your account ({user.email}) is registered as a <span className="text-blue-400 font-semibold">Citizen / Student</span>. 
            Detailed case files, procedural timelines, and Case Brief exports are exclusive to Advocate accounts.
          </p>
          <div className="mt-6 flex flex-col gap-3">
            <Link
              href="/public/chat"
              className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 py-2.5 text-xs font-semibold text-white hover:brightness-110 transition-all no-underline shadow-md"
            >
              Go to Citizen AI Research Chat →
            </Link>
            <button
              onClick={signOut}
              className="rounded-xl border border-white/10 bg-white/[0.04] py-2.5 text-xs font-medium text-slate-400 hover:bg-white/[0.08] hover:text-white transition-all cursor-pointer"
            >
              Sign Out / Switch Account
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!caseData) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-[#050608] text-slate-300 font-sans p-6 text-center">
        <h2 className="text-xl font-semibold text-white">Case Not Found</h2>
        <p className="mt-2 text-sm text-slate-400">The requested case file could not be retrieved.</p>
        <Link
          href="/app/dashboard"
          className="mt-6 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-500"
        >
          Return to Dashboard
        </Link>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#050608] text-slate-100 font-sans antialiased">
      {/* Top Professional Navigation */}
      <header className="border-b border-white/[0.08] bg-[#07080D]/90 backdrop-blur-2xl sticky top-0 z-30">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3.5">
          <div className="flex items-center gap-3">
            <Link href="/app/dashboard" className="text-slate-400 hover:text-white transition-colors flex items-center gap-1 text-xs">
              <span>←</span>
              <span>Back to Cases</span>
            </Link>
            <span className="text-slate-600">|</span>
            <div className="flex items-center gap-2">
              <span className="text-base">⚖️</span>
              <span className="text-sm font-semibold tracking-tight text-white truncate max-w-sm">
                {caseData.filename || 'Case Workspace'}
              </span>
              <span className="rounded-full bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 text-[10px] font-medium text-blue-400">
                Workspace
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleLoadBrief}
              className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-[#B8925A] via-[#C89B59] to-[#D4A368] px-3.5 py-1.5 text-xs font-semibold text-slate-950 hover:brightness-110 transition-all cursor-pointer shadow-sm"
            >
              <span>📄</span>
              <span>Export Case Brief</span>
            </button>
            <button
              onClick={signOut}
              className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/20 transition-all cursor-pointer"
            >
              Sign Out
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <main className="mx-auto max-w-7xl px-6 py-8">
        {/* Case Header Hero Banner */}
        <div className="rounded-2xl border border-white/[0.08] bg-gradient-to-r from-[#0F121C] via-[#0D1017] to-[#0A0D14] p-6 shadow-xl mb-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <span className="text-[11px] font-medium uppercase tracking-wider text-amber-400/90">
                Case Intelligence Dossier
              </span>
              <h1 className="mt-1 text-xl font-bold tracking-tight text-white">
                {caseData.filename || 'Case Document'}
              </h1>
              <p className="mt-1 text-xs text-slate-400">
                Uploaded on {new Date(caseData.created_at).toLocaleDateString(undefined, { dateStyle: 'long' })}
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setActiveTab('timeline')}
                className={`rounded-xl px-3.5 py-2 text-xs font-medium transition-all cursor-pointer ${
                  activeTab === 'timeline'
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-white/[0.04] text-slate-300 hover:bg-white/[0.08]'
                }`}
              >
                ⏳ Visual Timeline
              </button>
              <button
                onClick={() => setActiveTab('document')}
                className={`rounded-xl px-3.5 py-2 text-xs font-medium transition-all cursor-pointer ${
                  activeTab === 'document'
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-white/[0.04] text-slate-300 hover:bg-white/[0.08]'
                }`}
              >
                📖 Document Viewer
              </button>
              <button
                onClick={() => setActiveTab('notes')}
                className={`rounded-xl px-3.5 py-2 text-xs font-medium transition-all cursor-pointer ${
                  activeTab === 'notes'
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-white/[0.04] text-slate-300 hover:bg-white/[0.08]'
                }`}
              >
                📝 Lawyer Notes {notes ? '•' : ''}
              </button>
              <button
                onClick={handleLoadBrief}
                className={`rounded-xl px-3.5 py-2 text-xs font-medium transition-all cursor-pointer ${
                  activeTab === 'brief'
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-white/[0.04] text-slate-300 hover:bg-white/[0.08]'
                }`}
              >
                ⚖️ AI Case Brief
              </button>
            </div>
          </div>

          {/* AI Summary Highlight */}
          <div className="mt-5 rounded-xl border border-white/[0.06] bg-black/30 p-4">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Executive AI Summary:
            </span>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-200">
              {caseData.summary || 'Summary generated during indexing.'}
            </p>
          </div>
        </div>

        {/* Tab 1: Visual Timeline */}
        {activeTab === 'timeline' && (
          <div className="rounded-2xl border border-white/[0.08] bg-[#0A0D14] p-6 shadow-xl">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">Chronological Case Timeline</h2>
                <p className="text-xs text-slate-400">Extracted sequence of key procedural steps, FIRs, notices, and hearings.</p>
              </div>
            </div>

            {timelineEvents.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500">
                No explicit chronological dates found in this document.
              </div>
            ) : (
              <div className="relative border-l-2 border-blue-500/30 ml-4 space-y-6 py-2">
                {timelineEvents.map((event, idx) => (
                  <div key={idx} className="relative pl-6 group">
                    {/* Timeline node icon */}
                    <div className="absolute -left-[9px] top-1.5 h-4 w-4 rounded-full border-2 border-blue-500 bg-[#0A0D14] group-hover:bg-blue-500 transition-colors" />
                    
                    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 transition-all group-hover:border-blue-500/30 group-hover:bg-white/[0.04]">
                      <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-400">
                        Event #{idx + 1}
                      </span>
                      <p className="mt-1 text-xs leading-relaxed text-slate-200 font-normal">
                        {event}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Document Viewer */}
        {activeTab === 'document' && (
          <div className="rounded-2xl border border-white/[0.08] bg-[#0A0D14] p-6 shadow-xl">
            <div className="mb-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-white">Document Reader & Search</h2>
                <p className="text-xs text-slate-400">Full extracted text of the uploaded case record.</p>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={docSearch}
                  onChange={(e) => setDocSearch(e.target.value)}
                  placeholder="Search in document..."
                  className="rounded-xl border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs text-white placeholder:text-slate-500 outline-none focus:border-blue-500"
                />
                {docSearch && (
                  <button
                    onClick={() => setDocSearch('')}
                    className="text-xs text-slate-400 hover:text-white"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>

            <div className="max-h-[600px] overflow-y-auto rounded-xl border border-white/[0.06] bg-black/40 p-5 font-mono text-xs leading-relaxed text-slate-300 whitespace-pre-wrap">
              {caseData.case_text || 'No raw text content available.'}
            </div>
          </div>
        )}

        {/* Tab 3: Lawyer Notes & Annotation Pad */}
        {activeTab === 'notes' && (
          <div className="rounded-2xl border border-white/[0.08] bg-[#0A0D14] p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">Lawyer Scratchpad & Private Notes</h2>
                <p className="text-xs text-slate-400">
                  Securely stored notes for client strategy, witness points, and cross-examination notes.
                </p>
              </div>

              <div className="flex items-center gap-3">
                {notesSavedNotice && (
                  <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1">
                    ✓ Saved successfully
                  </span>
                )}
                <button
                  onClick={handleSaveNotes}
                  disabled={savingNotes}
                  className="rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50 transition-all cursor-pointer shadow-md"
                >
                  {savingNotes ? 'Saving...' : 'Save Notes'}
                </button>
              </div>
            </div>

            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={16}
              placeholder="Type client background, hearing prep, sections to invoke, precedent references..."
              className="w-full rounded-xl border border-white/10 bg-black/30 p-4 font-sans text-sm leading-relaxed text-slate-100 placeholder:text-slate-500 outline-none focus:border-blue-500/60 focus:ring-1 focus:ring-blue-500/30"
            />
          </div>
        )}

        {/* Tab 4: AI Case Brief & Export */}
        {activeTab === 'brief' && (
          <div className="rounded-2xl border border-white/[0.08] bg-[#0A0D14] p-6 shadow-xl">
            <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-white/[0.08] pb-4">
              <div>
                <h2 className="text-lg font-bold text-white">Executive Case Brief</h2>
                <p className="text-xs text-slate-400">
                  Standardized legal briefing: Facts, Issues, Statutes, Ratio Decidendi, and Disposition.
                </p>
              </div>

              <div className="flex items-center gap-2 print:hidden">
                <button
                  onClick={handleCopyBrief}
                  className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.04] px-3.5 py-2 text-xs text-slate-200 hover:bg-white/[0.08] transition-all cursor-pointer"
                >
                  <span>{copiedBrief ? '✓ Copied' : '📋 Copy Markdown'}</span>
                </button>
                <button
                  onClick={handlePrintBrief}
                  className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-[#B8925A] via-[#C89B59] to-[#D4A368] px-4 py-2 text-xs font-semibold text-slate-950 hover:brightness-110 transition-all cursor-pointer shadow-md"
                >
                  <span>🖨️</span>
                  <span>Print / Save PDF</span>
                </button>
              </div>
            </div>

            {loadingBrief ? (
              <div className="py-16 flex flex-col items-center justify-center text-center">
                <span className="h-3 w-3 rounded-full bg-amber-400 animate-pulse-dot mb-3" />
                <span className="text-sm text-slate-300 font-medium">Synthesizing comprehensive legal case brief...</span>
                <span className="text-xs text-slate-500 mt-1">Analyzing facts, ratio decidendi, and statutory provisions.</span>
              </div>
            ) : brief ? (
              <div className="prose prose-invert max-w-none rounded-xl bg-black/30 p-6 text-sm text-slate-200 leading-relaxed font-sans border border-white/[0.04] whitespace-pre-wrap">
                {brief.brief_markdown}
              </div>
            ) : (
              <div className="py-12 text-center text-xs text-slate-400">
                Click "Export Case Brief" to generate a complete legal brief.
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
