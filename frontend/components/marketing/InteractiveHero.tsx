'use client'
import React, { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/Button'

interface DemoScenario {
  id: string
  label: string
  query: string
  act: string
  section: string
  verdict: 'binding' | 'supported' | 'statute'
  confidence: number
  summary: string
  bindingCitation: string
}

const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: 'bail',
    label: '⚖️ Anticipatory Bail (BNS)',
    query: 'Can anticipatory bail be granted for non-bailable offences under new criminal laws?',
    act: 'Bharatiya Nagarik Suraksha Sanhita (BNSS)',
    section: 'Section 482 (corresponding to Sec 438 CrPC)',
    verdict: 'binding',
    confidence: 98,
    summary: 'High Court and Sessions Court possess concurrent jurisdiction to grant pre-arrest bail based on judicial discretion and material facts.',
    bindingCitation: 'Gurbaksh Singh Sibbia vs State of Punjab (5-Judge Constitution Bench)',
  },
  {
    id: 'quash',
    label: '🏛️ FIR Quashing (482)',
    query: 'What are the guidelines for quashing an FIR in matrimonial disputes?',
    act: 'BNSS 2023 / CrPC 1973',
    section: 'Section 528 BNSS / Section 482 CrPC',
    verdict: 'supported',
    confidence: 96,
    summary: 'Inherent powers under Section 482 can be invoked to prevent abuse of court process where civil disputes or genuine settlements exist.',
    bindingCitation: 'State of Haryana vs Bhajan Lal & B.S. Joshi vs State of Haryana',
  },
  {
    id: 'cyber',
    label: '🛡️ Cyber Fraud & Relief',
    query: 'What immediate legal remedies exist for unauthorized UPI banking transactions?',
    act: 'IT Act 2000 & RBI Master Circular',
    section: 'Section 43A, 66D IT Act & RBI Circular DBR.No.Leg.BC.78',
    verdict: 'statute',
    confidence: 94,
    summary: 'Zero liability for customers if unauthorized fraud is reported within 3 working days via national helpline 1930 / cybercrime portal.',
    bindingCitation: 'RBI Mandate 2017 & Section 43A Information Technology Act',
  },
]

