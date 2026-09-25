'use client'
import React, { useState } from 'react'

interface Stage {
  number: number
  title: string
  shortLabel: string
  icon: string
  subtitle: string
  description: string
  inputExample: string
  transformation: string
  outputVerified: string
  badgeColor: string
}

const PIPELINE_STAGES: Stage[] = [
  {
    number: 1,
    title: 'Multi-Modal Ingestion & OCR',
    shortLabel: '1. Ingest & OCR',
    icon: '📥',
    subtitle: 'Extracts clean legal text from scanned court files, FIRs, and PDFs.',
    description: 'When you upload documents or ask a question, our high-speed ingestion pipeline parses text, runs Tesseract OCR for physical scanned papers, and structures sections into searchable embeddings.',
    inputExample: 'Scanned High Court Writ Petition.pdf (Image/Text)',
    transformation: 'Tesseract OCR + python-docx + Page-level segment chunking',
    outputVerified: 'Clean searchable document vectors with exact page coordinates.',
    badgeColor: 'border-blue-500/40 bg-blue-500/10 text-blue-300',
  },
  {
    number: 2,
    title: 'Dual-Stream Adaptive RAG (BNS & IPC)',
    shortLabel: '2. Dual-Stream RAG',
    icon: '⚡',
    subtitle: 'Correlates traditional IPC/CrPC with new BNS/BNSS 2023 statutes.',
    description: 'NyayaPramaan performs hybrid dense vector retrieval across official Indian statutes and landmark judgments. If local retrieval is sparse, Corrective RAG (CRAG) activates to fetch live verified gazette notifications.',
    inputExample: 'Query: "What is the penalty for cheating under BNS?"',
    transformation: 'Vector Search against 45,000+ chunks + Statute cross-mapper',
    outputVerified: 'Section 318 BNS retrieved with corresponding IPC 420 legacy context.',
    badgeColor: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
  },
  {
    number: 3,
    title: 'Atomic Claim Deconstruction',
    shortLabel: '3. Claim Extraction',
    icon: '🧠',
    subtitle: 'Splits AI drafts into standalone verifiable factual statements.',
    description: 'Generic LLMs generate paragraphs that mix fact with hallucination. NyayaPramaan isolates every legal proposition into an atomic claim before presenting it to the user.',
    inputExample: '"Under Section 438 CrPC, anticipatory bail is non-bailable..."',
    transformation: 'Claim Extractor isolates: [Claim 1: Sec 438 relates to pre-arrest bail], [Claim 2: High Court has jurisdiction]',
    outputVerified: '3 discrete atomic propositions ready for independent verification.',
    badgeColor: 'border-purple-500/40 bg-purple-500/10 text-purple-300',
  },
  {
    number: 4,
    title: 'TrustAgent™ Source Verification',
    shortLabel: '4. Trust Verification',
    icon: '🛡️',
    subtitle: 'Re-retrieves original sources and checks judicial hierarchy.',
    description: 'The TrustAgent independently checks whether the extracted legal claims are supported by the bare act text. It checks court hierarchy (Supreme Court binding vs High Court persuasive) and tags accuracy confidence.',
    inputExample: 'Claim: "Magistrate can grant pre-arrest bail under 438"',
    transformation: 'Hierarchy Cross-Check: Section 438 applies only to Sessions/High Court',
    outputVerified: 'Status: CONTRADICTED & AUTO-CORRECTED to Sessions Court.',
    badgeColor: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
  },
  {
    number: 5,
    title: 'SHA-256 Cryptographic Audit Ledger',
    shortLabel: '5. Hash-Chain Log',
    icon: '⛓️',
    subtitle: 'Immutable record of verification ensuring zero tampering.',
    description: 'Every verified query, model output, and precision score is cryptographically hashed with its preceding log entry (Blockchain-style SHA-256 chain). This provides evidentiary audit logs for advocates and judicial reviews.',
    inputExample: 'Event: { query_id: "q-9021", precision: 0.98, verified: true }',
    transformation: 'Compute: SHA256(PrevHash + Timestamp + VerificationPayload)',
    outputVerified: 'Block #8492: 8f4a7c...e01d (Verified Immutable)',
    badgeColor: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
  },
]

export function InteractivePipeline() {
  const [activeStage, setActiveStage] = useState<Stage>(PIPELINE_STAGES[0])

  return (
    <div className="space-y-8">
      {/* Interactive Step Navigator */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
        {PIPELINE_STAGES.map((s) => (
          <button
            key={s.number}
            onClick={() => setActiveStage(s)}
            className={`flex flex-col items-center p-3 rounded-2xl border text-center transition-all cursor-pointer ${
              activeStage.number === s.number
                ? 'border-amber-400 bg-amber-500/15 shadow-[0_0_25px_rgba(200,155,89,0.25)] scale-102'
                : 'border-white/10 bg-white/[0.02] text-slate-400 hover:border-white/20 hover:text-white hover:bg-white/[0.05]'
            }`}
          >
            <span className="text-2xl mb-1">{s.icon}</span>
            <span className="text-xs font-semibold text-white tracking-wide">{s.shortLabel}</span>
            <span className="text-[10px] text-slate-400 line-clamp-1 mt-0.5">{s.title}</span>
          </button>
        ))}
      </div>

      {/* Main Stage Detail Card */}
      <div className="gradient-border-card p-1 shadow-2xl">
        <div className="rounded-2xl bg-[#0C0F17] p-6 sm:p-8 space-y-6 border border-white/10 backdrop-blur-xl">
          {/* Stage Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-5">
            <div className="flex items-center gap-3">
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-500/20 text-2xl border border-amber-500/30">
                {activeStage.icon}
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-amber-400 uppercase tracking-widest">
                    Stage 0{activeStage.number} of 05
                  </span>
                  <span className={`rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase ${activeStage.badgeColor}`}>
                    Active Engine
                  </span>
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-white mt-1">
                  {activeStage.title}
                </h3>
              </div>
            </div>
          </div>

          {/* Description */}
          <p className="text-sm sm:text-base text-slate-300 leading-relaxed font-light">
            {activeStage.description}
          </p>

          {/* Live Data Flow Visualizer */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
            {/* Input */}
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 space-y-2">
              <div className="flex items-center gap-1.5 text-[11px] font-mono uppercase text-slate-400">
                <span>📥</span>
                <span>Stage Input:</span>
              </div>
              <p className="text-xs text-slate-200 font-mono bg-black/40 p-2.5 rounded-lg border border-white/5 leading-relaxed">
                {activeStage.inputExample}
              </p>
            </div>

            {/* Transformation */}
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 space-y-2">
              <div className="flex items-center gap-1.5 text-[11px] font-mono uppercase text-amber-300">
                <span>⚙️</span>
                <span>Engine Transformation:</span>
              </div>
              <p className="text-xs text-amber-100 font-mono bg-black/40 p-2.5 rounded-lg border border-amber-500/20 leading-relaxed">
                {activeStage.transformation}
              </p>
            </div>

            {/* Output */}
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4 space-y-2">
              <div className="flex items-center gap-1.5 text-[11px] font-mono uppercase text-emerald-400">
                <span>✓</span>
                <span>Verified Output:</span>
              </div>
              <p className="text-xs text-emerald-200 font-mono bg-black/40 p-2.5 rounded-lg border border-emerald-500/20 leading-relaxed">
                {activeStage.outputVerified}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
