// export default function Page() {
//   return <div>Phase pending: how-it-works</div>
// }

import { TopNav } from "@/components/layout/TopNav";
import { Footer } from "@/components/layout/Footer";
import { ProcessDiagram } from "@/components/marketing/ProcessDiagram";
import { ComparisonBlock } from "@/components/marketing/ComparisonBlock";

export default function HowItWorksPage() {
  return (
    <>
      <TopNav />
      <main className="mx-auto max-w-[1440px] px-6 py-20">
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--color-gold)]">How It Works</p>
        <h1 className="mt-4 font-[var(--font-serif)] text-4xl text-[var(--color-ivory)] md:text-5xl max-w-2xl">
          From question to verified answer.
        </h1>
        <p className="mt-4 max-w-xl text-white/60">
          Retrieval alone does not stop an AI model from generating a
          plausible but incorrect citation. NyayaPramaan adds an explicit
          verification step after every draft.
        </p>

        <div className="mt-20">
          <ProcessDiagram />
        </div>

        <div className="mt-20">
          <h2 className="mb-10 font-[var(--font-serif)] text-2xl text-[var(--color-ivory)]">
            Why this matters
          </h2>
          <ComparisonBlock />
        </div>
      </main>
      <Footer />
    </>
  );
}