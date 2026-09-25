'use client'
import React, { useState } from 'react'

interface FeatureRow {
  title: string
  description: string
  nyaya: { status: boolean; detail: string }
  genericAI: { status: boolean; detail: string }
  traditionalSearch: { status: boolean; detail: string }
}

const COMPARISON_DATA: FeatureRow[] = [
  {
    title: 'Statutory Grounding (BNS & IPC Dual-Mapping)',
    description: 'Accurately correlates new Bharatiya Nyaya Sanhita (BNS 2023) with legacy IPC/CrPC sections.',
    nyaya: { status: true, detail: 'Automated dual-statute cross-indexing with gazette verification' },
    genericAI: { status: false, detail: 'Frequently invents obsolete or non-existent section numbers' },
    traditionalSearch: { status: true, detail: 'Raw keyword search only; cannot correlate sections dynamically' },
  },
  {
    title: 'Post-Generation Citation Re-Verification',
    description: 'Every statement is broken into atomic claims and re-verified against the original Bare Act text.',
    nyaya: { status: true, detail: 'TrustAgent™ dual-pass verification with confidence score' },
    genericAI: { status: false, detail: 'Zero verification; outputs ungrounded probabilistic text' },
    traditionalSearch: { status: false, detail: 'Does not generate synthesized answers or check legal claims' },
  },
  {
    title: 'Court Hierarchy & Precedent Strength',
    description: 'Identifies whether a judgment is Constitution Bench (Binding) or High Court (Persuasive).',
    nyaya: { status: true, detail: 'Tags binding ratio decidendi vs obiter dicta automatically' },
    genericAI: { status: false, detail: 'No understanding of Indian judicial hierarchy' },
    traditionalSearch: { status: false, detail: 'Requires manual advocate reading and filtering' },
  },
  {
    title: 'Multi-Page Case Document OCR & Cross-Examination',
    description: 'Upload scanned High Court petitions, FIRs, and contracts to ask specific evidentiary questions.',
    nyaya: { status: true, detail: 'Page-level citation grounding with Tesseract OCR fallback' },
    genericAI: { status: false, detail: 'Loses page precision and often hallucinates missing facts' },
    traditionalSearch: { status: false, detail: 'Cannot upload and query your private court case files' },
  },
  {
    title: 'Cryptographic SHA-256 Audit Trail',
    description: 'Immutable ledger of every query, answer, and verification event for judicial compliance.',
    nyaya: { status: true, detail: 'Blockchain-style cryptographic hash chain for evidence logs' },
    genericAI: { status: false, detail: 'Ephemeral chat logs with zero tamper-evidence' },
    traditionalSearch: { status: false, detail: 'No verifiable audit logs' },
  },
  {
    title: 'Automatic PII Redaction (Aadhaar, PAN, Phone)',
    description: 'Protects client privacy by sanitizing sensitive personally identifiable information.',
    nyaya: { status: true, detail: 'Output guardrails redact Aadhaar, PAN, emails, and phone numbers' },
    genericAI: { status: false, detail: 'Stores and retains user data in training loops' },
    traditionalSearch: { status: false, detail: 'Displays unredacted court records' },
  },
]

export function RealWorldComparison() {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  return (
    <div className="space-y-6">
      {/* Comparison Container */}
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-[#0C0F17] shadow-2xl backdrop-blur-2xl">
        {/* Table Header */}
        <div className="grid grid-cols-12 gap-4 border-b border-white/10 bg-white/[0.03] p-4 sm:p-5 text-xs font-semibold uppercase tracking-wider text-slate-400">
          <div className="col-span-6 sm:col-span-5 text-white">Platform Capability</div>
          <div className="col-span-6 sm:col-span-3 text-center text-amber-300 font-bold flex items-center justify-center gap-1.5">
            <span>⚖️ NyayaPramaan</span>
            <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[9px] text-amber-300">Verified</span>
          </div>
          <div className="hidden sm:block sm:col-span-2 text-center text-slate-400">Generic LLMs (ChatGPT/Claude)</div>
          <div className="hidden sm:block sm:col-span-2 text-center text-slate-400">Traditional Law Search</div>
        </div>

        {/* Rows */}
        <div className="divide-y divide-white/5">
          {COMPARISON_DATA.map((row, idx) => (
            <div
              key={row.title}
              onMouseEnter={() => setHoveredIndex(idx)}
              onMouseLeave={() => setHoveredIndex(null)}
              className={`grid grid-cols-12 gap-4 p-4 sm:p-5 items-center transition-all ${
                hoveredIndex === idx ? 'bg-white/[0.04]' : 'bg-transparent'
              }`}
            >
              {/* Feature Title & Description */}
              <div className="col-span-6 sm:col-span-5 space-y-1">
                <h4 className="text-xs sm:text-sm font-semibold text-white tracking-wide">
                  {row.title}
                </h4>
                <p className="text-[11px] text-slate-400 leading-relaxed font-light">
                  {row.description}
                </p>
              </div>

              {/* NyayaPramaan Column */}
              <div className="col-span-6 sm:col-span-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-center space-y-1">
                <div className="flex items-center justify-center gap-1.5 text-xs font-bold text-amber-300">
                  <span className="text-emerald-400 font-black">✓</span>
                  <span>Supported</span>
                </div>
                <p className="text-[10px] text-amber-200/90 leading-tight">
                  {row.nyaya.detail}
                </p>
              </div>

              {/* Generic LLMs Column */}
              <div className="hidden sm:block sm:col-span-2 text-center space-y-1 p-2">
                <div className="flex items-center justify-center gap-1 text-xs font-semibold text-red-400">
                  <span>✗</span>
                  <span>Flawed</span>
                </div>
                <p className="text-[10px] text-slate-400 leading-tight">
                  {row.genericAI.detail}
                </p>
              </div>

              {/* Traditional Search Column */}
              <div className="hidden sm:block sm:col-span-2 text-center space-y-1 p-2">
                <div className="flex items-center justify-center gap-1 text-xs font-semibold text-slate-400">
                  <span>—</span>
                  <span>Limited</span>
                </div>
                <p className="text-[10px] text-slate-400 leading-tight">
                  {row.traditionalSearch.detail}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
