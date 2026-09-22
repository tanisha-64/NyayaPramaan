'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import { listCases, CaseSummary, deleteCase } from '@/services/caseService'
import { searchPrecedents, PrecedentResult, SearchFilters } from '@/services/searchService'
import { uploadDocument } from '@/services/documentService'
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

export default function ProfessionalDashboard() {
  const { user, role, loading: authLoading, signOut } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!authLoading && !user) router.push('/login?redirect=/app/dashboard')
  }, [authLoading, user, router])

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
    if (user && (role === 'professional' || role === 'admin')) refreshCases()
  }, [user, role])

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
    setUploading(true)
    try {
      await uploadDocument(file)
      await refreshCases()
    } catch (err: any) {
      const msg = err?.message || 'Upload failed — please check document and backend connection.'
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

  if (authLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#050608] text-slate-400 font-sans text-sm">
        <div className="flex items-center gap-3">
          <span className="h-2.5 w-2.5 rounded-full bg-blue-500 animate-pulse-dot" />
          <span>Authenticating NyayaPramaan Workspace...</span>
        </div>
      </div>
    )
  }

  // Strict Account Isolation Guard: Prevent Citizen/Student role from accessing Advocate Workspace
  if (role !== 'professional' && role !== 'admin') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-[#050608] px-6 text-center font-sans text-slate-200">
        <div className="mx-auto max-w-md rounded-2xl border border-amber-500/30 bg-gradient-to-b from-[#14120D] to-[#0A0D14] p-8 shadow-2xl">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-500/20 text-3xl text-amber-400 border border-amber-500/30">
            ⚖️
          </div>
          <h2 className="text-lg font-bold text-white">Professional Advocate Suite Only</h2>
          <p className="mt-2 text-xs leading-relaxed text-slate-400">
            Your account ({user.email}) is registered as a <span className="text-blue-400 font-semibold">Citizen / Student</span>. 
            The Professional Workspace with multi-case dossiers, visual procedural timelines, and Case Brief export is reserved for Advocate & Legal Researcher accounts.
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

  return (
    <div className="min-h-screen bg-[#050608] text-slate-100 font-sans antialiased">
      {/* Top Professional Header */}
      <header className="border-b border-white/[0.08] bg-[#07080D]/90 backdrop-blur-2xl sticky top-0 z-30">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3.5 flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2.5 text-white no-underline">
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-500/20 via-blue-500/15 to-transparent border border-white/10 text-sm">
                ⚖️
              </span>
              <span className="text-base font-semibold tracking-tight">NyayaPramaan</span>
            </Link>
            <span className="rounded-full bg-amber-500/15 border border-amber-500/25 px-2.5 py-0.5 text-[10px] font-semibold text-amber-300">
              Professional Suite
            </span>
          </div>

          <nav className="flex items-center gap-4 text-xs font-medium text-slate-300">
            <Link href="/public/chat" className="hover:text-white transition-colors">
              AI Research Chat
            </Link>
            <Link href="/app/dashboard" className="text-white font-semibold">
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
        {/* Workspace Title & Stats Banner */}
        <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4 rounded-2xl border border-white/[0.08] bg-gradient-to-r from-[#0F121C] via-[#0D1017] to-[#0A0D14] p-6 shadow-xl">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-400">
              Practicing Advocate & Researcher Console
            </span>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-white">
              Case Intelligence & Precedent Discovery
            </h1>
            <p className="mt-1 text-xs text-slate-400 max-w-xl leading-relaxed">
              Manage client dossiers, generate executive case briefs, explore visual timelines, and query binding Supreme Court vs persuasive High Court authorities.
            </p>
          </div>

          <label className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#B8925A] via-[#C89B59] to-[#D4A368] px-5 py-3 text-xs font-semibold text-slate-950 transition-all hover:brightness-110 shadow-lg cursor-pointer self-start md:self-auto">
            <span>{uploading ? '⏳ Indexing Case...' : '+ Ingest Case Dossier'}</span>
            <input
              type="file"
              accept=".pdf"
              onChange={handleUpload}
              className="hidden"
              disabled={uploading}
            />
          </label>
        </div>

        {/* 2-Column Split: Cases on Left (1.1fr), Precedents on Right (1.3fr) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Active Cases Library */}
          <section className="lg:col-span-5 space-y-4">
            <div className="flex items-center justify-between pb-1 border-b border-white/[0.08]">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold uppercase tracking-wider text-white">
                  Active Case Files
                </h2>
                <span className="rounded-full bg-white/[0.08] px-2 py-0.5 text-[10px] text-slate-400 font-semibold">
                  {cases.length}
                </span>
              </div>
            </div>

            {loadingCases && (
              <div className="py-12 text-center text-xs text-slate-400">
                <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse-dot inline-block mr-2" />
                Loading your case files...
              </div>
            )}

            {!loadingCases && cases.length === 0 && (
              <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-8 text-center">
                <span className="text-3xl">📁</span>
                <p className="mt-3 text-xs font-medium text-slate-300">No active cases uploaded</p>
                <p className="mt-1 text-[11px] text-slate-400">
                  Upload a PDF petition or judgment to view timelines, extracts, and case briefs.
                </p>
              </div>
            )}

            <div className="space-y-3">
              {cases.map((c) => (
                <div
                  key={c.id}
                  className="group relative rounded-2xl border border-white/[0.08] bg-gradient-to-b from-[#121520]/90 to-[#0C0E15]/90 p-5 shadow-lg transition-all hover:border-blue-500/40 hover:bg-[#151928]"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm">📄</span>
                        <h3 className="text-xs font-bold text-white group-hover:text-blue-400 transition-colors truncate max-w-[240px]">
                          {c.filename || 'Case Record'}
                        </h3>
                      </div>
                      <p className="mt-2 text-xs leading-relaxed text-slate-300 line-clamp-3">
                        {c.summary || 'Indexing extracted facts & chronological timeline...'}
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

                  <div className="mt-4 flex items-center justify-between border-t border-white/[0.06] pt-3 text-[11px]">
                    <span className="text-slate-400">
                      {new Date(c.created_at).toLocaleDateString()}
                    </span>

                    <div className="flex items-center gap-2">
                      <Link
                        href={`/app/cases/${c.id}`}
                        className="flex items-center gap-1 rounded-lg bg-blue-600/20 border border-blue-500/30 px-3 py-1 text-[11px] font-semibold text-blue-300 hover:bg-blue-600 hover:text-white transition-all no-underline"
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
            <div className="pb-1 border-b border-white/[0.08] flex items-center justify-between">
              <h2 className="text-sm font-bold uppercase tracking-wider text-white">
                Filterable Precedent & Statute Search
              </h2>
              <span className="text-[11px] text-slate-400">
                Hybrid Semantic + Keyword
              </span>
            </div>

            {/* Filter Bar Controls */}
            <div className="rounded-2xl border border-white/[0.08] bg-[#0E111A] p-4 shadow-lg space-y-3">
              {/* Search Bar */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="Enter legal issue, statute, or landmark case name..."
                  className="flex-1 rounded-xl border border-white/10 bg-black/40 px-4 py-2.5 text-xs text-white placeholder:text-slate-400 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/40"
                />
                <button
                  onClick={() => handleSearch()}
                  disabled={searching || !searchQuery.trim()}
                  className="flex items-center gap-1.5 rounded-xl bg-blue-600 px-5 py-2.5 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-40 transition-all cursor-pointer shadow-md"
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
                    className="w-full rounded-lg border border-white/10 bg-black/40 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-blue-500"
                  >
                    {COURTS.map((court) => (
                      <option key={court} value={court} className="bg-[#0D1017]">
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
                    className="w-full rounded-lg border border-white/10 bg-black/40 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-blue-500"
                  >
                    <option value="all" className="bg-[#0D1017]">All Authorities</option>
                    <option value="binding" className="bg-[#0D1017]">✅ Binding Only (SC)</option>
                    <option value="persuasive" className="bg-[#0D1017]">⚠️ Persuasive Only (HCs)</option>
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
                      className="w-full rounded-lg border border-white/10 bg-black/40 px-2 py-1.5 text-xs text-slate-200 placeholder:text-slate-400 outline-none focus:border-blue-500"
                    />
                    <span className="text-slate-400">-</span>
                    <input
                      type="number"
                      placeholder="To"
                      value={yearTo}
                      onChange={(e) => setYearTo(e.target.value)}
                      className="w-full rounded-lg border border-white/10 bg-black/40 px-2 py-1.5 text-xs text-slate-200 placeholder:text-slate-400 outline-none focus:border-blue-500"
                    />
                  </div>
                </div>
              </div>

              {/* Starter Quick Topic Chips */}
              <div className="pt-2 border-t border-white/[0.04]">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block mb-1.5">
                  Suggested Research Topics:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {QUICK_TOPICS.map((topic, i) => (
                    <button
                      key={i}
                      onClick={() => handleSearch(topic)}
                      className="rounded-full border border-white/[0.08] bg-white/[0.03] px-2.5 py-1 text-[11px] text-slate-300 hover:border-blue-500/40 hover:bg-blue-600/10 hover:text-white transition-all cursor-pointer"
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
                  <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse-dot inline-block mr-2" />
                  Querying vector database and statutory provisions...
                </div>
              )}

              {!searching && hasSearched && searchResults.length === 0 && (
                <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-8 text-center">
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
                    className="rounded-2xl border border-white/[0.08] bg-gradient-to-b from-[#121520] to-[#0A0D14] p-5 shadow-lg space-y-2.5 transition-all hover:border-blue-500/30"
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

                    <p className="text-xs leading-relaxed text-slate-300 font-mono bg-black/30 p-3 rounded-xl border border-white/[0.04]">
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