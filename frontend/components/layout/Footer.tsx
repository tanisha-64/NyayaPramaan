import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-white/10 px-6 py-12">
      <div className="mx-auto max-w-[1440px] grid gap-8 md:grid-cols-4">
        <div>
          <p className="font-[var(--font-serif)] text-lg">NyayaPramaan</p>
          <p className="mt-2 text-sm text-white/50">Legal AI, verified by evidence.</p>
        </div>
        <div className="flex flex-col gap-2 text-sm text-white/60">
          <Link href="/how-it-works">How It Works</Link>
          <Link href="/trust-verification">Trust & Verification</Link>
          <Link href="/research">Research</Link>
        </div>
        <div className="flex flex-col gap-2 text-sm text-white/60">
          <Link href="/about">About</Link>
          <Link href="/disclaimer">Legal Disclaimer</Link>
        </div>
        <div className="text-xs text-white/40 leading-relaxed">
          This platform provides AI-assisted legal information and research
          support. It does not constitute legal advice.
        </div>
      </div>
    </footer>
  );
}