export function InteractiveHero() {
  const [selectedScenario, setSelectedScenario] = useState<DemoScenario>(DEMO_SCENARIOS[0])
  const [isVerifying, setIsVerifying] = useState(false)

  function handleSelectScenario(s: DemoScenario) {
    setIsVerifying(true)
    setSelectedScenario(s)
    setTimeout(() => setIsVerifying(false), 300)
  }

  return (
    <section className="relative overflow-hidden pt-12 pb-20 md:pt-20 md:pb-32 bg-grid-pattern">
      {/* Radiant Background Bloom Orbs */}
      <div className="bloom-orb-amber -top-20 -left-20" />
      <div className="bloom-orb-indigo top-1/3 -right-20" />
      <div className="bloom-orb-cyan -bottom-20 left-1/3" />

      <div className="relative z-10 mx-auto max-w-[1440px] px-6">
        {/* Top Tag */}
        <div className="flex justify-center md:justify-start mb-6">
          <div className="inline-flex items-center gap-2.5 rounded-full border border-amber-500/40 bg-amber-500/10 px-4 py-1.5 text-xs font-semibold text-amber-300 shadow-[0_0_20px_rgba(200,155,89,0.2)] backdrop-blur-xl">
            <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="tracking-wider uppercase text-[11px]">India's 1st Evidence-Grounded Legal Intelligence</span>
            <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[9px] text-amber-200">BNS & IPC Ready</span>
          </div>
        </div>

        {/* Main 2-Column Hero Grid */}
        <div className="grid gap-12 lg:grid-cols-12 lg:items-center">
          {/* Left Column: Vision & Dynamic Copy */}
          <div className="lg:col-span-7 space-y-6 text-center md:text-left">
            <h1 className="font-[var(--font-serif)] text-4xl sm:text-5xl lg:text-6xl font-bold leading-[1.12] tracking-tight text-white">
              Legal AI Grounded in{' '}
              <span className="gradient-text-gold">Pinpoint Evidence</span>,{' '}
              <br className="hidden sm:inline" />
              Not Hallucinations.
            </h1>

            <p className="max-w-2xl text-base sm:text-lg text-slate-300 leading-relaxed font-light">
              Generic LLMs invent fictional citations. NyayaPramaan verifies every atomic legal claim against Indian Statutes (BNS, BNSS, IPC, CrPC) and Supreme Court precedents with a <strong className="text-white font-medium">tamper-proof cryptographic audit trail</strong>.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-wrap items-center justify-center md:justify-start gap-4 pt-2">
              <Button
                href="/public/chat"
                variant="primary"
                className="px-6 py-3.5 text-sm font-semibold shadow-[0_0_30px_rgba(200,155,89,0.3)] hover:scale-105 transition-transform"
              >
                Launch Legal AI Research →
              </Button>
              <Button
                href="/how-it-works"
                variant="secondary"
                className="px-6 py-3.5 text-sm font-semibold border-white/20 hover:border-white/40"
              >
                Explore 5-Stage Engine ⚡
              </Button>
            </div>

            {/* Live Trust Badges */}
            <div className="grid grid-cols-3 gap-3 pt-6 border-t border-white/10 max-w-lg mx-auto md:mx-0">
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 backdrop-blur-md">
                <div className="text-xl sm:text-2xl font-black text-amber-300 tabular-nums">95.8%</div>
                <div className="text-[11px] text-slate-400 font-medium">Citation Accuracy</div>
              </div>
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 backdrop-blur-md">
                <div className="text-xl sm:text-2xl font-black text-blue-300 tabular-nums">45K+</div>
                <div className="text-[11px] text-slate-400 font-medium">Verified Precedents</div>
              </div>
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 backdrop-blur-md">
                <div className="text-xl sm:text-2xl font-black text-emerald-300 tabular-nums">SHA-256</div>
                <div className="text-[11px] text-slate-400 font-medium">Tamper-Proof Audit</div>
              </div>
            </div>
          </div>

          {/* Right Column: Live Interactive Legal AI Terminal */}
          <div className="lg:col-span-5">
            <div className="gradient-border-card p-1 shadow-2xl transition-all duration-300 hover:shadow-[0_0_50px_rgba(200,155,89,0.2)]">
              <div className="rounded-2xl bg-[#0C0E15] p-5 space-y-4 border border-white/10 backdrop-blur-2xl">
                {/* Terminal Header */}
                <div className="flex items-center justify-between border-b border-white/10 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="flex h-3 w-3 rounded-full bg-red-500/80" />
                    <span className="flex h-3 w-3 rounded-full bg-amber-500/80" />
                    <span className="flex h-3 w-3 rounded-full bg-emerald-500/80" />
                    <span className="ml-2 text-xs font-mono text-slate-400">TrustAgent™ Verification Terminal</span>
                  </div>
                  <span className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-300 uppercase tracking-wider">
                    ● Active Live
                  </span>
                </div>

                {/* Scenario Selector Pills */}
                <div>
                  <div className="text-[11px] text-slate-400 mb-2 font-medium">Try Live Legal Query Demo:</div>
                  <div className="flex flex-wrap gap-1.5">
                    {DEMO_SCENARIOS.map((s) => (
                      <button
                        key={s.id}
                        onClick={() => handleSelectScenario(s)}
                        className={`rounded-xl px-2.5 py-1.5 text-[11px] font-medium transition-all cursor-pointer ${
                          selectedScenario.id === s.id
                            ? 'border border-amber-400 bg-amber-500/20 text-amber-200 shadow-[0_0_15px_rgba(200,155,89,0.25)]'
                            : 'border border-white/10 bg-white/[0.03] text-slate-400 hover:border-white/20 hover:text-white'
                        }`}
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Query Bubble */}
                <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3 text-xs text-white">
                  <span className="font-semibold text-amber-300 mr-1.5">User Query:</span>
                  <span className="text-slate-200 leading-relaxed">"{selectedScenario.query}"</span>
                </div>

                {/* Verified Output Card */}
                <div className={`rounded-xl border border-amber-500/30 bg-[#12151F] p-4 text-xs space-y-3 transition-opacity duration-200 ${
                  isVerifying ? 'opacity-40 animate-pulse' : 'opacity-100'
                }`}>
                  {/* Verified Header & Score */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 text-xs border border-emerald-500/40">
                        ✓
                      </span>
                      <span className="font-semibold text-emerald-300 text-xs">
                        Verified Legal Ratio
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-bold text-emerald-300">
                      <span>Precision:</span>
                      <span>{selectedScenario.confidence}%</span>
                    </div>
                  </div>

                  {/* Summary Text */}
                  <p className="text-slate-200 leading-relaxed text-[11.5px]">
                    {selectedScenario.summary}
                  </p>

                  {/* Pinpoint Grounded Citations */}
                  <div className="rounded-lg border border-white/10 bg-black/40 p-2.5 space-y-1.5">
                    <div className="flex items-center justify-between text-[10px] text-slate-400">
                      <span className="font-mono text-amber-300 uppercase">Statutory Grounding:</span>
                      <span className="text-emerald-300">Supreme Court Precedent</span>
                    </div>
                    <div className="text-[11px] font-medium text-white flex items-center gap-1.5">
                      <span>🏛️</span>
                      <span className="truncate">{selectedScenario.section}</span>
                    </div>
                    <div className="text-[10px] text-slate-400 flex items-center gap-1.5">
                      <span>📜</span>
                      <span className="truncate text-slate-300">{selectedScenario.bindingCitation}</span>
                    </div>
                  </div>
                </div>

                {/* Interactive Action Link */}
                <div className="text-center pt-1">
                  <Link
                    href="/public/chat"
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-300 hover:text-amber-200 transition-colors no-underline"
                  >
                    <span>Ask Your Own Legal Question in Chat</span>
                    <span>→</span>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
