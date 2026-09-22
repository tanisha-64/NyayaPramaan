export function ConfirmDialog({
  open,
  title,
  message,
  onConfirm,
  onCancel,
}: {
  open: boolean
  title: string
  message: string
  onConfirm: () => void
  onCancel: () => void
}) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-sm rounded-xl border border-white/[0.12] bg-[#141722] p-5 shadow-2xl backdrop-blur-md animate-in fade-in zoom-in duration-150">
        <div className="flex items-center gap-2 text-slate-100">
          <span className="text-sm">⚠️</span>
          <h3 className="text-sm font-semibold tracking-tight">{title}</h3>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-slate-400">{message}</p>
        <div className="mt-5 flex items-center justify-end gap-2.5">
          <button
            onClick={onCancel}
            className="rounded-lg border border-white/10 bg-white/[0.04] px-3.5 py-1.5 text-xs text-slate-300 hover:bg-white/[0.08] hover:text-white transition-all cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="rounded-lg bg-red-600/80 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-red-500 transition-all cursor-pointer shadow-sm"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  )
}