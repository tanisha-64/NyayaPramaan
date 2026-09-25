'use client'
import React, { useState } from 'react'

interface CaseScenario {
  id: string
  title: string
  citation: string
  bench: string
  claims: { text: string; verdict: 'supported' | 'binding' | 'corrected'; source: string }[]
  overallPrecision: number
  sha256Hash: string
  prevHash: string
}

const CASE_SCENARIOS: CaseScenario[] = [
  {
    id: 'maneka',
    title: 'Maneka Gandhi vs Union of India (1978)',
    citation: '1978 AIR 597, 1978 SCR (2) 621',
    bench: '7-Judge Constitution Bench',
    claims: [
      {
        text: 'Article 21 procedure must not only be statutory, but also just, fair, and reasonable (Due Process principle).',
        verdict: 'binding',
        source: 'Supreme Court Judgment Para 54 & Article 21 Bare Act',
      },
      {
        text: 'Right to travel abroad is a fundamental freedom under Article 21.',
        verdict: 'supported',
        source: 'Passports Act 1967 & Satwant Singh Sawhney affirmation',
      },
      {
        text: 'Articles 14, 19, and 21 form an interconnected golden triangle of constitutional liberties.',
        verdict: 'binding',
        source: 'Golden Triangle Jurisprudence (Bhagwati J. majority ratio)',
      },
    ],
    overallPrecision: 99.2,
    sha256Hash: '9e3b7a82c4f1d09e5b881a742cd9320e8a7199cf431e2894b9e2890471b6ea12',
    prevHash: '7c82a19b02f8319e716e99ab12093847e129384a8b7c6d5e4f3a2b1c0d9e8f7a',
  },
  {
    id: 'kesavananda',
    title: 'Kesavananda Bharati vs State of Kerala (1973)',
    citation: '1973 4 SCC 225',
    bench: '13-Judge Constitution Bench (Largest in Indian History)',
    claims: [
      {
        text: 'Parliament has wide powers to amend the Constitution under Article 368 but cannot alter its Basic Structure.',
        verdict: 'binding',
        source: 'Constitution of India Art 368 & 7:6 Majority Ratio',
      },
      {
        text: 'Judicial review, democracy, secularism, and rule of law are unamendable core features.',
        verdict: 'supported',
        source: 'Supreme Court Doctrine of Basic Structure',
      },
      {
        text: '24th, 25th, and 29th Constitutional Amendments were examined and partially upheld.',
        verdict: 'supported',
        source: 'Constitutional Gazette Notification & Final Order',
      },
    ],
    overallPrecision: 98.7,
    sha256Hash: '4f1a9c8e2b7d3019e5a847b2c9301e8a918237cf412e3894a9e1890471b6ef90',
    prevHash: '9e3b7a82c4f1d09e5b881a742cd9320e8a7199cf431e2894b9e2890471b6ea12',
  },
  {
    id: 'gopalan',
    title: 'A.K. Gopalan vs State of Madras (1950)',
    citation: '1950 AIR 27, 1950 SCR 88',
    bench: '6-Judge Constitution Bench',
    claims: [
      {
        text: 'Article 21 "procedure established by law" was initially interpreted literally as state-made lex.',
        verdict: 'supported',
        source: 'Preventive Detention Act 1950 & Majority opinion of Kania CJ',
      },
      {
        text: 'Later overruled by Maneka Gandhi to establish substantive due process.',
        verdict: 'binding',
        source: 'Subsequent Overruling Judicial History Record',
      },
    ],
    overallPrecision: 97.5,
    sha256Hash: '1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b',
    prevHash: '4f1a9c8e2b7d3019e5a847b2c9301e8a918237cf412e3894a9e1890471b6ef90',
  },
]

