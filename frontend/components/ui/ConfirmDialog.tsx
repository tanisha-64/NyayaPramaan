
export function ConfirmDialog({ open, title, message, onConfirm, onCancel }: {

  open: boolean; title: string; message: string; onConfirm: () => void; onCancel: () => void

}) {

  if (!open) return null

  return (

    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>

      <div style={{ background: '#1C1C1E', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 12, padding: 24, maxWidth: 360, width: '90%' }}>

        <h3 style={{ margin: 0, fontSize: 16 }}>{title}</h3>

        <p style={{ marginTop: 10, fontSize: 13, color: 'rgba(247,245,240,0.6)' }}>{message}</p>

        <div style={{ marginTop: 20, display: 'flex', gap: 10, justifyContent: 'flex-end' }}>

          <button onClick={onCancel} style={{ padding: '8px 16px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.2)', background: 'transparent', color: '#F7F5F0', cursor: 'pointer', fontSize: 13 }}>Cancel</button>

          <button onClick={onConfirm} style={{ padding: '8px 16px', borderRadius: 6, border: 'none', background: '#B8862E', color: '#0A0A0B', cursor: 'pointer', fontSize: 13, fontWeight: 500 }}>Delete</button>

        </div>

      </div>

    </div>

  )

}

