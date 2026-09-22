const rows = [
  { label: "Retrieves source documents", ordinary: true, nyaya: true },
  { label: "Re-checks every citation after drafting", ordinary: false, nyaya: true },
  { label: "Flags unverified claims instead of hiding them", ordinary: false, nyaya: true },
  { label: "Shows jurisdiction status (binding/persuasive)", ordinary: false, nyaya: true },
  { label: "Tamper-evident audit log of verification events", ordinary: false, nyaya: true },
];

function Mark({ ok }: { ok: boolean }) {
  return (
    <span className={ok ? "text-[var(--color-verified-green)]" : "text-white/30"}>
      {ok ? "✓" : "—"}
    </span>
  );
}

export function ComparisonBlock() {
  return (
    <div className="mx-auto max-w-3xl overflow-hidden rounded-lg border border-white/10">
      <div className="grid grid-cols-[1fr_auto_auto] gap-4 border-b border-white/10 bg-white/[0.03] px-6 py-4 text-xs uppercase tracking-wide text-white/40">
        <span>Capability</span>
        <span className="text-center">Ordinary RAG Chatbot</span>
        <span className="text-center">NyayaPramaan</span>
      </div>
      {rows.map((r) => (
        <div
          key={r.label}
          className="grid grid-cols-[1fr_auto_auto] items-center gap-4 border-b border-white/5 px-6 py-4 last:border-0"
        >
          <span className="text-sm text-white/70">{r.label}</span>
          <span className="text-center w-24"><Mark ok={r.ordinary} /></span>
          <span className="text-center w-24"><Mark ok={r.nyaya} /></span>
        </div>
      ))}
    </div>
  );
}