export function LiveTrustAgentDemo() {
  const [activeCase, setActiveCase] = useState<CaseScenario>(CASE_SCENARIOS[0])
  const [isVerifying, setIsVerifying] = useState(false)

  function handleSwitchCase(c: CaseScenario) {
    setIsVerifying(true)
    setActiveCase(c)
    setTimeout(() => setIsVerifying(false), 250)
  }

  return (
    <div className="space-y-6">
      {/* Case Selector Tabs */}
      <div className="flex flex-wrap gap-2">
        {CASE_SCENARIOS.map((c) => (
          <button
            key={c.id}
            onClick={() => handleSwitchCase(c)}
            className={`rounded-xl px-4 py-2.5 text-xs font-semibold transition-all cursor-pointer ${
              activeCase.id === c.id
                ? 'border border-amber-400 bg-amber-500/20 text-amber-200 shadow-[0_0_20px_rgba(200,155,89,0.25)]'
                : 'border border-white/10 bg-white/[0.03] text-slate-300 hover:border-white/20 hover:text-white'
            }`}
          >
            {c.title}
          </button>
        ))}
      </div>

      {/* Main Verification Card */}
      <div className="gradient-border-card p-1 shadow-2xl">
        <div className={`rounded-2xl bg-[#0B0E16] p-6 sm:p-8 space-y-6 border border-white/10 backdrop-blur-2xl transition-opacity duration-200 ${
          isVerifying ? 'opacity-40' : 'opacity-100'
        }`}>
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-5">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-amber-400 uppercase tracking-wider">
                  Landmark Constitutional Precedent
                </span>
                <span className="rounded-md border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-300">
                  {activeCase.bench}
                </span>
              </div>
              <h3 className="text-xl sm:text-2xl font-bold text-white mt-1">
                {activeCase.title}
              </h3>
              <p className="text-xs font-mono text-slate-400 mt-0.5">
                Official Citation: {activeCase.citation}
              </p>
            </div>

            <div className="flex items-center gap-3 self-start sm:self-auto">
              <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-center">
                <div className="text-lg font-black text-emerald-300 tabular-nums">{activeCase.overallPrecision}%</div>
                <div className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">Verification Score</div>
              </div>
            </div>
          </div>

          {/* Section: Atomic Claims Breakdown */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <span>🔬</span>
              <span>Atomic Claims & Source Grounding Breakdown</span>
            </h4>

            <div className="space-y-2.5">
              {activeCase.claims.map((claim, idx) => (
                <div
                  key={idx}
                  className="rounded-xl border border-white/10 bg-white/[0.03] p-4 space-y-2 hover:border-white/20 transition-colors"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2.5 min-w-0 flex-1">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold border border-emerald-500/40 mt-0.5">
                        ✓
                      </span>
                      <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-normal">
                        {claim.text}
                      </p>
                    </div>

                    <span className="shrink-0 rounded-full border border-emerald-500/40 bg-emerald-500/15 px-2.5 py-0.5 text-[10px] font-bold text-emerald-300 uppercase">
                      {claim.verdict === 'binding' ? '🏛️ Binding Ratio' : '📜 Supported'}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 text-[11px] text-slate-400 pl-7 font-mono">
                    <span className="text-amber-400">Source:</span>
                    <span className="text-slate-300">{claim.source}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Section: Cryptographic SHA-256 Ledger Block */}
          <div className="rounded-xl border border-amber-500/30 bg-[#07090E] p-4 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-semibold text-amber-300 flex items-center gap-1.5">
                <span>⛓️</span>
                <span>Cryptographic SHA-256 Audit Log</span>
              </span>
              <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-mono text-emerald-300">
                Tamper-Proof Block
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[11px] font-mono">
              <div className="bg-black/40 p-2.5 rounded-lg border border-white/5 space-y-1">
                <span className="text-slate-500 block text-[10px]">PREVIOUS BLOCK HASH:</span>
                <span className="text-slate-400 truncate block" title={activeCase.prevHash}>
                  {activeCase.prevHash}
                </span>
              </div>
              <div className="bg-amber-500/10 p-2.5 rounded-lg border border-amber-500/20 space-y-1">
                <span className="text-amber-400 block text-[10px]">CURRENT BLOCK SIGNATURE:</span>
                <span className="text-amber-200 truncate block font-bold" title={activeCase.sha256Hash}>
                  {activeCase.sha256Hash}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
