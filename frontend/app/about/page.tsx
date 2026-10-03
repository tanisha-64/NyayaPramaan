import { TopNav } from "@/components/layout/TopNav";
import { Footer } from "@/components/layout/Footer";

export default function AboutPage() {
  return (
    <>
      <TopNav />
      <main className="min-h-screen bg-[#070B14] text-slate-100">
        {/* Hero */}
        <section className="mx-auto max-w-4xl px-6 pt-24 pb-16 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-4 py-1.5 text-xs font-semibold text-amber-300 mb-6">
            <span>⚖️</span>
            <span>About NyayaPramaan</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-white mb-6 leading-tight">
            न्यायप्रमाण — Evidence for Justice
          </h1>
          <p className="text-slate-300 text-base sm:text-lg leading-relaxed max-w-2xl mx-auto">
            NyayaPramaan is India's first enterprise-grade, verifiable, and citational AI legal research platform —
            built specifically for the Indian legal ecosystem to eliminate hallucinations and ensure every answer
            is grounded in Bare Acts, Supreme Court judgments, and authenticated legal sources.
          </p>
        </section>

        {/* Mission Cards */}
        <section className="mx-auto max-w-5xl px-6 pb-20">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
            {[
              {
                icon: "🎯",
                title: "Our Mission",
                desc: "To make verified, citational Indian legal intelligence accessible to every citizen, student, and practicing advocate — removing the barriers of complexity, cost, and misinformation.",
              },
              {
                icon: "🛡️",
                title: "Why We Built This",
                desc: "Generic AI systems frequently hallucinate Indian law — inventing non-existent sections, misquoting judgments, and conflating old IPC with new BNS/BNSS provisions. NyayaPramaan is the solution.",
              },
              {
                icon: "⚖️",
                title: "Our Commitment",
                desc: "Every response is verifiable. We show you exactly which statute, judgment, or court record supports it, with a cryptographic SHA-256 audit trail of every event.",
              },
            ].map((card) => (
              <div
                key={card.title}
                className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 space-y-3 hover:border-amber-500/30 transition-all"
              >
                <span className="text-3xl">{card.icon}</span>
                <h3 className="text-base font-bold text-white">{card.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{card.desc}</p>
              </div>
            ))}
          </div>

          {/* Platform Coverage */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-8 mb-10">
            <h2 className="text-2xl font-bold text-white mb-2">Indian Law Coverage</h2>
            <p className="text-sm text-slate-400 mb-6">NyayaPramaan's knowledge base spans the entire Indian legal corpus:</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {[
                { law: "Constitution of India", desc: "All Articles & Schedules" },
                { law: "Bharatiya Nyaya Sanhita (BNS 2023)", desc: "Replaces IPC" },
                { law: "Indian Penal Code (IPC)", desc: "Legacy Criminal Law" },
                { law: "BNSS 2023", desc: "Replaces CrPC" },
                { law: "Code of Criminal Procedure", desc: "CrPC (Legacy)" },
                { law: "Code of Civil Procedure", desc: "CPC" },
                { law: "Bharatiya Sakshya Adhiniyam", desc: "Replaces Indian Evidence Act" },
                { law: "Supreme Court Judgments", desc: "Landmark & Recent" },
                { law: "High Court Judgments", desc: "All State HCs" },
                { law: "Bare Acts", desc: "300+ Indian Statutes" },
                { law: "FIRs & Affidavits", desc: "Document Analysis" },
                { law: "Contracts & Deeds", desc: "Civil Disputes" },
              ].map((item) => (
                <div key={item.law} className="rounded-xl border border-amber-500/15 bg-amber-500/[0.04] p-3">
                  <div className="text-xs font-semibold text-amber-300 leading-tight">{item.law}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">{item.desc}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Core Principles */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-8 mb-10">
            <h2 className="text-2xl font-bold text-white mb-6">Core Principles</h2>
            <div className="space-y-4">
              {[
                {
                  num: "01",
                  title: "Verifiability Over Fluency",
                  desc: "Every AI response is broken into atomic factual claims and independently verified against source statutes and court records before being returned to you.",
                },
                {
                  num: "02",
                  title: "Transparency Over Trust",
                  desc: "We show you every source citation, every verification status (Verified / Partial / Unverified / Contradicted), and a tamper-evident SHA-256 audit log of every event.",
                },
                {
                  num: "03",
                  title: "Privacy by Design",
                  desc: "Your documents are private to your account. Sensitive Indian PII (Aadhaar numbers, PAN cards, phone numbers) is automatically redacted from all AI outputs.",
                },
                {
                  num: "04",
                  title: "Resilience by Architecture",
                  desc: "A 3-tier LLM fallback chain ensures zero single-point-of-failure. If one model is unavailable, the system seamlessly routes to the next with automatic caching.",
                },
              ].map((p) => (
                <div key={p.num} className="flex gap-4 border-b border-white/5 pb-4 last:border-0 last:pb-0">
                  <span className="text-2xl font-black text-amber-500/30 font-mono w-8 shrink-0">{p.num}</span>
                  <div>
                    <h4 className="text-sm font-bold text-white mb-1">{p.title}</h4>
                    <p className="text-sm text-slate-400 leading-relaxed">{p.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Disclaimer */}
          <div className="rounded-2xl border border-blue-500/20 bg-blue-500/[0.05] p-6 text-center">
            <p className="text-xs text-slate-400 leading-relaxed max-w-2xl mx-auto">
              <span className="text-blue-300 font-semibold">⚠️ Important: </span>
              NyayaPramaan is an AI-assisted legal research tool. It does not constitute formal legal advice and
              no attorney-client relationship is created by using this platform. All outputs should be verified
              with a qualified legal professional before relying on them for any legal matter.
            </p>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
