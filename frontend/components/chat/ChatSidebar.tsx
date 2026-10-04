'use client'
import { useState, useMemo } from 'react'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { ChatSettingsModal } from './ChatSettingsModal'
import Link from 'next/link'

type Session = { id: string; title: string; updated_at?: string; created_at?: string; pinned?: boolean }

export function ChatSidebar({
  sessions,
  activeId,
  mode = 'professional',
  onSelect,
  onNew,
  onRename,
  onDelete,
  onTogglePin,
  onModeChange,
  onLogout,
}: {
  sessions: Session[]
  activeId: string | null
  mode?: 'professional' | 'student' | 'citizen'
  onSelect: (id: string) => void
  onNew: () => void
  onRename: (id: string, title: string) => void
  onDelete: (id: string) => void
  onTogglePin: (id: string, pinned: boolean) => void
  onModeChange?: (mode: 'professional' | 'student' | 'citizen') => void
  onLogout: () => void
}) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [collapsed, setCollapsed] = useState(false)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [confirmLogout, setConfirmLogout] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)

  // Filter sessions by search query
  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessions
    const q = searchQuery.toLowerCase()
    return sessions.filter((s) => (s.title || '').toLowerCase().includes(q))
  }, [sessions, searchQuery])

  // Grouping by Date & Pinned
  const { pinned, today, yesterday, previous7Days, older } = useMemo(() => {
    const now = new Date()
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
    const yesterdayStart = todayStart - 86400000
    const weekStart = todayStart - 7 * 86400000

    const p: Session[] = []
    const tod: Session[] = []
    const yest: Session[] = []
    const prev7: Session[] = []
    const old: Session[] = []

    filteredSessions.forEach((s) => {
      if (s.pinned) {
        p.push(s)
        return
      }
      const time = new Date(s.updated_at || s.created_at || Date.now()).getTime()
      if (time >= todayStart) tod.push(s)
      else if (time >= yesterdayStart) yest.push(s)
      else if (time >= weekStart) prev7.push(s)
      else old.push(s)
    })

    return { pinned: p, today: tod, yesterday: yest, previous7Days: prev7, older: old }
  }, [filteredSessions])

  if (collapsed) {
    return (
      <div className="flex h-full w-14 flex-col items-center justify-between border-r border-white/[0.08] bg-[#0A0D14]/95 py-4 backdrop-blur-2xl transition-all z-20">
        <div className="flex flex-col items-center gap-3">
          <button
            onClick={() => setCollapsed(false)}
            className="flex h-9 w-9 items-center justify-center rounded-xl text-slate-400 hover:bg-white/[0.08] hover:text-white transition-all cursor-pointer"
            title="Expand Sidebar"
          >
            ☰
          </button>
          <button
            onClick={onNew}
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 transition-all cursor-pointer text-base font-bold border border-blue-500/30"
            title="New Chat"
          >
            +
          </button>
        </div>

        <div className="flex flex-col items-center gap-2">
          <button
            onClick={() => setSettingsOpen(true)}
            className="flex h-9 w-9 items-center justify-center rounded-xl text-slate-400 hover:bg-white/[0.08] hover:text-white transition-all cursor-pointer text-sm"
            title="Settings"
          >
            ⚙️
          </button>
          <button
            onClick={() => setConfirmLogout(true)}
            className="flex h-9 w-9 items-center justify-center rounded-xl text-slate-400 hover:bg-rose-500/20 hover:text-rose-400 transition-all cursor-pointer text-xs"
            title="Log Out"
          >
            ⎋
          </button>
        </div>
      </div>
    )
  }

  function renderRow(s: Session) {
    const isActive = s.id === activeId

    return (
      <div
        key={s.id}
        className={`group relative mb-1 flex items-center justify-between rounded-xl px-3 py-2 text-xs transition-all ${
          isActive
            ? 'bg-blue-600/20 text-blue-300 border border-blue-500/35 shadow-sm font-semibold'
            : 'text-slate-300 hover:bg-white/[0.05] hover:text-white border border-transparent'
        }`}
      >
        {editingId === s.id ? (
          <input
            autoFocus
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={() => {
              if (editValue.trim()) onRename(s.id, editValue.trim())
              setEditingId(null)
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                if (editValue.trim()) onRename(s.id, editValue.trim())
                setEditingId(null)
              } else if (e.key === 'Escape') {
                setEditingId(null)
              }
            }}
            className="w-full bg-transparent border-b border-blue-500 text-white outline-none text-xs py-0.5 font-normal"
          />
        ) : (
          <div
            onClick={() => onSelect(s.id)}
            className="flex flex-1 items-center gap-2 overflow-hidden cursor-pointer mr-1"
          >
            <span className={`text-[12px] ${isActive ? 'text-blue-400' : 'text-slate-400'}`}>
              💬
            </span>
            <span className="truncate tracking-tight">{s.title || 'Legal Research'}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={() => onTogglePin(s.id, !s.pinned)}
            className={`p-1 text-[11px] hover:text-amber-400 transition-colors cursor-pointer ${
              s.pinned ? 'opacity-100 text-amber-400' : 'text-slate-400'
            }`}
            title={s.pinned ? 'Unpin' : 'Pin'}
          >
            📌
          </button>
          <button
            onClick={() => {
              setEditingId(s.id)
              setEditValue(s.title || '')
            }}
            className="p-1 text-[11px] text-slate-400 hover:text-white transition-colors cursor-pointer"
            title="Rename"
          >
            ✏️
          </button>
          <button
            onClick={() => setConfirmDeleteId(s.id)}
            className="p-1 text-[11px] text-slate-400 hover:text-rose-400 transition-colors cursor-pointer"
            title="Delete"
          >
            🗑
          </button>
        </div>
      </div>
    )
  }

  function renderGroup(title: string, items: Session[]) {
    if (items.length === 0) return null
    return (
      <div className="mb-4">
        <div className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
          {title} ({items.length})
        </div>
        {items.map((s) => renderRow(s))}
      </div>
    )
  }

  return (
    <>
      <aside className="relative flex h-full w-64 md:w-72 flex-col justify-between border-r border-white/[0.08] bg-[#0A0D14]/95 p-3.5 backdrop-blur-2xl transition-all z-20">
        {/* Top Header & Actions */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-xl bg-gradient-to-tr from-[#B8925A]/30 to-blue-500/20 text-xs border border-[#B8925A]/30 font-bold">
                ⚖️
              </span>
              <span className="text-xs font-bold tracking-tight text-white">NYAYA PRAMAAN</span>
            </div>
            <button
              onClick={() => setCollapsed(true)}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-slate-400 hover:bg-white/[0.08] hover:text-white transition-colors cursor-pointer"
              title="Collapse"
            >
              ◀
            </button>
          </div>

          {/* New Chat Button */}
          <button
            onClick={onNew}
            className="flex items-center justify-between rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-3.5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-blue-600/20 hover:brightness-110 active:scale-[0.98] transition-all cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <span className="text-base font-bold">+</span>
              <span>New Legal Chat</span>
            </div>
            <span className="text-[10px] bg-white/20 rounded px-1.5 py-0.5">Ctrl+K</span>
          </button>

          {/* Search Chats Input */}
          <div className="relative">
            <input
              type="text"
              placeholder="Search legal chats..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-xl border border-white/[0.08] bg-white/[0.03] px-3 py-2 pl-8 text-xs text-white placeholder-slate-400 outline-none focus:border-blue-500/50 transition-all"
            />
            <span className="absolute left-2.5 top-2.5 text-xs text-slate-400">🔍</span>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-2.5 text-xs text-slate-400 hover:text-white cursor-pointer"
              >
                ✕
              </button>
            )}
          </div>

          {/* Role Mode Selector */}
          {onModeChange && (
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-1.5">
              <div className="mb-1 px-1.5 text-[9px] font-semibold uppercase tracking-wider text-slate-400">
                Persona Mode
              </div>
              <div className="grid grid-cols-3 gap-1 text-[10px]">
                <button
                  type="button"
                  onClick={() => onModeChange('professional')}
                  className={`rounded-lg py-1 font-semibold transition-all cursor-pointer text-center ${
                    mode === 'professional'
                      ? 'bg-blue-600 text-white shadow-xs'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Lawyer
                </button>
                <button
                  type="button"
                  onClick={() => onModeChange('student')}
                  className={`rounded-lg py-1 font-semibold transition-all cursor-pointer text-center ${
                    mode === 'student'
                      ? 'bg-indigo-600 text-white shadow-xs'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Student
                </button>
                <button
                  type="button"
                  onClick={() => onModeChange('citizen')}
                  className={`rounded-lg py-1 font-semibold transition-all cursor-pointer text-center ${
                    mode === 'citizen'
                      ? 'bg-emerald-600 text-white shadow-xs'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Citizen
                </button>
              </div>
            </div>
          )}

          {/* Case Workspace Quick Link */}
          <Link
            href="/app/dashboard"
            className="flex items-center justify-between rounded-xl border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-xs text-slate-300 hover:border-[#B8925A]/40 hover:bg-white/[0.06] hover:text-white transition-all"
          >
            <div className="flex items-center gap-2">
              <span>💼</span>
              <span className="font-medium">Case Workspace</span>
            </div>
            <span className="text-[10px] text-[#B8925A]">Explore →</span>
          </Link>
        </div>

        {/* Chat History List */}
        <div className="my-3 flex-1 overflow-y-auto pr-1">
          {filteredSessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center text-slate-400">
              <span className="text-xl mb-1">📭</span>
              <p className="text-xs">No conversations found</p>
            </div>
          ) : (
            <>
              {renderGroup('📌 Pinned', pinned)}
              {renderGroup('Today', today)}
              {renderGroup('Yesterday', yesterday)}
              {renderGroup('Previous 7 Days', previous7Days)}
              {renderGroup('Older', older)}
            </>
          )}
        </div>

        {/* Footer actions */}
        <div className="border-t border-white/[0.08] pt-3 flex items-center justify-between">
          <button
            onClick={() => setSettingsOpen(true)}
            className="flex items-center gap-2 rounded-xl px-2.5 py-1.5 text-xs text-slate-300 hover:bg-white/[0.06] hover:text-white transition-colors cursor-pointer"
          >
            <span>⚙️</span>
            <span>Settings</span>
          </button>

          <button
            onClick={() => setConfirmLogout(true)}
            className="flex items-center gap-1.5 rounded-xl px-2.5 py-1.5 text-xs text-slate-400 hover:bg-rose-500/15 hover:text-rose-400 transition-colors cursor-pointer"
          >
            <span>⎋</span>
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={!!confirmDeleteId}
        title="Delete Legal Chat"
        message="Are you sure you want to delete this research session? Associated citations and query history will be removed."
        onConfirm={() => {
          if (confirmDeleteId) onDelete(confirmDeleteId)
          setConfirmDeleteId(null)
        }}
        onCancel={() => setConfirmDeleteId(null)}
      />

      {/* Logout Confirmation */}
      <ConfirmDialog
        open={confirmLogout}
        title="Sign Out"
        message="Are you sure you want to sign out of NyayaPramaan?"
        onConfirm={() => {
          setConfirmLogout(false)
          onLogout()
        }}
        onCancel={() => setConfirmLogout(false)}
      />

      {/* Settings Modal */}
      <ChatSettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
    </>
  )
}