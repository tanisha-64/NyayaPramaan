const stats = [
  { value: "5.6 Cr+", label: "cases pending across Indian courts" },
  { value: "17–33%", label: "hallucination rate even in leading commercial legal-AI tools" },
  { value: "0.08%", label: "of national budget allocated to the judiciary" },
];

export function ProblemSection() {
  return (
    <section className="mx-auto max-w-[1440px] px-6 py-24">
      <h2 className="font-[var(--font-serif)] text-3xl text-[var(--color-ivory)] md:text-4xl max-w-2xl">
        Ordinary AI is not enough for legal research.
      </h2>
      <p className="mt-4 max-w-2xl text-white/60">
        Retrieval-augmented generation reduces hallucination — it does not
        eliminate it. Independent evaluation of leading legal-AI tools found
        real, documented failure rates.
      </p>
      <div className="mt-14 grid gap-10 md:grid-cols-3">
        {stats.map((s) => (
          <div key={s.label} className="border-t border-white/15 pt-6">
            <p className="font-[var(--font-serif)] text-4xl text-[var(--color-gold)]">{s.value}</p>
            <p className="mt-3 text-sm text-white/50">{s.label}</p>
          </div>
        ))}
      </div>
    </section>
  );
}