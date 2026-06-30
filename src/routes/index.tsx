import { createFileRoute } from "@tanstack/react-router";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { Hero } from "@/components/landing/hero";
import { FeatureCards } from "@/components/landing/feature-cards";
import { Workflow } from "@/components/landing/workflow";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "SHL Assessment AI — Find the right assessment, by conversation" },
      { name: "description", content: "Describe the role. Get a curated shortlist of validated SHL assessments." },
      { property: "og:title", content: "SHL Assessment AI" },
      { property: "og:description", content: "Conversational discovery of the right SHL assessment for every hiring decision." },
    ],
  }),
  component: LandingPage,
});

function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar variant="landing" />
      <main>
        <Hero />
        <FeatureCards />
        <Workflow />
      </main>
      <Footer />
    </div>
  );
}
