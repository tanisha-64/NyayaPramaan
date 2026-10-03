import Link from "next/link";

export function Footer() {
  return (
    <footer className="relative overflow-hidden border-t border-white/10 bg-[#05060A] pt-16 pb-12 transition-all">
      {/* Radiant Ambient Background Bloom Lighting */}
      <div className="bloom-orb-amber -top-24 left-1/4 opacity-40 pointer-events-none" />
      <div className="bloom-orb-indigo -bottom-24 right-1/4 opacity-35 pointer-events-none" />
      <div className="bloom-orb-cyan top-1/2 -left-20 opacity-25 pointer-events-none" />

      <div className="relative z-10 mx-auto max-w-[1440px] px-6 space-y-12">
        {/* Top Interactive Feature Highlight Banner */}
        <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-r from-amber-500/10 via-blue-500/10 to-emerald-500/10 p-6 sm:p-8 backdrop-blur-2xl shadow-[0_0_40px_rgba(0,0,0,0.6)]">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="space-y-1.5 text-center md:text-left">
              <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/15 px-3 py-0.5 text-[11px] font-bold text-amber-300">
                <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>Next-Gen Legal AI Platform</span>
              </div>
              <h3 className="font-[var(--font-serif)] text-xl sm:text-2xl font-bold text-white tracking-wide">
                Evidence-Grounded Intelligence for Every Indian Citizen & Advocate
              </h3>
              <p className="text-xs sm:text-sm text-slate-300 font-light max-w-xl">
                Cross-referenced with official Bare Acts, Supreme Court constitutional ratios, and immutable SHA-256 cryptographic audit logs.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3 shrink-0">
              <Link
                href="/public/chat"
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 px-5 py-2.5 text-xs font-semibold text-black shadow-[0_0_20px_rgba(200,155,89,0.35)] hover:scale-105 transition-transform no-underline"
              >
                <span>Citizen AI Chat 💬</span>
              </Link>
              <Link
                href="/app/dashboard"
                className="inline-flex items-center gap-2 rounded-xl border border-white/20 bg-white/[0.05] px-4 py-2.5 text-xs font-semibold text-white hover:bg-white/10 hover:border-white/30 transition-all no-underline"
              >
                <span>Advocate Workspace ⚖️</span>
              </Link>
            </div>
          </div>
        </div>

        {/* Main Footer Links Grid (Cleanly Categorized & Deduplicated) */}
        <div className="grid gap-8 sm:grid-cols-2 md:grid-cols-4 pt-4 border-t border-white/[0.08]">
          {/* Column 1: Brand & Mission */}
          <div className="space-y-4">
            <Link href="/" className="flex items-center gap-2.5 no-underline group">
              <span className="flex h-9 w-9 items-center justify-center rounded-2xl bg-gradient-to-tr from-amber-500/30 via-blue-500/30 to-transparent border border-white/20 text-lg shadow-md group-hover:scale-110 transition-transform">
                ⚖️
              </span>
              <span className="font-[var(--font-serif)] text-xl tracking-wide text-white font-bold">
                NyayaPramaan
              </span>
            </Link>
            <p className="text-xs text-slate-400 leading-relaxed font-light">
              Democratizing evidence-verified Indian legal intelligence. Zero hallucinations, pure statutory citations.
            </p>
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <span className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-mono font-semibold text-emerald-300">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
                <span>BNS & IPC 2023 Live</span>
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-lg border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-[10px] font-mono font-semibold text-amber-300">
                <span>SHA-256 Ledger</span>
              </span>
            </div>
          </div>

          {/* Column 2: Citizen & Student Portal (Role: Public) */}
          <div className="space-y-3">
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-blue-400 font-mono">
              <span>👤</span>
              <span>Citizen & Student Hub</span>
            </div>
            <ul className="space-y-2 text-xs text-slate-300">
              <li>
                <Link href="/public/chat" className="hover:text-blue-300 transition-colors flex items-center gap-1.5">
                  <span>💬</span>
                  <span>Citizen Legal AI Assistant</span>
                </Link>
              </li>
              <li>
                <Link href="/game" className="hover:text-blue-300 transition-colors flex items-center gap-1.5">
                  <span>🎮</span>
                  <span>Legal Rights Adventure Game</span>
                </Link>
              </li>
              <li>
                <Link href="/quiz" className="hover:text-blue-300 transition-colors flex items-center gap-1.5">
                  <span>🎯</span>
                  <span>Daily Indian Law Quiz</span>
                </Link>
              </li>
              <li>
                <Link href="/news" className="hover:text-blue-300 transition-colors flex items-center gap-1.5">
                  <span>📰</span>
                  <span>Latest Legal News & Updates</span>
                </Link>
              </li>
              <li>
                <Link href="/public/saved" className="hover:text-blue-300 transition-colors flex items-center gap-1.5">
                  <span>⭐</span>
                  <span>Saved Research Bookmarks</span>
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 3: Professional Advocate Suite (Role: Professional) */}
          <div className="space-y-3">
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-amber-300 font-mono">
              <span>⚖️</span>
              <span>Advocate Research Suite</span>
            </div>
            <ul className="space-y-2 text-xs text-slate-300">
              <li>
                <Link href="/app/dashboard" className="hover:text-amber-300 transition-colors flex items-center gap-1.5">
                  <span>🏛️</span>
                  <span>Advocate Dashboard & Vault</span>
                </Link>
              </li>
              <li>
                <Link href="/app/dashboard" className="hover:text-amber-300 transition-colors flex items-center gap-1.5">
                  <span>🔍</span>
                  <span>Precedent Search & Court Filter</span>
                </Link>
              </li>
              <li>
                <Link href="/register" className="hover:text-amber-300 transition-colors flex items-center gap-1.5">
                  <span>📝</span>
                  <span>Create Advocate Account</span>
                </Link>
              </li>
              <li>
                <Link href="/login" className="hover:text-amber-300 transition-colors flex items-center gap-1.5">
                  <span>🔐</span>
                  <span>Advocate Sign In Portal</span>
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 4: Platform Transparency & Info */}
          <div className="space-y-3">
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-purple-300 font-mono">
              <span>🛡️</span>
              <span>Transparency & Help</span>
            </div>
            <ul className="space-y-2 text-xs text-slate-300">
              <li>
                <Link href="/how-it-works" className="hover:text-purple-300 transition-colors flex items-center gap-1.5">
                  <span>⚡</span>
                  <span>How It Works (4 Steps)</span>
                </Link>
              </li>
              <li>
                <Link href="/trust-verification" className="hover:text-purple-300 transition-colors flex items-center gap-1.5">
                  <span>🛡️</span>
                  <span>Trust & Verification Engine</span>
                </Link>
              </li>
              <li>
                <Link href="/about" className="hover:text-purple-300 transition-colors flex items-center gap-1.5">
                  <span>ℹ️</span>
                  <span>About Our Mission</span>
                </Link>
              </li>
              <li>
                <Link href="/disclaimer" className="hover:text-purple-300 transition-colors flex items-center gap-1.5">
                  <span>📜</span>
                  <span>Legal Disclaimer & Policy</span>
                </Link>
              </li>
            </ul>
            <div className="pt-1">
              <div className="rounded-xl border border-white/5 bg-white/[0.02] p-2.5 text-[10px] text-slate-400 font-light leading-relaxed">
                ⚖️ <strong>Informational Note:</strong> AI research assistance only; not a substitute for formal legal representation.
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Copyright & Security Strip */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-white/[0.08] pt-8 text-xs text-slate-400 font-light">
          <div className="flex items-center gap-2">
            <span>© {new Date().getFullYear()} NyayaPramaan. All rights reserved.</span>
            <span className="text-slate-600">•</span>
            <span className="text-slate-400">Made for India 🇮🇳</span>
          </div>

          <div className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1.5 text-emerald-400 font-mono text-[11px]">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              <span>All Systems Operational</span>
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}