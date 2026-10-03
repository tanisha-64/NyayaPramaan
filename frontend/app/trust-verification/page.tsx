import { TopNav } from "@/components/layout/TopNav";
import { Footer } from "@/components/layout/Footer";
import { InteractivePipeline } from "@/components/marketing/InteractivePipeline";
import { RealWorldComparison } from "@/components/marketing/RealWorldComparison";
import { CTASection } from "@/components/marketing/CTASection";

export default function TrustVerificationPage() {
  return (
    <>
      <TopNav />
      <main className="mx-auto max-w-[1440px] px-6 py-12 md:py-20 space-y-20">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-semibold uppercase tracking-[0.15em] text-emerald-300">
            <span>🛡️</span>
            <span>Trust & Verification Engine</span>
          </div>
          <h1 className="font-[var(--font-serif)] text-4xl sm:text-5xl lg:text-6xl font-bold text-white tracking-tight">
            Evidence-Verified. <br />
            <span className="gradient-text-gold">Not Evidence-Inspired.</span>
          </h1>
          <p className="text-slate-300 text-base sm:text-lg leading-relaxed font-light">
            In legal research, a single hallucinated section can invalidate an entire petition. NyayaPramaan tests every proposition against authoritative Bare Acts and Constitution Bench precedents before giving you an answer.
          </p>
        </div>

        {/* 1. Live Interactive Verification Pipeline */}
        <section className="space-y-6">
          <div className="text-center max-w-2xl mx-auto space-y-2 mb-8">
            <h2 className="text-2xl sm:text-3xl font-bold text-white">
              Standard 5-Step Verification Architecture
            </h2>
            <p className="text-xs sm:text-sm text-slate-400">
              Click any stage below to inspect the generic data transformation, bare act matching logic, and cryptographic verification flow.
            </p>
          </div>
          <InteractivePipeline />
        </section>

        {/* 2. Principles Grid */}
        <section className="grid gap-6 md:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 sm:p-8 space-y-3">
            <div className="flex items-center gap-2.5 text-emerald-400 text-base font-semibold">
              <span className="flex h-7 w-7 items-center justify-center rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-sm">
                ✓
              </span>
              <span>What "Verified" Means at NyayaPramaan</span>
            </div>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-light">
              A claim is marked <strong className="text-emerald-300">Supported / Binding</strong> only after our TrustAgent independently re-retrieves the exact Bare Act section or official judgment paragraph. If a claim cannot be verified, it is either automatically rewritten with correct law or flagged to the user.
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 sm:p-8 space-y-3">
            <div className="flex items-center gap-2.5 text-amber-400 text-base font-semibold">
              <span className="flex h-7 w-7 items-center justify-center rounded-xl bg-amber-500/20 border border-amber-500/30 text-sm">
                🎯
              </span>
              <span>Our Benchmark & Precision Targets</span>
            </div>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-light">
              We target citation verification accuracy exceeding <strong className="text-amber-300">95%+</strong> across Indian statutes. Every transaction is signed into a blockchain-style SHA-256 hash chain so that research audit trails remain tamper-evident for advocates and courts.
            </p>
          </div>
        </section>

        {/* 3. Comparison with other platforms */}
        <section className="space-y-8">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <h2 className="text-2xl sm:text-3xl font-bold text-white">
              Platform Verification Comparison
            </h2>
            <p className="text-xs sm:text-sm text-slate-400">
              How NyayaPramaan compares directly against generic LLMs and traditional legal databases.
            </p>
          </div>
          <RealWorldComparison />
        </section>

        {/* 4. Legal Disclaimer Notice */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5 text-center text-xs text-slate-400 max-w-3xl mx-auto">
          ⚠️ <strong>Statutory Notice:</strong> NyayaPramaan provides AI-assisted legal research and intelligence grounded in Indian law. It is designed to assist citizens, law students, and advocates, and does not replace formal advocate-client consultation.
        </div>

        {/* 5. CTA */}
        <CTASection />
      </main>
      <Footer />
    </>
  );
}