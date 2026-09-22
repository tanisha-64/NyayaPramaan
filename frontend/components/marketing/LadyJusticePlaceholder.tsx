/**
 * Clean placeholder for the signature Lady Justice visual.
 * Structured so a real GLB/GLTF model can be dropped into a React Three
 * Fiber <Canvas> here later without restructuring this section.
 */
export function LadyJusticePlaceholder() {
  return (
    <div className="relative flex h-[420px] w-full items-center justify-center rounded-lg border border-white/10 bg-gradient-to-b from-[var(--color-navy)] to-[var(--color-obsidian)] md:h-[520px]">
      <svg
        width="140"
        height="220"
        viewBox="0 0 140 220"
        fill="none"
        className="opacity-80"
        aria-hidden="true"
      >
        <line x1="70" y1="10" x2="70" y2="60" stroke="#B8925A" strokeWidth="2" />
        <line x1="20" y1="30" x2="120" y2="30" stroke="#B8925A" strokeWidth="2" />
        <path d="M20 30 L10 70 L30 70 Z" stroke="#B8925A" strokeWidth="1.5" fill="none" />
        <path d="M120 30 L110 70 L130 70 Z" stroke="#B8925A" strokeWidth="1.5" fill="none" />
        <rect x="55" y="60" width="30" height="120" rx="6" stroke="#F7F5F0" strokeWidth="1.5" fill="none" opacity="0.6" />
        <line x1="70" y1="180" x2="70" y2="210" stroke="#F7F5F0" strokeWidth="2" opacity="0.6" />
      </svg>
      <span className="absolute bottom-4 text-xs uppercase tracking-widest text-white/30">
        Evidence · Balance · Trust
      </span>
    </div>
  );
}