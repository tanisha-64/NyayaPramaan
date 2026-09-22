'use client'
import { ReactNode } from 'react'
import Link from 'next/link'

export function AuthLayout({
  children,
  title,
  subtitle,
}: {
  children: ReactNode
  title: string
  subtitle: string
}) {
  return (
    <div className="relative flex min-h-screen w-full items-center justify-center overflow-hidden bg-[#050608] px-4 py-12 transition-colors [data-theme=light]:bg-[#F4F6FB]">
      {/* Ambient Bloom Lights in Background */}
      <div className="bloom-orb-indigo top-[-50px] left-[-50px] opacity-75" />
      <div className="bloom-orb-amber bottom-[-80px] right-[-80px] opacity-60" />
      <div className="bloom-orb-cyan top-[40%] right-[10%] opacity-45" />

      {/* Top Bar with Brand */}
      <div className="absolute top-6 left-6 right-6 z-20 flex items-center justify-between">
        <Link href="/" className="group flex items-center gap-2.5 no-underline">
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-amber-500/20 via-blue-500/20 to-transparent border border-white/15 text-sm shadow-md transition-transform duration-300 group-hover:scale-105">
            ⚖️
          </span>
          <span className="font-[var(--font-serif)] text-lg font-medium tracking-wide text-white">
            NyayaPramaan
          </span>
        </Link>
      </div>

      {/* Glass Jelly Main Auth Card */}
      <div className="relative z-10 w-full max-w-[440px] rounded-3xl border border-white/[0.12] bg-[#0E121B]/70 p-8 shadow-2xl backdrop-blur-2xl transition-all [data-theme=light]:bg-white/80 [data-theme=light]:border-black/[0.08] [data-theme=light]:shadow-xl sm:p-10">
        
        {/* Floating Emblem */}
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="animate-text-float mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-blue-600/25 via-indigo-500/20 to-amber-500/20 border border-white/20 shadow-lg [data-theme=light]:border-black/10">
            <span className="text-xl">⚖️</span>
          </div>

          <h1 className="font-[var(--font-serif)] text-2xl font-semibold tracking-tight text-white [data-theme=light]:text-slate-900">
            {title}
          </h1>
          <p className="mt-2 text-xs text-slate-400 [data-theme=light]:text-slate-500 leading-relaxed max-w-xs">
            {subtitle}
          </p>
        </div>

        {/* Children (Form / Inputs / Actions) */}
        <div className="mt-6">{children}</div>

        {/* Trust Badges */}
        <div className="mt-8 border-t border-white/[0.06] [data-theme=light]:border-black/[0.06] pt-4 flex items-center justify-center gap-4 text-[11px] text-white/40 [data-theme=light]:text-slate-400">
          <span className="flex items-center gap-1">🔒 256-Bit Encrypted</span>
          <span>•</span>
          <span className="flex items-center gap-1">📜 Evidence-Verified</span>
        </div>
      </div>
    </div>
  )
}