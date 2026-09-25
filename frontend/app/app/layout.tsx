'use client'
import React from 'react'
import { RoleGuard } from '@/components/auth/RoleGuard'

export default function ProfessionalAppLayout({ children }: { children: React.ReactNode }) {
  return (
    <RoleGuard allowedRole="professional">
      <div className="min-h-screen bg-[#0F1B2E] text-slate-100 selection:bg-blue-500/30">
        {children}
      </div>
    </RoleGuard>
  )
}
