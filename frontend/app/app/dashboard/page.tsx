'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import { RoleGuard } from '@/components/auth/RoleGuard'
import { listCases, CaseSummary, deleteCase } from '@/services/caseService'
import { searchPrecedents, PrecedentResult, SearchFilters } from '@/services/searchService'
import { uploadDocument, ACCEPTED_FORMATS, validateFileType } from '@/services/documentService'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

const COURTS = [
  'All Courts',
  'Supreme Court of India',
  'Delhi High Court',
  'Bombay High Court',
  'Allahabad High Court',
  'Madras High Court',
  'Calcutta High Court',
  'Karnataka High Court',
]

const QUICK_TOPICS = [
  'Section 304A IPC Medical Negligence',
  'Anticipatory Bail Grounds under BNSS',
  'Specific Performance of Contract Limitation',
  'Cheque Bounce Section 138 NI Act Notice',
]

function ProfessionalDashboardContent() {
  const { user, role, signOut } = useAuth()

  const [cases, setCases] = useState<CaseSummary[]>([])
  const [loadingCases, setLoadingCases] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)

  // Filterable Precedent Search state
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCourt, setSelectedCourt] = useState('All Courts')
  const [jurisdictionFilter, setJurisdictionFilter] = useState<'all' | 'binding' | 'persuasive'>('all')
  const [yearFrom, setYearFrom] = useState<string>('')
  const [yearTo, setYearTo] = useState<string>('')
  const [searchResults, setSearchResults] = useState<PrecedentResult[]>([])
  const [searching, setSearching] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  useEffect(() => {
    if (user) refreshCases()
  }, [user])

  // Auto-refresh when any case is still processing
  useEffect(() => {
    const hasProcessing = cases.some((c) => c.status === 'processing')
    if (!hasProcessing) return
    const interval = setInterval(() => {
      refreshCases()
    }, 3000)
    return () => clearInterval(interval)
  }, [cases])

  async function refreshCases() {
    setLoadingCases(true)
    try {
      const list = await listCases()
      setCases(Array.isArray(list) ? list : [])
    } catch (err) {
      console.error(err)
    }
    setLoadingCases(false)
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file before upload
    const validationError = validateFileType(file)
    if (validationError) {
      alert(validationError)
      e.target.value = ''
      return
    }

    setUploading(true)
    try {
      await uploadDocument(file)
      // Refresh immediately — case will show as "processing", then update via list polling
      await refreshCases()
    } catch (err: any) {
      const rawMsg: string = err?.message || 'Upload failed — please check document and backend connection.'
      let msg = rawMsg
      if (rawMsg.includes('Cannot reach the server') || rawMsg.includes('fetch')) {
        msg = 'Cannot reach the backend server. Please ensure the server is running at http://127.0.0.1:8000 and try again.'
      } else if (rawMsg.includes('Unsupported file format')) {
        msg = rawMsg
      } else if (rawMsg.includes('too large')) {
        msg = rawMsg
      }
      alert(`Upload Notice: ${msg}`)
    }
    setUploading(false)
    e.target.value = ''
  }

  async function handleDelete(id: string) {
    await deleteCase(id)
    setConfirmDeleteId(null)
    refreshCases()
  }

  async function handleSearch(overrideQuery?: string) {
    const q = overrideQuery ?? searchQuery
    if (!q.trim()) return
    if (overrideQuery) setSearchQuery(overrideQuery)
    setSearching(true)
    setHasSearched(true)
    try {
      const filters: SearchFilters = {
        query: q,
        court: selectedCourt === 'All Courts' ? undefined : selectedCourt,
        jurisdiction_type: jurisdictionFilter === 'all' ? undefined : jurisdictionFilter,
        year_from: yearFrom ? parseInt(yearFrom, 10) : undefined,
        year_to: yearTo ? parseInt(yearTo, 10) : undefined,
      }
      const res = await searchPrecedents(filters)
      setSearchResults(res.results || [])
    } catch {
      setSearchResults([])
    }
    setSearching(false)
  }

  return (
    <div className="min-h-screen bg-[#0F1B2E] text-slate-100 font-sans antialiased">
      {/* Top Professional Header — Navy Theme with Blue Accent */}
      <header className="border-b border-[#2B5CE0]/15 bg-[#0C1624]/90 backdrop-blur-2xl sticky top-0 z-30">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3.5 flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2.5 text-white no-underline">
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-[#2B5CE0]/25 via-[#2B5CE0]/15 to-transparent border border-[#2B5CE0]/25 text-sm">
                ⚖️
              </span>
              <span className="text-base font-semibold tracking-tight">NyayaPramaan</span>
            </Link>
            <span className="rounded-full bg-[#2B5CE0]/15 border border-[#2B5CE0]/25 px-2.5 py-0.5 text-[10px] font-semibold text-[#5B8DEF]">
              Professional Suite
            </span>
          </div>

          <nav className="flex items-center gap-4 text-xs font-medium text-slate-300">
            <Link href="/public/chat" className="hover:text-white transition-colors">
              AI Research Chat
            </Link>
            <Link href="/app/dashboard" className="text-[#5B8DEF] font-semibold">
              Case Workspace
            </Link>
            <Link href="/game" className="hover:text-white transition-colors">
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
            <button
              onClick={signOut}
              className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-1 text-xs text-red-400 hover:bg-red-500/20 transition-all cursor-pointer"
            >
              Sign Out
            </button>
          </nav>
        </div>
      </header>

      {/* Main Container */}
      <main className="mx-auto max-w-7xl px-6 py-8">
        {/* Workspace Title & Stats Banner — Navy theme */}
        <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4 rounded-2xl border border-[#2B5CE0]/15 bg-gradient-to-r from-[#0C1624] via-[#0F1B2E] to-[#0C1624] p-6 shadow-xl">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#5B8DEF]">
              Practicing Advocate & Researcher Console
            </span>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-white">
              Case Intelligence & Precedent Discovery
            </h1>
            <p className="mt-1 text-xs text-slate-400 max-w-xl leading-relaxed">
              Manage client dossiers, generate executive case briefs, explore visual timelines, and query binding Supreme Court vs persuasive High Court authorities.
            </p>
          </div>

          <label className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#2B5CE0] to-[#4F7AF7] px-5 py-3 text-xs font-semibold text-white transition-all hover:brightness-110 shadow-lg cursor-pointer self-start md:self-auto">
            <span>{uploading ? '⏳ Indexing Case...' : '+ Ingest Case Dossier'}</span>
            <input
              type="file"
              accept={ACCEPTED_FORMATS}
              onChange={handleUpload}
              className="hidden"
              disabled={uploading}
            />
          </label>
        </div>

        {/* 2-Column Split: Cases on Left, Precedents on Right */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Active Cases Library */}
          <section className="lg:col-span-5 space-y-4">
            <div className="flex items-center justify-between pb-1 border-b border-[#2B5CE0]/15">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold uppercase tracking-wider text-white">
                  Active Case Files
                </h2>
                <span className="rounded-full bg-[#2B5CE0]/15 px-2 py-0.5 text-[10px] text-[#5B8DEF] font-semibold">
                  {cases.length}
                </span>
              </div>
            </div>

            {loadingCases && (
              <div className="py-12 text-center text-xs text-slate-400">
                <span className="h-2 w-2 rounded-full bg-[#2B5CE0] animate-pulse-dot inline-block mr-2" />
                Loading your case files...
              </div>
            )}

            {!loadingCases && cases.length === 0 && (
              <div className="rounded-2xl border border-[#2B5CE0]/10 bg-[#2B5CE0]/[0.04] p-8 text-center">
                <span className="text-3xl">📁</span>
                <p className="mt-3 text-xs font-medium text-slate-300">No active cases uploaded</p>
                <p className="mt-1 text-[11px] text-slate-400">
                  Upload a PDF, DOCX, or image file to view timelines, extracts, and case briefs.
                </p>
              </div>
            )}

            <div className="space-y-3">
              {cases.map((c) => (
                <div
                  key={c.id}
                  className="group relative rounded-2xl border border-[#2B5CE0]/12 bg-gradient-to-b from-[#0C1624]/90 to-[#0F1B2E]/90 p-5 shadow-lg transition-all hover:border-[#2B5CE0]/40 hover:bg-[#121E38]"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm">📄</span>
                        <h3 className="text-xs font-bold text-white group-hover:text-[#5B8DEF] transition-colors truncate max-w-[240px]">
                          {c.filename || 'Case Record'}
                        </h3>
                        {c.status && c.status !== 'ready' && (
                          <span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold border ${
                            c.status === 'processing'
                              ? 'bg-amber-500/10 border-amber-500/30 text-amber-300 animate-pulse'
                              : c.status === 'rejected'
                              ? 'bg-red-500/10 border-red-500/30 text-red-300'
                              : c.status === 'failed'
                              ? 'bg-red-500/10 border-red-500/30 text-red-400'
                              : 'bg-slate-500/10 border-slate-500/30 text-slate-400'
                          }`}>
                            {c.status === 'processing' ? '⏳ Processing' : c.status === 'rejected' ? '⚠ Rejected' : c.status === 'failed' ? '✕ Failed' : c.status}
                          </span>
                        )}
                      </div>
                      <p className="mt-2 text-xs leading-relaxed text-slate-300 line-clamp-3">
                        {c.status === 'rejected'
                          ? 'This document was not identified as a legal case file.'
                          : c.status === 'processing'
                          ? 'Analyzing document, extracting text and building index...'
                          : c.summary || 'Indexing extracted facts & chronological timeline...'}
                      </p>
                    </div>

                    <button
                      onClick={() => setConfirmDeleteId(c.id)}
                      className="text-slate-400 hover:text-red-400 transition-colors p-1"
                      title="Delete Case"
                    >
                      🗑
                    </button>
                  </div>

                  <div className="mt-4 flex items-center justify-between border-t border-[#2B5CE0]/10 pt-3 text-[11px]">
                    <span className="text-slate-400">
                      {new Date(c.created_at).toLocaleDateString()}
                    </span>

                    <div className="flex items-center gap-2">
                      <Link
                        href={`/app/cases/${c.id}`}
                        className="flex items-center gap-1 rounded-lg bg-[#2B5CE0]/20 border border-[#2B5CE0]/30 px-3 py-1 text-[11px] font-semibold text-[#5B8DEF] hover:bg-[#2B5CE0] hover:text-white transition-all no-underline"
                      >
                        <span>Open Workspace</span>
                        <span>→</span>
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Right Column: Precedent Research Engine with Filters */}
          <section className="lg:col-span-7 space-y-4">
            <div className="pb-1 border-b border-[#2B5CE0]/15 flex items-center justify-between">
              <h2 className="text-sm font-bold uppercase tracking-wider text-white">
                Filterable Precedent & Statute Search
              </h2>
              <span className="text-[11px] text-[#5B8DEF]">
                Hybrid Semantic + Keyword
              </span>
            </div>

            {/* Filter Bar Controls — Blue themed */}
            <div className="rounded-2xl border border-[#2B5CE0]/12 bg-[#0C1624] p-4 shadow-lg space-y-3">
              {/* Search Bar */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="Enter legal issue, statute, or landmark case name..."
                  className="flex-1 rounded-xl border border-[#2B5CE0]/20 bg-[#0F1B2E]/80 px-4 py-2.5 text-xs text-white placeholder:text-slate-400 outline-none focus:border-[#2B5CE0] focus:ring-1 focus:ring-[#2B5CE0]/40"
                />
                <button
                  onClick={() => handleSearch()}
                  disabled={searching || !searchQuery.trim()}
                  className="flex items-center gap-1.5 rounded-xl bg-[#2B5CE0] px-5 py-2.5 text-xs font-semibold text-white hover:bg-[#3D6CF0] disabled:opacity-40 transition-all cursor-pointer shadow-md"
                >
                  {searching ? (
                    <span className="flex items-center gap-1">
                      <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse" />
                      Searching...
                    </span>
                  ) : (
                    'Search Precedents'
                  )}
                </button>
              </div>

              {/* Advanced Filters: Court, Jurisdiction, Year */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1 text-xs">
                {/* Court Filter */}
                <div>
                  <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Court Jurisdiction
                  </label>
                  <select
                    value={selectedCourt}
                    onChange={(e) => setSelectedCourt(e.target.value)}
                    className="w-full rounded-lg border border-[#2B5CE0]/20 bg-[#0F1B2E]/80 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-[#2B5CE0]"
                  >
                    {COURTS.map((court) => (
                      <option key={court} value={court} className="bg-[#0C1624]">
                        {court}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Jurisdiction Type (Binding vs Persuasive) */}
                <div>
                  <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Authority Type
                  </label>
                  <select
                    value={jurisdictionFilter}
                    onChange={(e) => setJurisdictionFilter(e.target.value as any)}
                    className="w-full rounded-lg border border-[#2B5CE0]/20 bg-[#0F1B2E]/80 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-[#2B5CE0]"
                  >
                    <option value="all" className="bg-[#0C1624]">All Authorities</option>
                    <option value="binding" className="bg-[#0C1624]">✅ Binding Only (SC)</option>
                    <option value="persuasive" className="bg-[#0C1624]">⚠️ Persuasive Only (HCs)</option>
                  </select>
                </div>

                {/* Year Range */}
                <div>
                  <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Year Range
                  </label>
                  <div className="flex items-center gap-1.5">
                    <input
                      type="number"
                      placeholder="From"
                      value={yearFrom}
                      onChange={(e) => setYearFrom(e.target.value)}
                      className="w-full rounded-lg border border-[#2B5CE0]/20 bg-[#0F1B2E]/80 px-2 py-1.5 text-xs text-slate-200 placeholder:text-slate-400 outline-none focus:border-[#2B5CE0]"
                    />
                    <span className="text-slate-400">-</span>
                    <input
                      type="number"
                      placeholder="To"
                      value={yearTo}
                      onChange={(e) => setYearTo(e.target.value)}
                      className="w-full rounded-lg border border-[#2B5CE0]/20 bg-[#0F1B2E]/80 px-2 py-1.5 text-xs text-slate-200 placeholder:text-slate-400 outline-none focus:border-[#2B5CE0]"
                    />
                  </div>
                </div>
              </div>

              {/* Starter Quick Topic Chips */}
              <div className="pt-2 border-t border-[#2B5CE0]/10">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block mb-1.5">
                  Suggested Research Topics:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {QUICK_TOPICS.map((topic, i) => (
                    <button
                      key={i}
                      onClick={() => handleSearch(topic)}
                      className="rounded-full border border-[#2B5CE0]/15 bg-[#2B5CE0]/[0.06] px-2.5 py-1 text-[11px] text-slate-300 hover:border-[#2B5CE0]/40 hover:bg-[#2B5CE0]/15 hover:text-white transition-all cursor-pointer"
                    >
                      {topic}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Precedent Results Stream */}
            <div className="space-y-3">
              {searching && (
                <div className="py-12 text-center text-xs text-slate-400">
                  <span className="h-2 w-2 rounded-full bg-[#2B5CE0] animate-pulse-dot inline-block mr-2" />
                  Querying vector database and statutory provisions...
                </div>
              )}

              {!searching && hasSearched && searchResults.length === 0 && (
                <div className="rounded-2xl border border-[#2B5CE0]/10 bg-[#2B5CE0]/[0.04] p-8 text-center">
                  <span className="text-3xl">⚖️</span>
                  <p className="mt-3 text-xs font-medium text-slate-300">No matching precedents found</p>
                  <p className="mt-1 text-[11px] text-slate-400">
                    Try broadening your search query or removing court/year filters.
                  </p>
                </div>
              )}

              {!searching &&
                searchResults.map((r, i) => (
                  <div
                    key={i}
                    className="rounded-2xl border border-[#2B5CE0]/12 bg-gradient-to-b from-[#0C1624] to-[#0F1B2E] p-5 shadow-lg space-y-2.5 transition-all hover:border-[#2B5CE0]/30"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h4 className="text-xs font-bold text-white tracking-wide">
                          {r.display_name || r.case_name}
                        </h4>
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
                          {r.court && <span>🏛️ {r.court}</span>}
                          {r.year && <span>📅 ({r.year})</span>}
                        </div>
                      </div>

                      {r.jurisdiction_type && (
                        <span
                          className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold border ${
                            r.jurisdiction_type === 'binding'
                              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                              : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                          }`}
                        >
                          {r.jurisdiction_type === 'binding' ? '✅ Binding Precedent' : '⚠️ Persuasive Precedent'}
                        </span>
                      )}
                    </div>

                    <p className="text-xs leading-relaxed text-slate-300 font-mono bg-[#0F1B2E]/80 p-3 rounded-xl border border-[#2B5CE0]/08">
                      {r.full_text?.slice(0, 320)}...
                    </p>
                  </div>
                ))}
            </div>
          </section>
        </div>
      </main>

      {/* Delete Confirmation Modal */}
      <ConfirmDialog
        open={!!confirmDeleteId}
        title="Delete this case dossier?"
        message="This will permanently delete the case summary, timeline, and associated vector chunks."
        onConfirm={() => confirmDeleteId && handleDelete(confirmDeleteId)}
        onCancel={() => setConfirmDeleteId(null)}
      />
    </div>
  )
}

export default function ProfessionalDashboard() {
  return (
    <RoleGuard allowedRole="professional">
      <ProfessionalDashboardContent />
    </RoleGuard>
  )
}