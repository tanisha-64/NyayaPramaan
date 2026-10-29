'use client'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import { RoleGuard } from '@/components/auth/RoleGuard'
import { getAdminMetrics, getJudgmentsCount, getAdminActivity, getAdminHealth, AdminMetrics, AdminActivity, HealthCheck } from '@/services/adminService'

function AdminContent() {
  const { user, signOut } = useAuth()

  const [metrics, setMetrics] = useState<AdminMetrics | null>(null)
  const [judgmentCount, setJudgmentCount] = useState<number | null>(null)
  const [activity, setActivity] = useState<AdminActivity | null>(null)
  const [health, setHealth] = useState<HealthCheck[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    if (user) fetchData()
  }, [user])

  async function fetchData() {
    setLoading(true)
    try {
      const [m, j, a, h] = await Promise.allSettled([
        getAdminMetrics(), getJudgmentsCount(), getAdminActivity(), getAdminHealth(),
      ])
      if (m.status === 'fulfilled') setMetrics(m.value)
      if (j.status === 'fulfilled') setJudgmentCount(j.value.total_judgments)
      if (a.status === 'fulfilled') setActivity(a.value)
      if (h.status === 'fulfilled') setHealth(h.value.checks)
    } catch (err) {
      console.error('Failed to load admin metrics:', err)
    }
    setLoading(false)
  }

  async function handleRefresh() {
    setRefreshing(true)
    await fetchData()
    setRefreshing(false)
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#141414] text-slate-400 font-mono text-sm">
        <div className="flex items-center gap-3">
          <span className="h-2.5 w-2.5 rounded-full bg-[#D9A441] animate-pulse-dot" />
          <span>Loading NyayaPramaan System Console Metrics...</span>
        </div>
      </div>
    )
  }

  const accuracyPercent = metrics?.citation_accuracy_rate != null
    ? Math.round(metrics.citation_accuracy_rate * 100)
    : null

  const modelUsage = metrics?.model_usage_breakdown || {}
  const hasModelUsage = Object.keys(modelUsage).length > 0
  const totalModelCalls = Object.values(modelUsage).reduce((a, b) => a + b, 0) || 1

  return (
    <div className="min-h-screen bg-[#141414] text-[#E8E6E1] font-mono antialiased">
      {/* Top Header — Technical Charcoal with Amber accent */}
      <header className="border-b border-[#D9A441]/15 bg-[#1A1A1A]/95 backdrop-blur-2xl sticky top-0 z-30">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3 flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2.5 text-white no-underline">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#D9A441]/15 border border-[#D9A441]/25 text-sm">
                🛡️
              </span>
              <span className="text-sm font-bold tracking-wider uppercase text-[#D9A441]">
                NYAYAPRAMAAN
              </span>
            </Link>
            <span className="rounded bg-[#D9A441]/12 border border-[#D9A441]/25 px-2 py-0.5 text-[10px] font-bold text-[#D9A441] tracking-widest uppercase">
              SYSTEM CONSOLE
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-1.5 rounded-lg border border-[#D9A441]/20 bg-[#D9A441]/[0.06] px-3 py-1.5 text-[11px] text-[#D9A441] hover:bg-[#D9A441]/15 transition-all cursor-pointer font-bold tracking-wider uppercase"
            >
              {refreshing ? '⟳ REFRESHING...' : '⟳ REFRESH'}
            </button>
            <Link
              href="/app/dashboard"
              className="rounded-lg bg-[#2B5CE0]/80 px-3 py-1.5 text-[11px] font-bold text-white hover:bg-[#2B5CE0] transition-all no-underline tracking-wider uppercase"
            >
              LAWYER WORKSPACE
            </Link>
            <button
              onClick={signOut}
              className="rounded-lg border border-red-500/25 bg-red-500/10 px-3 py-1.5 text-[11px] text-red-400 hover:bg-red-500/20 transition-all cursor-pointer font-bold tracking-wider uppercase"
            >
              LOG OUT
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-6 py-6 space-y-6">
        {/* System Banner — Compact, technical */}
        <div className="rounded-xl border border-[#D9A441]/12 bg-gradient-to-r from-[#1A1A1A] via-[#181818] to-[#1A1A1A] p-5">
          <div className="flex items-center gap-2 mb-1">
            <span className="h-2 w-2 rounded-full bg-[#D9A441] animate-pulse-dot" />
            <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-[#D9A441]">
              SYSTEM OPERATIONS & VERIFICATION TELEMETRY
            </span>
          </div>
          <h1 className="text-lg font-bold tracking-tight text-white">
            Trust & Evidence Health Dashboard
          </h1>
          <p className="mt-0.5 text-[11px] text-[#E8E6E1]/40 max-w-2xl leading-relaxed font-mono">
            Live telemetry: verification accuracy, vector store corpus, model routing, guardrail protections.
          </p>
        </div>

        {/* 4 KPI Grid — Technical, compact cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <KPICard
            label="TOTAL QUERIES"
            value={metrics?.total_queries ?? 0}
            sublabel="across all portals"
            color="#D9A441"
          />
          <KPICard
            label="EVIDENCE VERIFIED"
            value={metrics?.verified_count ?? 0}
            sublabel="pgvector cross-checked"
            color="#10B981"
          />
          <KPICard
            label="CITATION ACCURACY"
            value={accuracyPercent != null ? `${accuracyPercent}%` : '—'}
            sublabel="4-level TrustAgent"
            color="#D9A441"
          />
          <KPICard
            label="INDEXED JUDGMENTS"
            value={judgmentCount != null ? judgmentCount.toLocaleString() : '—'}
            sublabel="SC & HC cases"
            color="#5B8DEF"
          />
        </div>

        {/* 2-Column: Model Usage + Trust Pipeline */}
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Left: Model Routing Breakdown */}
          <section className="w-full lg:w-1/2 min-w-0 rounded-xl border border-[#D9A441]/10 bg-[#1A1A1A] p-5 space-y-4">
            <div className="border-b border-[#D9A441]/10 pb-2.5">
              <h2 className="text-[11px] font-bold uppercase tracking-[0.12em] text-[#D9A441]">
                MULTI-MODEL ROUTING & LLM GATEWAY
              </h2>
              <p className="text-[10px] text-[#E8E6E1]/35 mt-0.5 font-mono">
                Workload distribution across free-tier models
              </p>
            </div>

            {hasModelUsage ? (
              <div className="space-y-3.5">
                {Object.entries(modelUsage).map(([model, count]) => {
                  const pct = Math.round((count / totalModelCalls) * 100)
                  return (
                    <div key={model} className="space-y-1">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-mono text-[#E8E6E1]/70 truncate max-w-[250px]">{model}</span>
                        <span className="text-[#D9A441] font-bold tabular-nums">{count} ({pct}%)</span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-white/[0.06] overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-700"
                          style={{
                            width: `${pct}%`,
                            background: `linear-gradient(90deg, #D9A441, #E5B84A)`,
                          }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-[11px] text-[#E8E6E1]/35 font-mono">No queries logged yet.</p>
            )}
          </section>

          {/* Right: Trust Pipeline Health — real checks from /admin/health */}
          <section className="w-full lg:w-1/2 min-w-0 rounded-xl border border-[#D9A441]/10 bg-[#1A1A1A] p-5 space-y-4">
            <div className="border-b border-[#D9A441]/10 pb-2.5">
              <h2 className="text-[11px] font-bold uppercase tracking-[0.12em] text-[#D9A441]">
                CORE TRUST ENGINE STATUS
              </h2>
              <p className="text-[10px] text-[#E8E6E1]/35 mt-0.5 font-mono">
                Live pings — database, LLM gateway, citation verifier
              </p>
            </div>

            {health.length > 0 ? (
              <div className="space-y-2">
                {health.map((item, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between rounded-lg border border-[#D9A441]/08 bg-[#D9A441]/[0.03] p-3 text-[11px]"
                  >
                    <div className="flex items-center gap-2.5">
                      <span className={`h-1.5 w-1.5 rounded-full ${item.ok ? 'bg-emerald-400' : 'bg-red-400'} animate-pulse-dot`} />
                      <span className="font-mono text-[#E8E6E1]/70">{item.name}</span>
                    </div>
                    <span className={`text-[10px] font-bold tracking-wider px-2 py-0.5 rounded border uppercase ${item.ok ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' : 'text-red-400 bg-red-500/10 border-red-500/20'}`}>
                      {item.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[11px] text-[#E8E6E1]/35 font-mono">Could not run health checks.</p>
            )}
          </section>
        </div>

        {/* User Activity — real counts from /admin/activity */}
        <section className="rounded-xl border border-[#D9A441]/10 bg-[#1A1A1A] p-5 space-y-4">
          <div className="border-b border-[#D9A441]/10 pb-2.5">
            <h2 className="text-[11px] font-bold uppercase tracking-[0.12em] text-[#D9A441]">
              PLATFORM USER ACTIVITY
            </h2>
            <p className="text-[10px] text-[#E8E6E1]/35 mt-0.5 font-mono">
              Real counts from the database
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              { label: 'Total Registered Users', value: activity?.total_registered_users ?? '—', icon: '👥', color: '#5B8DEF' },
              { label: 'Active Users (Today)', value: activity?.active_users_today ?? '—', icon: '🟢', color: '#10B981' },
            ].map((stat) => (
              <div key={stat.label} className="flex items-center justify-between rounded-lg border border-white/[0.05] bg-white/[0.02] px-4 py-3">
                <div className="flex items-center gap-2.5">
                  <span className="text-sm">{stat.icon}</span>
                  <span className="text-[11px] font-mono text-[#E8E6E1]/70">{stat.label}</span>
                </div>
                <span className="text-sm font-black tabular-nums" style={{ color: stat.color }}>{stat.value}</span>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}

function KPICard({
  label,
  value,
  sublabel,
  color,
}: {
  label: string
  value: string | number
  sublabel: string
  color: string
}) {
  return (
    <div
      className="rounded-xl border p-4 space-y-1.5"
      style={{
        borderColor: `${color}15`,
        background: `linear-gradient(180deg, ${color}08 0%, #14141400 100%)`,
      }}
    >
      <span className="text-[10px] font-bold uppercase tracking-[0.12em]" style={{ color: `${color}90` }}>
        {label}
      </span>
      <div className="text-2xl font-black tabular-nums" style={{ color }}>
        {value}
      </div>
      <p className="text-[10px] text-[#E8E6E1]/30 font-mono">{sublabel}</p>
    </div>
  )
}

export default function AdminPage() {
  return (
    <RoleGuard allowedRole="admin">
      <AdminContent />
    </RoleGuard>
  )
}