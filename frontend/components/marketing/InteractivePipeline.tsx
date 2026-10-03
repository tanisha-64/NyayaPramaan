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
    title: 'Document & Query Ingestion',
    shortLabel: '1. Ingestion',
    icon: '📥',
    subtitle: 'Extracts and parses legal text from user prompts, court files, or petitions.',
    description: 'When a citizen or lawyer submits a legal question or uploads a case document (PDF/DOCX), our pipeline extracts clean structured text, splits it into semantic chunks, and creates vector embeddings.',
    inputExample: 'Legal Prompt or Case Document (PDF/DOCX/Text)',
    transformation: 'Text Extraction + Semantic Chunking + Vector Embeddings',
    outputVerified: 'Clean indexed document chunks ready for statutory search.',
    badgeColor: 'border-blue-500/40 bg-blue-500/10 text-blue-300',
  },
  {
    number: 2,
    title: 'Dual-Stream Statutory RAG (BNS & IPC)',
    shortLabel: '2. Statute Search',
    icon: '⚡',
    subtitle: 'Retrieves relevant sections from official Bare Acts and Central Acts.',
    description: 'NyayaPramaan simultaneously queries both legacy laws (IPC, CrPC, IEA) and new criminal codes (BNS, BNSS, BSA 2023) to fetch the exact statutory provisions applicable to the scenario.',
    inputExample: 'Query semantic vector matching legal database',
    transformation: 'Hybrid Dense Retrieval + BNS/IPC Cross-Reference Index',
    outputVerified: 'Exact Bare Act statutory sections & official text extracted.',
    badgeColor: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
  },
  {
    number: 3,
    title: 'Atomic Claim Deconstruction',
    shortLabel: '3. Claim Isolation',
    icon: '🔬',
    subtitle: 'Splits AI responses into individual verifiable legal propositions.',
    description: 'Rather than outputting unchecked text, the engine deconstructs the draft into distinct atomic legal claims (e.g. bail eligibility, jurisdiction, limitation period) for granular verification.',
    inputExample: 'Draft legal response with multiple statutory assertions',
    transformation: 'Syntactic parsing into independent atomic propositions',
    outputVerified: 'Isolated claim units tagged for direct citation verification.',
    badgeColor: 'border-purple-500/40 bg-purple-500/10 text-purple-300',
  },
  {
    number: 4,
    title: 'TrustAgent™ Evidence Verification',
    shortLabel: '4. Evidence Check',
    icon: '🛡️',
    subtitle: 'Verifies claims against official source texts and court hierarchy.',
    description: 'The TrustAgent independently checks whether each atomic claim is supported by the bare act text or authoritative judicial authority. Any hallucination or misquote is flagged or corrected in real-time.',
    inputExample: 'Claim propositions matched against retrieved Bare Act text',
    transformation: 'NLI Entailment + Judicial Hierarchy Validation (Binding vs Persuasive)',
    outputVerified: 'Status: 100% Grounded & Citation Verified.',
    badgeColor: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
  },
  {
    number: 5,
    title: 'Cryptographic SHA-256 Audit Trail',
    shortLabel: '5. Audit Ledger',
    icon: '⛓️',
    subtitle: 'Generates tamper-proof cryptographic proof of verification.',
    description: 'Every completed query, verified citation, and trust score is hashed into an immutable chronological audit trail, ensuring complete transparency and proof against hallucinations.',
    inputExample: 'Verification metadata + timestamp + source citations',
    transformation: 'SHA-256 Block Signature: SHA256(PrevHash + ClaimPayload)',
    outputVerified: 'Tamper-evident verification receipt generated for the user.',
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
