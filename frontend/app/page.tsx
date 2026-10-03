import { TopNav } from "@/components/layout/TopNav";
import { Footer } from "@/components/layout/Footer";
import { InteractiveHero } from "@/components/marketing/InteractiveHero";
import { RealWorldComparison } from "@/components/marketing/RealWorldComparison";
import { InteractivePipeline } from "@/components/marketing/InteractivePipeline";
import { CTASection } from "@/components/marketing/CTASection";

export default function LandingPage() {
  return (
    <>
      <TopNav />
      <main className="space-y-24 pb-20">
        {/* 1. Ultra-Pro Interactive Hero */}
        <InteractiveHero />

        {/* 2. Interactive Legal Verification Pipeline Flowchart */}
        <section className="mx-auto max-w-[1440px] px-6">
          <div className="text-center max-w-3xl mx-auto space-y-3 mb-12">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3.5 py-1 text-xs font-semibold text-amber-300">
              <span>🔄</span>
              <span>Verification Process</span>
            </div>
            <h2 className="font-[var(--font-serif)] text-3xl sm:text-4xl lg:text-5xl font-bold text-white tracking-tight">
              How Legal AI Verification Works
            </h2>
            <p className="text-slate-300 text-sm sm:text-base leading-relaxed font-light">
              An end-to-end flowchart showing how user questions or legal files pass through dual-stream Bare Act search, atomic claim isolation, and immutable cryptographic audit logging.
            </p>
          </div>
          <InteractivePipeline />
        </section>

        {/* 3. Real-World Comparison Matrix */}
        <section className="mx-auto max-w-[1440px] px-6">
          <div className="text-center max-w-3xl mx-auto space-y-3 mb-12">
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-3.5 py-1 text-xs font-semibold text-blue-300">
              <span>⚖️</span>
              <span>Comparative Benchmark</span>
            </div>
            <h2 className="font-[var(--font-serif)] text-3xl sm:text-4xl lg:text-5xl font-bold text-white tracking-tight">
              Why Generic LLMs Fail at Indian Law
            </h2>
            <p className="text-slate-300 text-sm sm:text-base leading-relaxed font-light">
              Comparing NyayaPramaan's citation-verified architecture against probabilistic models and traditional keyword search portals.
            </p>
          </div>
          <RealWorldComparison />
        </section>

        {/* 4. Call to Action */}
        <CTASection />
      </main>
      <Footer />
    </>
  );
}