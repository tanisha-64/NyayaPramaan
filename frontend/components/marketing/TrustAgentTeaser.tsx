import { Badge } from "@/components/ui/Badge";
import Link from "next/link";

const steps = [
  "Draft generated",
  "Claim / citation extracted",
  "Evidence re-retrieved",
  "Claim verified against source",
  "Correction applied if required",
  "Verified final answer",
];

export function TrustAgentTeaser() {
  return (
    <section className="mx-auto max-w-[1440px] px-6 py-24">
      <div className="grid gap-14 md:grid-cols-2 md:items-center">
        <div>
          <p className="mb-3 text-xs uppercase tracking-[0.2em] text-[var(--color-trust-blue)]">
            TrustAgent
          </p>
          <h2 className="font-[var(--font-serif)] text-3xl text-[var(--color-ivory)] md:text-4xl">
            Every answer walks a visible path to its evidence.
          </h2>
          <p className="mt-4 text-white/60">
            NyayaPramaan never presents an unverified claim as verified. Each
            factual statement is traceable back to its source document.
          </p>
          <div className="mt-6">
            <Badge status="verified" />
          </div>
          <Link href="/trust-verification" className="mt-6 inline-block text-sm text-[var(--color-trust-blue)] hover:underline">
            See how verification works →
          </Link>
        </div>

        <ol className="space-y-3">
          {steps.map((step, i) => (
            <li
              key={step}
              className="flex items-center gap-4 rounded-md border border-white/10 bg-white/[0.02] px-4 py-3"
            >
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-white/20 text-xs text-white/60">
                {i + 1}
              </span>
              <span className="text-sm text-white/70">{step}</span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}