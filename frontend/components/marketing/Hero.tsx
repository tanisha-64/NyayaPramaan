import { Button } from "@/components/ui/Button";
import { LadyJusticePlaceholder } from "./LadyJusticePlaceholder";

export function Hero() {
  return (
    <section className="relative mx-auto grid max-w-[1440px] gap-12 px-6 py-16 lg:grid-cols-12 lg:items-center lg:py-24">
      {/* Left Column: Headlines & Call to Actions */}
      <div className="lg:col-span-7">
        <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.15em] text-amber-400 mb-6">
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z" />
          </svg>
          <span>India's Evidence-Verified Legal AI</span>
        </div>
        
        <h1 className="font-[var(--font-serif)] text-4xl font-semibold leading-[1.15] text-[var(--color-ivory)] sm:text-5xl lg:text-6xl">
          Legal AI, Verified by Evidence.
        </h1>
        
        <p className="mt-6 max-w-xl text-base leading-relaxed text-slate-300 sm:text-lg">
          Zero hallucination. Page-level statutory citations. Cross-examine multi-page case files against Indian Statutes (BNS, BNSS, IPC, CrPC) with tamper-evident audit logs.
        </p>

        <div className="mt-8 flex flex-wrap gap-4">
          <Button href="/public/chat" variant="primary">Start Legal Research ➔</Button>
          <Button href="/trust-verification" variant="secondary">See Verification Engine</Button>
        </div>

        <div className="mt-10 flex flex-wrap gap-6 text-xs text-white/50 border-t border-white/10 pt-6">
          <span className="flex items-center gap-1.5">
            <svg className="h-4 w-4 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>
            Citation Verified
          </span>
          <span className="flex items-center gap-1.5">
            <svg className="h-4 w-4 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="m9 15 2 2 4-4"/></svg>
            Multi-Doc RAG
          </span>
          <span className="flex items-center gap-1.5">
            <svg className="h-4 w-4 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            Tamper-Proof Audit
          </span>
        </div>
      </div>

      {/* Right Column: Original Clean Placeholder */}
      <div className="lg:col-span-5">
        <LadyJusticePlaceholder />
      </div>
    </section>
  );
}