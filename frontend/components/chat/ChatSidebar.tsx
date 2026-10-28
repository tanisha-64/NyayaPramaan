'use client'
import { useState } from 'react'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { exportSessionPdf } from '@/services/chatService'

type Session = { id: string; title: string; updated_at: string; pinned: boolean }

export function ChatSidebar({ sessions, activeId, onSelect, onNew, onRename, onDelete, onTogglePin, onLogout, isMobile = false, mobileOpen = false, onCloseMobile }: {
  sessions: Session[]; activeId: string | null
  onSelect: (id: string) => void; onNew: () => void
  onRename: (id: string, title: string) => void; onDelete: (id: string) => void
  onTogglePin: (id: string, pinned: boolean) => void; onLogout: () => void
  isMobile?: boolean; mobileOpen?: boolean; onCloseMobile?: () => void
}) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [collapsed, setCollapsed] = useState(false)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [confirmLogout, setConfirmLogout] = useState(false)
  const [exportingId, setExportingId] = useState<string | null>(null)

  async function handleExport(id: string) {
    setExportingId(id)
    try {
      const { blob, filename } = await exportSessionPdf(id)
      const file = new File([blob], filename || 'chat.pdf', { type: 'application/pdf' })
      const nav = navigator as Navigator & { canShare?: (data?: unknown) => boolean; share?: (data: unknown) => Promise<void> }
      if (nav.share && nav.canShare?.({ files: [file] })) {
        await nav.share({ files: [file], title: filename || 'NyayaPramaan Chat' })
      } else {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename || 'chat.pdf'
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(url)
      }
    } catch (err) {
      console.error(err)
      alert('Could not export this chat. Please try again.')
    }
    setExportingId(null)
  }

  function selectAndClose(id: string) {
    onSelect(id)
    if (isMobile) onCloseMobile?.()
  }

  function newAndClose() {
    onNew()
    if (isMobile) onCloseMobile?.()
  }

  if (!isMobile && collapsed) {
    return (
      <div style={{ width: 44, borderRight: '1px solid rgba(255,255,255,0.1)', padding: 12, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
        <button onClick={() => setCollapsed(false)} style={{ background: 'none', border: 'none', color: '#F7F5F0', cursor: 'pointer', fontSize: 16 }}>☰</button>
      </div>
    )
  }

  const pinned = sessions.filter((s) => s.pinned)
  const recent = sessions.filter((s) => !s.pinned)

  function renderRow(s: Session) {
    return (
      <div key={s.id} style={{ padding: '8px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 13, background: s.id === activeId ? 'rgba(255,255,255,0.08)' : 'transparent', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6 }}>
        {editingId === s.id ? (
          <input autoFocus value={editValue} onChange={(e) => setEditValue(e.target.value)}
            onBlur={() => { onRename(s.id, editValue); setEditingId(null) }}
            onKeyDown={(e) => { if (e.key === 'Enter') { onRename(s.id, editValue); setEditingId(null) } }}
            style={{ flex: 1, minWidth: 0, background: 'transparent', border: 'none', borderBottom: '1px solid #2B5CE0', color: '#F7F5F0', fontSize: 13 }} />
        ) : (
          <span onClick={() => selectAndClose(s.id)} style={{ flex: 1, minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.title}</span>
        )}
        <span onClick={() => onTogglePin(s.id, !s.pinned)} style={{ opacity: s.pinned ? 1 : 0.4, fontSize: 12, flexShrink: 0 }}>📌</span>
        <span onClick={() => !exportingId && handleExport(s.id)} title="Export / Share as PDF" style={{ opacity: exportingId === s.id ? 0.3 : 0.5, fontSize: 12, flexShrink: 0 }}>
          {exportingId === s.id ? '⏳' : '📤'}
        </span>
        <span onClick={() => { setEditingId(s.id); setEditValue(s.title) }} style={{ opacity: 0.5, fontSize: 12, flexShrink: 0 }}>✎</span>
        <span onClick={() => setConfirmDeleteId(s.id)} style={{ opacity: 0.5, fontSize: 12, flexShrink: 0 }}>🗑</span>
      </div>
    )
  }

  const panel = (
    <div style={{
      width: isMobile ? '80vw' : 240, minWidth: isMobile ? 220 : 180, maxWidth: isMobile ? 320 : 400,
      resize: isMobile ? 'none' : 'horizontal', height: '100%', overflow: 'hidden',
      borderRight: '1px solid rgba(255,255,255,0.1)', padding: 16, display: 'flex', flexDirection: 'column', gap: 8,
      ...(isMobile ? {
        position: 'fixed' as const, top: 0, left: 0, zIndex: 60, background: '#0A0A0B',
        transform: mobileOpen ? 'translateX(0)' : 'translateX(-100%)',
        transition: 'transform .25s ease', boxShadow: '4px 0 24px rgba(0,0,0,0.5)',
      } : {}),
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button onClick={newAndClose} style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.2)', background: 'transparent', color: '#F7F5F0', cursor: 'pointer', textAlign: 'left', fontSize: 13 }}>+ New Chat</button>
        {isMobile ? (
          <button onClick={onCloseMobile} style={{ marginLeft: 8, background: 'none', border: 'none', color: 'rgba(247,245,240,0.5)', cursor: 'pointer', fontSize: 16 }}>✕</button>
        ) : (
          <button onClick={() => setCollapsed(true)} style={{ marginLeft: 8, background: 'none', border: 'none', color: 'rgba(247,245,240,0.5)', cursor: 'pointer', fontSize: 14 }}>«</button>
        )}
      </div>

      <div style={{ marginTop: 8, overflowY: 'auto', flex: 1 }}>
        {pinned.length > 0 && (<>
          <p style={{ fontSize: 11, color: 'rgba(247,245,240,0.4)', margin: '8px 0 4px', textTransform: 'uppercase' }}>Pinned</p>
          {pinned.map(renderRow)}
        </>)}
        <p style={{ fontSize: 11, color: 'rgba(247,245,240,0.4)', margin: '12px 0 4px', textTransform: 'uppercase' }}>Recent</p>
        {recent.map(renderRow)}
      </div>

      <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 10 }}>
        <button onClick={() => setConfirmLogout(true)} style={{ width: '100%', textAlign: 'left', fontSize: 12, padding: '8px 6px', background: 'none', border: 'none', color: 'rgba(247,245,240,0.5)', cursor: 'pointer' }}>⎋ Log Out</button>
      </div>

      <ConfirmDialog open={!!confirmDeleteId} title="Delete this chat?" message="Are you sure you want to delete this chat? This cannot be undone."
        onConfirm={() => { if (confirmDeleteId) onDelete(confirmDeleteId); setConfirmDeleteId(null) }} onCancel={() => setConfirmDeleteId(null)} />
      <ConfirmDialog open={confirmLogout} title="Log out?" message="Are you sure you want to log out of NyayaPramaan?"
        onConfirm={() => { setConfirmLogout(false); onLogout() }} onCancel={() => setConfirmLogout(false)} />
    </div>
  )

  if (!isMobile) return panel

  return (
    <>
      {mobileOpen && (
        <div onClick={onCloseMobile} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 55 }} />
      )}
      {panel}
    </>
  )
}