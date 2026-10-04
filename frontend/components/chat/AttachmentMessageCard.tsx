'use client'

function getFileIcon(fileName: string): string {
  const ext = fileName.split('.').pop()?.toLowerCase() || ''
  if (ext === 'pdf') return '📄'
  if (['docx', 'doc'].includes(ext)) return '📝'
  if (['jpg', 'jpeg', 'png', 'webp', 'tiff', 'bmp'].includes(ext)) return '🖼️'
  if (ext === 'txt') return '📃'
  return '📁'
}

export function AttachmentMessageCard({
  fileName,
  pageCount,
}: {
  fileName: string
  pageCount?: number
}) {
  return (
    <div className="inline-flex items-center gap-2.5 rounded-xl border border-indigo-400/25 bg-indigo-950/40 px-3.5 py-2 text-xs text-indigo-200 shadow-sm backdrop-blur-sm">
      <div className="flex h-6 w-6 items-center justify-center rounded-md bg-indigo-500/20 text-sm">
        {getFileIcon(fileName)}
      </div>
      <div className="flex flex-col">
        <span className="font-semibold text-white tracking-tight">{fileName}</span>
        <span className="text-[10px] text-indigo-300/80">
          {pageCount ? `${pageCount} pages attached` : 'Attached Legal Case File'}
        </span>
      </div>
    </div>
  )
}
