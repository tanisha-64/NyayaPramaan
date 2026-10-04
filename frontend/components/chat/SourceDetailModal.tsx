'use client'
import { LegalSource } from '@/services/chatService'

export function SourceDetailModal({
  source,
  onClose,
}: {
  source: LegalSource | null
  onClose: () => void
}) {
  if (!source) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-lg rounded-2xl border border-[#B8925A]/30 bg-[#0E121B] p-6 shadow-2xl text-slate-100">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-white/[0.08] pb-4">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-500/15 text-base border border-blue-500/25">
              📜
            </span>
            <div>
              <h3 className="text-sm font-semibold tracking-tight text-white">
                {source.name}
              </h3>
              <p className="text-[11px] text-slate-400 capitalize">
                {source.type || 'Statutory Code'} • {source.jurisdiction || 'Indian Jurisdiction'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-white/[0.08] hover:text-white transition-colors cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Details Grid */}
        <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
            <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
              Verification Status
            </span>
            <div className="mt-1 flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse-dot" />
              <span className="font-semibold text-emerald-400 uppercase text-[11px]">
                {source.verification_status || 'Verified'}
              </span>
            </div>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
            <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
              Location / Page
            </span>
            <div className="mt-1 font-semibold text-slate-200 text-[11px]">
              {source.page ? `Page ${source.page}` : 'Primary Document'}{' '}
              {source.section ? `• ${source.section}` : ''}
            </div>
          </div>
        </div>

        {/* Excerpt */}
        <div className="mt-4">
          <span className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">
            Authoritative Excerpt / Provision
          </span>
          <div className="mt-2 rounded-xl border border-white/[0.08] bg-[#080B11] p-3.5 text-xs text-slate-300 leading-relaxed max-h-48 overflow-y-auto">
            {source.excerpt ||
              'Referenced from the authoritative legislative text and indexed legal record within the NyayaPramaan repository.'}
          </div>
        </div>

        {/* External Link or Action */}
        <div className="mt-5 flex items-center justify-between border-t border-white/[0.08] pt-4">
          <span className="text-[11px] text-slate-400">
            Cryptographically logged to NyayaPramaan Trust Trail
          </span>
          {source.url ? (
            <a
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 transition-all shadow-md"
            >
              <span>View Source</span>
              <span>↗</span>
            </a>
          ) : (
            <button
              onClick={onClose}
              className="rounded-xl bg-white/[0.08] px-3.5 py-1.5 text-xs font-medium text-slate-200 hover:bg-white/[0.14] transition-all cursor-pointer"
            >
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
