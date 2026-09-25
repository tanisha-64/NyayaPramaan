'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { SuperadminHUD } from './SuperadminHUD'

const ROLE_HOME: Record<string, string> = {
  admin: '/admin',
  professional: '/app/dashboard',
  public: '/public/chat',
}

/**
 * RoleGuard — Reusable route-protection wrapper.
 * Wraps any page content and ensures strict isolation & security:
 * - Not logged in → redirects to /login?redirect=...
 * - Superadmin (isAdmin) → UNIVERSAL ACCESS to all 3 workspaces (Citizen, Professional, Admin)
 * - Regular Citizen ('public') → ONLY allowed in /public/* routes. Blocked from /app and /admin.
 * - Regular Professional ('professional') → Allowed in /app/* and /public/*. Blocked from /admin.
 * - Admin Console (/admin/*) → STRICTLY restricted to Superadmin email (mitanisha74@gmail.com).
 */
export function RoleGuard({
  allowedRole,
  children,
}: {
  allowedRole: 'admin' | 'professional' | 'public'
  children: React.ReactNode
}) {
  const { user, role, isAdmin, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (loading) return

    // 1. Unauthenticated users must log in
    if (!user) {
      router.push(`/login?redirect=${encodeURIComponent(ROLE_HOME[allowedRole] || '/')}`)
      return
    }

    // 2. Superadmin has universal access to all portals
    if (isAdmin) {
      return
    }

    // 3. Regular users trying to access Admin console are strictly blocked
    if (allowedRole === 'admin') {
      const fallback = role === 'professional' ? '/app/dashboard' : '/public/chat'
      router.push(fallback)
      return
    }

    // 4. Regular Citizen trying to access Professional Workspace is blocked
    if (allowedRole === 'professional' && role === 'public') {
      router.push('/public/chat')
      return
    }
  }, [loading, user, role, isAdmin, allowedRole, router])

  if (loading || !user) {
    return (
      <div
        className="role-guard-loading"
        style={{
          height: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '12px',
          fontFamily: 'var(--font-sans, Inter, sans-serif)',
          fontSize: '13px',
          letterSpacing: '0.02em',
        }}
      >
        <span
          style={{
            width: 10,
            height: 10,
            borderRadius: '50%',
            background:
              allowedRole === 'admin'
                ? '#D9A441'
                : allowedRole === 'professional'
                ? '#2B5CE0'
                : '#B8925A',
            animation: 'pulse-dot 1.4s ease-in-out infinite',
          }}
        />
        <span style={{ opacity: 0.6 }}>
          {allowedRole === 'admin'
            ? 'Initializing System Console…'
            : allowedRole === 'professional'
            ? 'Loading Case Workspace…'
            : 'Preparing Legal Research…'}
        </span>
      </div>
    )
  }

  // Access check for non-admin
  if (!isAdmin) {
    if (allowedRole === 'admin') {
      return null
    }
    if (allowedRole === 'professional' && role === 'public') {
      return null
    }
  }

  return (
    <>
      <SuperadminHUD />
      {children}
    </>
  )
}

