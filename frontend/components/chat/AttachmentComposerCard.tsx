'use client'

export type ComposerDoc = {
  caseId: string
  fileName: string
  fileSize?: number
  fileType?: string
  status: 'uploading' | 'processing' | 'ocr' | 'indexing' | 'ready' | 'rejected' | 'failed'
  progress?: number
  pagesProcessed?: number
  totalPages?: number
  rejectionReason?: string
  errorMessage?: string
}

function formatBytes(bytes?: number): string {
  if (!bytes || bytes <= 0) return 'Document'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

function getFileIcon(fileName: string): string {
  const ext = fileName.split('.').pop()?.toLowerCase() || ''
  if (ext === 'pdf') return '📄'
  if (['docx', 'doc'].includes(ext)) return '📝'
  if (['jpg', 'jpeg', 'png', 'webp', 'tiff', 'bmp'].includes(ext)) return '🖼️'
  if (ext === 'txt') return '📃'
  return '📁'
}

export function AttachmentComposerCard({
  doc,
  onRemove,
  onRetry,
}: {
  doc: ComposerDoc
  onRemove: () => void
  onRetry?: () => void
}) {
  const isReady = doc.status === 'ready'
  const isRejected = doc.status === 'rejected'
  const isFailed = doc.status === 'failed'
  const isUploading = doc.status === 'uploading' || doc.status === 'processing' || doc.status === 'ocr' || doc.status === 'indexing'

  return (
    <div
      className={`group relative flex items-center justify-between gap-3 rounded-xl border p-2.5 transition-all shadow-sm ${
        isRejected
          ? 'border-rose-500/40 bg-rose-950/30 text-rose-200'
          : isFailed
          ? 'border-amber-500/40 bg-amber-950/30 text-amber-200'
          : isReady
          ? 'border-emerald-500/30 bg-emerald-950/20 text-emerald-200'
          : 'border-[#B8925A]/30 bg-[#121622] text-slate-200'
      }`}
    >
      <div className="flex items-center gap-2.5 overflow-hidden">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/[0.06] text-base border border-white/10">
          {getFileIcon(doc.fileName)}
        </div>

        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="truncate text-xs font-semibold tracking-tight text-white max-w-[200px] sm:max-w-[280px]">
              {doc.fileName}
            </span>
            {doc.fileSize ? (
              <span className="text-[10px] text-slate-400 shrink-0 font-medium">
                ({formatBytes(doc.fileSize)})
              </span>
            ) : null}
          </div>

          <div className="mt-0.5 flex items-center gap-2 text-[10px]">
            {isReady ? (
              <span className="flex items-center gap-1 font-medium text-emerald-400">
                <span>✓</span>
                <span>Ready for legal query</span>
                {doc.totalPages ? ` (${doc.totalPages} pages indexed)` : ''}
              </span>
            ) : isRejected ? (
              <span className="flex items-center gap-1 text-rose-300 font-medium truncate max-w-[260px]">
                <span>✕</span>
                <span>{doc.rejectionReason || 'Rejected: Non-legal file'}</span>
              </span>
            ) : isFailed ? (
              <span className="flex items-center gap-1 text-amber-300 font-medium">
                <span>⚠️</span>
                <span>{doc.errorMessage || 'Processing failed'}</span>
              </span>
            ) : (
              <span className="flex items-center gap-1 text-blue-400 font-medium">
                <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse-dot" />
                <span>
                  {doc.status === 'ocr'
                    ? 'OCR Text Extraction...'
                    : doc.status === 'indexing'
                    ? `Indexing Chunks (${doc.pagesProcessed || 1}/${doc.totalPages || 1})...`
                    : doc.progress
                    ? `Uploading... ${doc.progress}%`
                    : 'Processing Legal Document...'}
                </span>
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-1.5 shrink-0 ml-2">
        {(isRejected || isFailed) && onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="rounded-lg bg-white/10 px-2 py-1 text-[10px] font-semibold text-slate-200 hover:bg-white/20 transition-all cursor-pointer"
          >
            Retry
          </button>
        ) : null}

        <button
          type="button"
          onClick={onRemove}
          className="flex h-6 w-6 items-center justify-center rounded-lg text-slate-400 hover:bg-white/10 hover:text-white transition-all cursor-pointer"
          title="Remove attachment"
        >
          ✕
        </button>
      </div>
    </div>
  )
}
