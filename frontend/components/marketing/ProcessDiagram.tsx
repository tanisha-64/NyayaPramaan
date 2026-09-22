const steps = [
  { title: "User Query", desc: "You ask a legal question in plain language." },
  { title: "AI Draft", desc: "The model generates a first-pass answer using retrieved context." },
  { title: "Claim / Citation Extraction", desc: "The draft is broken into individually verifiable factual claims." },
  { title: "Evidence Re-Retrieval", desc: "Each claim is checked against the original source documents again." },
  { title: "Verification", desc: "Every claim is marked supported, contradicted, or insufficient evidence." },
  { title: "Confidence Assessment", desc: "A confidence level is attached to each verified claim." },
  { title: "Correction if Required", desc: "Unsupported claims are rewritten or flagged for manual review." },
  { title: "Verified Final Answer", desc: "You receive an answer with source, evidence, and audit information." },
];

export function ProcessDiagram() {
  return (
    <div className="mx-auto max-w-3xl">
      {steps.map((s, i) => (
        <div key={s.title} className="flex gap-6">
          <div className="flex flex-col items-center">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-[var(--color-trust-blue)]/40 text-sm text-[var(--color-trust-blue)]">
              {i + 1}
            </span>
            {i < steps.length - 1 && (
              <span className="mt-1 h-full w-px flex-1 bg-white/10" />
            )}
          </div>
          <div className="pb-10">
            <p className="text-base font-medium text-[var(--color-ivory)]">{s.title}</p>
            <p className="mt-1 text-sm text-white/50">{s.desc}</p>
          </div>
        </div>
      ))}
    </div>
  );
}