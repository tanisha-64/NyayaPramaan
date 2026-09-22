import { TopNav } from "@/components/layout/TopNav";
import { Footer } from "@/components/layout/Footer";
import { Hero } from "@/components/marketing/Hero";
import { TrustStatement } from "@/components/marketing/TrustStatement";
import { ProblemSection } from "@/components/marketing/ProblemSection";
import { TrustAgentTeaser } from "@/components/marketing/TrustAgentTeaser";
import { CTASection } from "@/components/marketing/CTASection";

export default function LandingPage() {
  return (
    <>
      <TopNav />
      <main>
        <Hero />
        <TrustStatement />
        <ProblemSection />
        <TrustAgentTeaser />
        <CTASection />
      </main>
      <Footer />
    </>
  );
}