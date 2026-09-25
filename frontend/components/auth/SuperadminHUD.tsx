'use client'
import React, { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'

/**
 * SuperadminHUD — Persistent floating control bar for the Superadmin.
 * Visible ONLY to verified Admin accounts (e.g. mitanisha74@gmail.com).
 * Allows 1-click preview and navigation across:
 * - 🧑‍🎓 Citizen & Student Research (/public/chat)
 * - ⚖️ Professional Case Workspace (/app/dashboard)
 * - 🛠️ System Admin Console (/admin)
 */
export function SuperadminHUD() {
  const { user, isAdmin, signOut } = useAuth()
  const pathname = usePathname()
  const [minimized, setMinimized] = useState(false)

  if (!isAdmin || !user) return null

  const isCitizenPath = pathname.startsWith('/public')
  const isProfessionalPath = pathname.startsWith('/app')
  const isAdminPath = pathname.startsWith('/admin')

  const currentViewName = isCitizenPath
    ? '🧑‍🎓 Citizen / Student View'
    : isProfessionalPath
    ? '⚖️ Legal Professional Workspace'
    : isAdminPath
    ? '🛠️ System Admin Console'
    : '🌐 Public Portal'

  const currentBadgeColor = isCitizenPath
    ? 'border-[#B8925A]/40 bg-[#B8925A]/15 text-[#E6CA92]'
    : isProfessionalPath
    ? 'border-[#2B5CE0]/40 bg-[#2B5CE0]/15 text-[#93B4FF]'
    : 'border-[#D9A441]/40 bg-[#D9A441]/15 text-[#F3C769]'

  return (
    <div
      className="fixed bottom-4 right-4 z-[9999] transition-all duration-300 font-sans"
      style={{ filter: 'drop-shadow(0 10px 25px rgba(0,0,0,0.6))' }}
    >
      {minimized ? (
        <button
          onClick={() => setMinimized(false)}
          className="flex items-center gap-2 rounded-full border border-amber-500/40 bg-[#0C0E14]/95 px-3.5 py-2 text-xs font-semibold text-amber-300 shadow-2xl backdrop-blur-xl hover:scale-105 transition-all cursor-pointer"
          title="Open Superadmin Workspace Switcher"
        >
          <span>👑</span>
          <span className="hidden sm:inline">Admin Mode</span>
          <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
        </button>
      ) : (
        <div className="flex flex-col gap-2 rounded-2xl border border-amber-500/30 bg-[#0C0E14]/95 p-3 text-xs text-white shadow-2xl backdrop-blur-xl max-w-[440px]">
          {/* Header */}
          <div className="flex items-center justify-between gap-2 border-b border-white/10 pb-2">
            <div className="flex items-center gap-2">
              <span className="flex h-5 w-5 items-center justify-center rounded-lg bg-amber-500/20 text-xs border border-amber-500/30">
                👑
              </span>
              <span className="font-semibold text-amber-300 tracking-wide text-[11px] uppercase">
                Superadmin Switcher
              </span>
              <span className="text-[10px] text-slate-400 truncate max-w-[140px]" title={user.email || ''}>
                {user.email}
              </span>
            </div>
            <button
              onClick={() => setMinimized(true)}
              className="rounded-lg p-1 text-slate-400 hover:bg-white/10 hover:text-white transition-colors cursor-pointer text-xs"
              title="Minimize bar"
            >
              ✕
            </button>
          </div>

          {/* Current view indicator */}
          <div className="flex items-center justify-between text-[11px] px-1">
            <span className="text-slate-400">Currently inspecting:</span>
            <span className={`rounded-md border px-2 py-0.5 font-medium ${currentBadgeColor}`}>
              {currentViewName}
            </span>
          </div>

          {/* View Jump Links */}
          <div className="grid grid-cols-3 gap-1.5 pt-1">
            <Link
              href="/public/chat"
              className={`flex flex-col items-center justify-center gap-0.5 rounded-xl border p-2 text-center transition-all no-underline ${
                isCitizenPath
                  ? 'border-[#B8925A] bg-[#B8925A]/20 text-amber-200 shadow-inner'
                  : 'border-white/10 bg-white/[0.03] text-slate-300 hover:bg-white/[0.08] hover:text-white hover:border-[#B8925A]/30'
              }`}
            >
              <span className="text-sm">🧑‍🎓</span>
              <span className="font-medium text-[10px] leading-tight">Citizen Chat</span>
            </Link>

            <Link
              href="/app/dashboard"
              className={`flex flex-col items-center justify-center gap-0.5 rounded-xl border p-2 text-center transition-all no-underline ${
                isProfessionalPath
                  ? 'border-[#2B5CE0] bg-[#2B5CE0]/20 text-blue-200 shadow-inner'
                  : 'border-white/10 bg-white/[0.03] text-slate-300 hover:bg-white/[0.08] hover:text-white hover:border-[#2B5CE0]/30'
              }`}
            >
              <span className="text-sm">⚖️</span>
              <span className="font-medium text-[10px] leading-tight">Professional</span>
            </Link>

            <Link
              href="/admin"
              className={`flex flex-col items-center justify-center gap-0.5 rounded-xl border p-2 text-center transition-all no-underline ${
                isAdminPath
                  ? 'border-[#D9A441] bg-[#D9A441]/20 text-amber-200 shadow-inner'
                  : 'border-white/10 bg-white/[0.03] text-slate-300 hover:bg-white/[0.08] hover:text-white hover:border-[#D9A441]/30'
              }`}
            >
              <span className="text-sm">🛠️</span>
              <span className="font-medium text-[10px] leading-tight">Admin Console</span>
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
