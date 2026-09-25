'use client'
import { useState } from 'react'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { ChatSettingsModal } from './ChatSettingsModal'

type Session = { id: string; title: string; updated_at: string; pinned: boolean }

export function ChatSidebar({
  sessions,
  activeId,
  onSelect,
  onNew,
  onRename,
  onDelete,
  onTogglePin,
  onLogout,
}: {
  sessions: Session[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onRename: (id: string, title: string) => void
  onDelete: (id: string) => void
  onTogglePin: (id: string, pinned: boolean) => void
  onLogout: () => void
}) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [collapsed, setCollapsed] = useState(false)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [confirmLogout, setConfirmLogout] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)


  if (collapsed) {
    return (
      <div className="flex h-full w-12 flex-col items-center justify-between border-r border-white/[0.08] bg-[#07080D]/90 py-4 backdrop-blur-xl transition-all">
        <button
          onClick={() => setCollapsed(false)}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-white/[0.08] hover:text-white transition-all cursor-pointer"
          title="Expand Sidebar"
        >
          ☰
        </button>
        <button
          onClick={onNew}
          className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 transition-all cursor-pointer text-sm font-bold"
          title="New Chat"
        >
          +
        </button>
        <button
          onClick={() => setConfirmLogout(true)}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-white/[0.08] hover:text-red-400 transition-all cursor-pointer text-xs"
          title="Log Out"
        >
          ⎋
        </button>
      </div>
    )
  }

  const pinned = sessions.filter((s) => s.pinned)
  const recent = sessions.filter((s) => !s.pinned)

  function renderRow(s: Session) {
    const isActive = s.id === activeId

    return (
      <div
        key={s.id}
        className={`group relative mb-1 flex items-center justify-between rounded-xl px-3 py-2 text-xs transition-all ${
          isActive
            ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 shadow-xs font-semibold'
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
            className="w-full bg-transparent border-b border-blue-500 text-white outline-none text-xs py-0.5"
          />
        ) : (
          <div
            onClick={() => onSelect(s.id)}
            className="flex flex-1 items-center gap-2 overflow-hidden cursor-pointer mr-1"
          >
            <span className={`text-[11px] ${isActive ? 'text-blue-400' : 'text-slate-400'}`}>
              💬
            </span>
            <span className="truncate tracking-tight">{s.title || 'Untitled Research'}</span>
          </div>
        )}

        {/* Action icons */}
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
              setEditValue(s.title)
            }}
            className="p-1 text-[11px] text-slate-400 hover:text-white transition-colors cursor-pointer"
            title="Rename"
          >
            ✎
          </button>
          <button
            onClick={() => setConfirmDeleteId(s.id)}
            className="p-1 text-[11px] text-slate-400 hover:text-red-400 transition-colors cursor-pointer"
            title="Delete"
          >
            🗑
          </button>
        </div>
      </div>
    )
  }

  return (
    <aside className="flex h-full w-64 min-w-[230px] max-w-[320px] flex-col justify-between border-r border-white/[0.08] bg-[#07080D]/95 p-3.5 backdrop-blur-2xl transition-all">
      {/* Top action bar */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500/20 to-blue-500/20 border border-white/10 text-xs">
              ⚖️
            </span>
            <span className="font-semibold text-xs tracking-wider uppercase text-slate-300">
              Workspace
            </span>
          </div>
          <button
            onClick={() => setCollapsed(true)}
            className="rounded-lg p-1 text-xs text-slate-400 hover:bg-white/[0.06] hover:text-white transition-all cursor-pointer"
            title="Collapse sidebar"
          >
            «
          </button>
        </div>

        <button
          onClick={onNew}
          className="group flex w-full items-center justify-between rounded-xl border border-white/[0.1] bg-white/[0.04] px-3 py-2.5 text-xs font-medium text-white hover:border-blue-500/40 hover:bg-blue-600/10 transition-all cursor-pointer shadow-xs"
        >
          <span className="flex items-center gap-2">
            <span className="text-blue-400 font-bold">+</span>
            <span>New Research Chat</span>
          </span>
          <span className="rounded-md bg-white/[0.06] px-1.5 py-0.5 text-[10px] text-slate-400 group-hover:text-blue-300">
            ⌘N
          </span>
        </button>
      </div>

      {/* Sessions list */}
      <div className="my-3 flex-1 overflow-y-auto pr-1">
        {pinned.length > 0 && (
          <div className="mb-4">
            <div className="mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-amber-400">
              Pinned Chats
            </div>
            {pinned.map(renderRow)}
          </div>
        )}

        <div>
          <div className="mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            Recent Chats
          </div>
          {recent.length === 0 && pinned.length === 0 ? (
            <div className="px-2 py-4 text-center text-xs text-slate-400">
              No conversations yet
            </div>
          ) : (
            recent.map(renderRow)
          )}
        </div>
      </div>

      {/* App Tools & Navigation Links */}
      <div className="border-t border-white/[0.08] pt-2 pb-1 flex flex-col gap-1">
        <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Tools & Apps
        </div>
        <a
          href="/app/dashboard"
          className="flex items-center gap-2 rounded-xl px-2.5 py-1.5 text-xs text-slate-300 hover:bg-white/[0.06] hover:text-white transition-all no-underline"
        >
          <span>📂</span>
          <span>Case Workspace</span>
        </a>
        <a
          href="/public/saved"
          className="flex items-center gap-2 rounded-xl px-2.5 py-1.5 text-xs text-slate-300 hover:bg-white/[0.06] hover:text-[#B8925A] transition-all no-underline"
        >
          <span>★</span>
          <span>Saved Answers</span>
        </a>
        <a
          href="/game"
          className="flex items-center gap-2 rounded-xl px-2.5 py-1.5 text-xs text-slate-300 hover:bg-white/[0.06] hover:text-amber-400 transition-all no-underline"
        >
          <span>🎮</span>
          <span>Rights Game</span>
        </a>
        <a
          href="/quiz"
          className="flex items-center gap-2 rounded-xl px-2.5 py-1.5 text-xs text-slate-300 hover:bg-white/[0.06] hover:text-blue-400 transition-all no-underline"
        >
          <span>📝</span>
          <span>Daily Quiz</span>
        </a>
        <a
          href="/news"
          className="flex items-center gap-2 rounded-xl px-2.5 py-1.5 text-xs text-slate-300 hover:bg-white/[0.06] hover:text-white transition-all no-underline"
        >
          <span>📰</span>
          <span>Legal News</span>
        </a>
      </div>

      {/* Bottom User Bar */}
      <div className="border-t border-white/[0.08] pt-2 flex flex-col gap-1">
        <button
          onClick={() => setSettingsOpen(true)}
          className="flex w-full items-center justify-between rounded-xl px-2.5 py-1.5 text-xs text-slate-300 hover:bg-white/[0.06] hover:text-white transition-all cursor-pointer"
        >
          <span className="flex items-center gap-2">
            <span className="text-[13px]">⚙️</span>
            <span>Settings & Library</span>
          </span>
          <span className="text-[9px] rounded bg-white/10 px-1.5 py-0.5 text-slate-400">Manage</span>
        </button>

        <button
          onClick={() => setConfirmLogout(true)}
          className="flex w-full items-center justify-between rounded-xl px-2.5 py-1.5 text-xs text-slate-400 hover:bg-white/[0.05] hover:text-red-400 transition-all cursor-pointer"
        >
          <span className="flex items-center gap-2">
            <span className="text-[13px]">⎋</span>
            <span>Sign Out</span>
          </span>
          <span className="text-[10px] text-slate-500">NyayaPramaan</span>
        </button>
      </div>


      <ConfirmDialog
        open={!!confirmDeleteId}
        title="Delete this chat?"
        message="Are you sure you want to delete this legal research thread? This cannot be undone."
        onConfirm={() => {
          if (confirmDeleteId) onDelete(confirmDeleteId)
          setConfirmDeleteId(null)
        }}
        onCancel={() => setConfirmDeleteId(null)}
      />

      <ConfirmDialog
        open={confirmLogout}
        title="Sign Out?"
        message="Are you sure you want to end your current session?"
        onConfirm={() => {
          setConfirmLogout(false)
          onLogout()
        }}
        onCancel={() => setConfirmLogout(false)}
      />

      <ChatSettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onChatsCleared={() => {
          onNew()
          window.location.reload()
        }}
      />
    </aside>
  )
}