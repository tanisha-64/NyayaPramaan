import { Button } from "@/components/ui/Button";

export function CTASection() {
  return (
    <section className="mx-auto max-w-[1440px] px-6 py-28 text-center">
      <h2 className="font-[var(--font-serif)] text-3xl text-[var(--color-ivory)] md:text-5xl">
        Research with evidence, not guesses.
      </h2>
      <div className="mt-8 flex justify-center gap-4">
        <Button href="/public/chat" variant="primary">Start Legal Research</Button>
        <Button href="/register" variant="secondary">Create an Account</Button>
      </div>
    </section>
  );
}