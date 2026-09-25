import { TopNav } from "@/components/layout/TopNav";
import { Footer } from "@/components/layout/Footer";
import { InteractivePipeline } from "@/components/marketing/InteractivePipeline";
import { RealWorldComparison } from "@/components/marketing/RealWorldComparison";
import { CTASection } from "@/components/marketing/CTASection";

export default function HowItWorksPage() {
  return (
    <>
      <TopNav />
      <main className="mx-auto max-w-[1440px] px-6 py-12 md:py-20 space-y-24">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3.5 py-1 text-xs font-semibold uppercase tracking-[0.15em] text-amber-300">
            <span>⚡</span>
            <span>How NyayaPramaan Works</span>
          </div>
          <h1 className="font-[var(--font-serif)] text-4xl sm:text-5xl lg:text-6xl font-bold text-white tracking-tight">
            From Legal Question to <span className="gradient-text-gold">Verified Citation</span>.
          </h1>
          <p className="text-slate-300 text-base sm:text-lg leading-relaxed font-light">
            Retrieval alone cannot stop an AI model from inventing plausible section numbers. NyayaPramaan enforces a mandatory 5-stage pipeline with post-generation claim extraction and dual-pass verification.
          </p>
        </div>

        {/* 1. Interactive 5-Stage Stepper Pipeline */}
        <section>
          <div className="text-center mb-10 space-y-2">
            <h2 className="text-2xl sm:text-3xl font-bold text-white">
              The 5-Stage Evidence Verification Engine
            </h2>
            <p className="text-xs sm:text-sm text-slate-400">
              Click any stage below to inspect live inputs, internal transformations, and verified outputs.
            </p>
          </div>
          <InteractivePipeline />
        </section>

        {/* 2. Comparative Matrix */}
        <section className="space-y-8">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <h2 className="text-2xl sm:text-3xl font-bold text-white">
              Why Dual-Pass Verification Matters
            </h2>
            <p className="text-xs sm:text-sm text-slate-400">
              Comparing how NyayaPramaan prevents legal hallucinations versus single-pass generative AI chatbots.
            </p>
          </div>
          <RealWorldComparison />
        </section>

        {/* 3. CTA */}
        <CTASection />
      </main>
      <Footer />
    </>
  );
}