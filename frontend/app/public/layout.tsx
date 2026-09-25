'use client'
import React from 'react'
import { RoleGuard } from '@/components/auth/RoleGuard'

export default function PublicCitizenLayout({ children }: { children: React.ReactNode }) {
  return (
    <RoleGuard allowedRole="public">
      <div className="min-h-screen bg-[#0A0A0B] text-slate-100 selection:bg-amber-500/30">
        {children}
      </div>
    </RoleGuard>
  )
}
