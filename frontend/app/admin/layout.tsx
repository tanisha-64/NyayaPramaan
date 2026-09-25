'use client'
import React from 'react'
import { RoleGuard } from '@/components/auth/RoleGuard'

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <RoleGuard allowedRole="admin">
      <div className="min-h-screen bg-[#141414] text-slate-100 selection:bg-amber-500/30">
        {children}
      </div>
    </RoleGuard>
  )
}
