export function AttachmentCard({
  fileName,
  pages,
  uploading,
}: {
  fileName: string
  pages?: number
  uploading?: boolean
}) {
  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 10,
        padding: '10px 14px',
        borderRadius: 10,
        background: 'rgba(255,255,255,0.05)',
        border: '1px solid rgba(255,255,255,0.15)',
        maxWidth: 280,
      }}
    >
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: 8,
          background: 'rgba(43,92,224,0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 16,
          flexShrink: 0,
        }}
      >
        📄
      </div>
      <div style={{ overflow: 'hidden' }}>
        <p
          style={{
            fontSize: 13,
            fontWeight: 500,
            margin: 0,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {fileName}
        </p>
        <p style={{ fontSize: 11, color: 'rgba(247,245,240,0.5)', margin: '2px 0 0' }}>
          {uploading ? 'Uploading & indexing...' : `${pages} pages indexed`}
        </p>
      </div>
    </div>
  )
}