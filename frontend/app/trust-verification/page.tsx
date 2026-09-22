// export default function Page() {
//   return <div>Phase pending: trust-verification</div>
// }

import { TopNav } from "@/components/layout/TopNav";
import { Footer } from "@/components/layout/Footer";
import { Badge } from "@/components/ui/Badge";

export default function TrustVerificationPage() {
  return (
    <>
      <TopNav />
      <main className="mx-auto max-w-[1440px] px-6 py-20">
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--color-trust-blue)]">Trust & Verification</p>
        <h1 className="mt-4 font-[var(--font-serif)] text-4xl text-[var(--color-ivory)] md:text-5xl max-w-2xl">
          Evidence-verified. Not evidence-inspired.
        </h1>

        <div className="mt-16 grid gap-10 md:grid-cols-2">
          <div>
            <h2 className="text-lg font-medium text-[var(--color-ivory)]">What "verified" means here</h2>
            <p className="mt-3 text-white/60 leading-relaxed">
              A claim is marked <Badge status="verified" /> only after
              NyayaPramaan's TrustAgent re-retrieves the original source and
              confirms the claim is supported by it. If a claim cannot be
              confirmed, it is corrected or explicitly flagged.
            </p>
          </div>
          <div>
            <h2 className="text-lg font-medium text-[var(--color-ivory)]">What we do not claim</h2>
            <p className="mt-3 text-white/60 leading-relaxed">
              We do not claim 100% accuracy or a hallucination-free system.
              NyayaPramaan targets a citation-verification accuracy above 95%
              (<Badge status="target" />), benchmarked against documented
              industry baselines.
            </p>
          </div>
        </div>

        <div className="mt-16 rounded-lg border border-white/10 bg-white/[0.02] p-6 text-sm text-white/50">
          This platform provides AI-assisted legal information and research
          support. It does not constitute legal advice.
        </div>
      </main>
      <Footer />
    </>
  );
}