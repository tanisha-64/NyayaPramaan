'use client'
import React, { useState } from "react";
import Link from "next/link";
import { TopNav } from "@/components/layout/TopNav";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/Button";

const FLOW_STEPS = [
  {
    step: "01",
    title: "Ask in Everyday Language or Voice",
    tagline: "No complicated legal jargon required",
    description:
      "Simply describe your situation in plain everyday words, or speak directly into your microphone. You can also upload any legal document, FIR, agreement, or formal notice.",
    icon: "💬",
    accent: "blue",
    badge: "border-blue-500/30 text-blue-300 bg-blue-500/10",
    glow: "hover:border-blue-500/40 hover:shadow-[0_0_30px_rgba(59,130,246,0.15)]",
    activeBorder: "border-blue-400 ring-2 ring-blue-500/30 shadow-[0_0_35px_rgba(59,130,246,0.25)]",
    exampleIcon: "🗣️",
    exampleLabel: "User Question",
    exampleText: '"My landlord is refusing to refund my security deposit after moving out. What are my rights?"',
  },
  {
    step: "02",
    title: "Official Government Law Matching",
    tagline: "Instant lookup across central statutes and acts",
    description:
      "The system immediately scans official Indian Central Bare Acts (such as BNS, IPC, Consumer Protection Act, and State Rent Control Acts) to identify the exact provisions relevant to your situation.",
    icon: "🔍",
    accent: "amber",
    badge: "border-amber-500/30 text-amber-300 bg-amber-500/10",
    glow: "hover:border-amber-500/40 hover:shadow-[0_0_30px_rgba(245,158,11,0.15)]",
    activeBorder: "border-amber-400 ring-2 ring-amber-500/30 shadow-[0_0_35px_rgba(245,158,11,0.25)]",
    exampleIcon: "📚",
    exampleLabel: "Statutes Identified",
    exampleText: "Matched: State Tenancy Act Section 14 + Consumer Protection Rights & Civil Remedies",
  },
  {
    step: "03",
    title: "Truth & Accuracy Double-Check",
    tagline: "Zero hallucinations, zero fake section numbers",
    description:
      "Unlike ordinary AI chatbots that frequently fabricate non-existent laws, NyayaPramaan cross-checks every single statement directly against official published government gazettes.",
    icon: "🛡️",
    accent: "emerald",
    badge: "border-emerald-500/30 text-emerald-300 bg-emerald-500/10",
    glow: "hover:border-emerald-500/40 hover:shadow-[0_0_30px_rgba(168,85,247,0.15)]",
    activeBorder: "border-emerald-400 ring-2 ring-emerald-500/30 shadow-[0_0_35px_rgba(16,185,129,0.25)]",
    exampleIcon: "✅",
    exampleLabel: "Source Grounding",
    exampleText: "100% verified against original statutory text & binding judicial authority",
  },
  {
    step: "04",
    title: "Clear Step-by-Step Action Plan",
    tagline: "Actionable answers backed by official legal proof",
    description:
      "You receive a simple, structured summary of your legal rights, recommended next steps, and exact section citations for complete peace of mind.",
    icon: "📋",
    accent: "purple",
    badge: "border-purple-500/30 text-purple-300 bg-purple-500/10",
    glow: "hover:border-purple-500/40 hover:shadow-[0_0_30px_rgba(168,85,247,0.15)]",
    activeBorder: "border-purple-400 ring-2 ring-purple-500/30 shadow-[0_0_35px_rgba(168,85,247,0.25)]",
    exampleIcon: "⚖️",
    exampleLabel: "Final Output",
    exampleText: "Actionable 3-step remedy plan + ready-to-use draft notice template",
  },
];

