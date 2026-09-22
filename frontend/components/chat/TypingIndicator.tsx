export function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-white/[0.08] bg-[#141722]/80 px-4 py-3 shadow-lg backdrop-blur-md w-fit">
      <span className="flex h-4 w-4 items-center justify-center rounded-full bg-blue-500/20 text-[10px] text-blue-400">
        ⚖️
      </span>
      <span className="text-xs text-slate-400 mr-1 font-medium">Analyzing statutes & evidence</span>
      <div className="flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-blue-400"
            style={{
              animation: `bounce 1.2s infinite ${i * 0.2}s`,
            }}
          />
        ))}
      </div>
      <style>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.3; }
          30% { transform: translateY(-4px); opacity: 1; }
        }
      `}</style>
    </div>
  )
}