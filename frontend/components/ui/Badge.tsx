type BadgeStatus = "verified" | "unverified" | "binding" | "persuasive" | "target";

const statusStyles: Record<BadgeStatus, string> = {
  verified: "bg-[var(--color-verified-green)]/15 text-[var(--color-verified-green)] border-[var(--color-verified-green)]/30",
  unverified: "bg-[var(--color-review-amber)]/15 text-[var(--color-review-amber)] border-[var(--color-review-amber)]/30",
  binding: "bg-[var(--color-trust-blue)]/15 text-[var(--color-trust-blue)] border-[var(--color-trust-blue)]/30",
  persuasive: "bg-white/10 text-white/70 border-white/20",
  target: "bg-white/5 text-white/50 border-white/15",
};

const statusLabel: Record<BadgeStatus, string> = {
  verified: "Verified Against Source",
  unverified: "Verification Required",
  binding: "Binding in this Jurisdiction",
  persuasive: "Persuasive Only",
  target: "Target (Projected)",
};

export function Badge({ status, label }: { status: BadgeStatus; label?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${statusStyles[status]}`}
    >
      {label ?? statusLabel[status]}
    </span>
  );
}