const FAQS = [
  {
    q: "Do I need any legal knowledge to use NyayaPramaan?",
    a: "Not at all! You can describe your situation in simple, everyday words. Our AI automatically maps your situation to the appropriate official laws.",
  },
  {
    q: "Can I upload files like contracts, police complaints, or notices?",
    a: "Yes. You can upload PDF files, Word documents, or text notes. The AI will extract the key clauses, explain what they mean, and suggest next steps.",
  },
  {
    q: "How does this differ from regular generic AI chatbots?",
    a: "Generic AI tools often hallucinate or invent fake legal sections. NyayaPramaan strictly verifies every statement against real official Bare Acts before giving an answer.",
  },
  {
    q: "Can lawyers and law students use this as well?",
    a: "Yes! Students can use it to research Indian laws, while practicing advocates can use the Professional Workspace for case preparation, drafting, and cross-referencing old IPC to new BNS codes.",
  },
];

export default function HowItWorksPage() {
  const [selectedStep, setSelectedStep] = useState<string>("01");

  const scrollToStep = (stepId: string) => {
    setSelectedStep(stepId);
    const element = document.getElementById(`step-card-${stepId}`);
    if (element) {
      const yOffset = -100;
      const y = element.getBoundingClientRect().top + window.pageYOffset + yOffset;
      window.scrollTo({ top: y, behavior: "smooth" });
    }
  };

  return (
    <>
      <TopNav />
      <main className="mx-auto max-w-[1440px] px-6 py-12 md:py-20 space-y-24">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-3.5 py-1 text-xs font-semibold uppercase tracking-[0.15em] text-blue-300">
            <span>⚡</span>
            <span>Simple & Transparent Workflow</span>
          </div>
          <h1 className="font-[var(--font-serif)] text-4xl sm:text-5xl lg:text-6xl font-bold text-white tracking-tight">
            How NyayaPramaan <span className="gradient-text-gold">Works</span>
          </h1>
          <p className="text-slate-300 text-base sm:text-lg leading-relaxed font-light">
            Clear, reliable legal understanding made effortless. Here is the complete journey from your question to a verified answer.
          </p>
        </div>

        {/* Visual Flowchart Diagram Bar */}
        <div className="rounded-3xl border border-white/10 bg-[#0C0F17]/90 p-6 sm:p-10 backdrop-blur-2xl shadow-2xl space-y-8">
          <div className="text-center">
            <h2 className="text-xl sm:text-2xl font-bold text-white">
              The 4-Step Legal Journey
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Click any step below to explore its detailed working and example
            </p>
          </div>

          {/* Desktop Flowchart Connected Chain */}
          <div className="hidden lg:grid grid-cols-4 gap-4 relative">
            {FLOW_STEPS.map((s, idx) => {
              const isSelected = selectedStep === s.step;
              return (
                <button
                  key={s.step}
                  type="button"
                  onClick={() => scrollToStep(s.step)}
                  className={`relative flex flex-col items-center text-center p-4 rounded-2xl transition-all cursor-pointer ${
                    isSelected
                      ? "bg-white/[0.08] scale-105"
                      : "hover:bg-white/[0.04] opacity-85 hover:opacity-100"
                  }`}
                >
                  {/* Step Connector Line */}
                  {idx < FLOW_STEPS.length - 1 && (
                    <div className="absolute top-10 left-[60%] w-[80%] h-0.5 bg-gradient-to-r from-amber-500/50 via-blue-500/50 to-emerald-500/50 -z-0 pointer-events-none">
                      <span className="absolute -top-1.5 right-0 text-[10px] text-amber-300">➔</span>
                    </div>
                  )}
                  <div
                    className={`relative z-10 flex h-16 w-16 items-center justify-center rounded-2xl border text-3xl shadow-xl mb-4 transition-all duration-300 ${
                      isSelected
                        ? "border-amber-400 bg-amber-500/20 shadow-[0_0_25px_rgba(245,158,11,0.3)] scale-110"
                        : "border-white/15 bg-[#121622] hover:scale-105"
                    }`}
                  >
                    {s.icon}
                  </div>
                  <span
                    className={`rounded-full border px-2.5 py-0.5 text-[11px] font-mono font-bold mb-2 transition-all ${
                      isSelected
                        ? "border-amber-400 bg-amber-400/20 text-amber-300"
                        : s.badge
                    }`}
                  >
                    STEP {s.step}
                  </span>
                  <h3 className="text-sm font-bold text-white tracking-wide">{s.title}</h3>
                  <p className="text-xs text-slate-400 mt-1 font-light">{s.tagline}</p>
                </button>
              );
            })}
          </div>

          {/* Mobile Flowchart Stack */}
          <div className="lg:hidden flex flex-col gap-3">
            {FLOW_STEPS.map((s, idx) => {
              const isSelected = selectedStep === s.step;
              return (
                <button
                  key={s.step}
                  type="button"
                  onClick={() => scrollToStep(s.step)}
                  className={`flex items-center gap-3 p-3.5 rounded-2xl border text-left transition-all cursor-pointer ${
                    isSelected
                      ? "border-amber-400/60 bg-amber-500/10 shadow-lg"
                      : "border-white/5 bg-white/[0.03] hover:border-white/15"
                  }`}
                >
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/10 text-2xl">
                    {s.icon}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`rounded px-1.5 py-0.2 text-[10px] font-mono font-bold ${s.badge}`}>
                        0{idx + 1}
                      </span>
                      <h3 className="text-xs font-bold text-white truncate">{s.title}</h3>
                    </div>
                    <p className="text-[11px] text-slate-400 truncate">{s.tagline}</p>
                  </div>
                  <span className="text-amber-400 text-xs shrink-0 font-semibold">
                    View ➔
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Detailed Flow Step Cards with Real-World Examples */}
        <div className="grid gap-6 md:grid-cols-2">
          {FLOW_STEPS.map((s) => {
            const isSelected = selectedStep === s.step;
            return (
              <div
                key={s.step}
                id={`step-card-${s.step}`}
                className={`relative flex flex-col justify-between overflow-hidden rounded-3xl border bg-[#0C0F17]/80 p-8 backdrop-blur-xl shadow-xl transition-all duration-300 group ${
                  isSelected
                    ? s.activeBorder
                    : `border-white/10 ${s.glow}`
                }`}
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/[0.05] text-2xl border border-white/10 group-hover:scale-105 transition-transform">
                        {s.icon}
                      </span>
                      <div>
                        <span className={`rounded-full border px-2.5 py-0.5 text-xs font-mono font-bold ${s.badge}`}>
                          Step {s.step}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <h3 className="text-xl sm:text-2xl font-bold text-white group-hover:text-amber-300 transition-colors">
                      {s.title}
                    </h3>
                    <p className="text-xs font-medium text-amber-400/90 italic">
                      {s.tagline}
                    </p>
                    <p className="text-sm text-slate-300 leading-relaxed font-light pt-2">
                      {s.description}
                    </p>
                  </div>
                </div>

                {/* Example box at bottom */}
                <div className="mt-6 rounded-2xl border border-white/10 bg-black/50 p-4 space-y-1.5">
                  <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-slate-400">
                    <span>{s.exampleIcon}</span>
                    <span>{s.exampleLabel}:</span>
                  </div>
                  <p className="text-xs text-slate-200 font-sans leading-relaxed">
                    {s.exampleText}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Who Is This For Section */}
        <div className="rounded-3xl border border-amber-500/20 bg-gradient-to-b from-amber-500/[0.06] to-transparent p-8 sm:p-12 space-y-8">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <span className="text-xs font-mono font-bold uppercase tracking-widest text-amber-400">
              User Personas
            </span>
            <h2 className="font-[var(--font-serif)] text-2xl sm:text-4xl font-bold text-white">
              Built for Citizens, Students & Lawyers
            </h2>
            <p className="text-sm text-slate-300 font-light">
              Tailored workspaces designed for both everyday legal clarity and deep professional litigation research.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            {/* Citizens & Students Card */}
            <div className="rounded-2xl border border-blue-500/20 bg-[#0C0E14] p-6 sm:p-8 space-y-4 hover:border-blue-500/40 transition-all">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/20 border border-blue-500/30 text-xl">
                  👤
                </span>
                <div>
                  <h3 className="text-lg font-bold text-blue-300">For Citizens & Students</h3>
                  <p className="text-xs text-slate-400">Everyday legal clarity & rights education</p>
                </div>
              </div>
              <ul className="space-y-2.5 text-xs sm:text-sm text-slate-300 font-light pt-2">
                <li className="flex items-start gap-2.5">
                  <span className="text-emerald-400 font-bold shrink-0">✓</span>
                  <span>Ask legal doubts in everyday words via text or Voice Input (Hindi & English).</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-emerald-400 font-bold shrink-0">✓</span>
                  <span>Understand tenant issues, consumer complaints, and traffic fines easily.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-emerald-400 font-bold shrink-0">✓</span>
                  <span>Interactive Legal Rights games and daily knowledge quizzes.</span>
                </li>
              </ul>
              <div className="pt-2">
                <Button href="/public/chat" variant="primary" className="w-full justify-center text-xs py-2.5">
                  Open Citizen Chat →
                </Button>
              </div>
            </div>

            {/* Legal Advocates Card */}
            <div className="rounded-2xl border border-amber-500/20 bg-[#0C0E14] p-6 sm:p-8 space-y-4 hover:border-amber-500/40 transition-all">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/20 border border-amber-500/30 text-xl">
                  ⚖️
                </span>
                <div>
                  <h3 className="text-lg font-bold text-amber-300">For Advocates & Legal Counsel</h3>
                  <p className="text-xs text-slate-400">High-speed litigation & drafting workspace</p>
                </div>
              </div>
              <ul className="space-y-2.5 text-xs sm:text-sm text-slate-300 font-light pt-2">
                <li className="flex items-start gap-2.5">
                  <span className="text-emerald-400 font-bold shrink-0">✓</span>
                  <span>Generate legal notices, bail petitions, and statutory affidavits.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-emerald-400 font-bold shrink-0">✓</span>
                  <span>Automatic cross-mapping of legacy IPC/CrPC sections to new BNS/BNSS 2023.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-emerald-400 font-bold shrink-0">✓</span>
                  <span>Upload case files into the Case Vault for deep multi-document analysis.</span>
                </li>
              </ul>
              <div className="pt-2">
                <Button href="/app/dashboard" variant="primary" className="w-full justify-center text-xs py-2.5">
                  Open Professional Suite →
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* FAQs Section */}
        <div className="max-w-3xl mx-auto space-y-6">
          <div className="text-center space-y-2">
            <span className="text-xs font-mono font-bold uppercase tracking-widest text-amber-400">
              Need Help?
            </span>
            <h2 className="font-[var(--font-serif)] text-2xl sm:text-3xl font-bold text-white">
              Frequently Asked Questions
            </h2>
            <p className="text-xs sm:text-sm text-slate-400">
              Clear answers to the most common questions about our platform.
            </p>
          </div>

          <div className="space-y-3">
            {FAQS.map((faq, idx) => (
              <div
                key={idx}
                className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 space-y-2 hover:border-white/20 transition-all"
              >
                <p className="text-sm font-semibold text-amber-300 flex items-center gap-2">
                  <span>💡</span>
                  <span>{faq.q}</span>
                </p>
                <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-light pl-7">
                  {faq.a}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Call to Action */}
        <div className="text-center space-y-4 py-8 rounded-3xl border border-white/10 bg-gradient-to-r from-blue-900/20 via-black to-amber-900/20 p-8 sm:p-12">
          <span className="text-3xl">🚀</span>
          <h3 className="text-2xl sm:text-3xl font-bold text-white">
            Ready to explore verified legal intelligence?
          </h3>
          <p className="text-xs sm:text-sm text-slate-300 max-w-lg mx-auto font-light">
            Start with our citizen assistant or log in to access the advocate workspace.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <Button href="/public/chat" variant="primary" className="py-3 px-6 text-sm font-semibold shadow-lg">
              Start Legal AI Chat →
            </Button>
            <Button href="/login" variant="ghost" className="py-3 px-6 text-sm">
              Sign In to Account
            </Button>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}