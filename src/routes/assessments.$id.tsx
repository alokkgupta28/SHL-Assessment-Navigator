import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { ArrowLeft, Clock, ExternalLink, GitCompareArrows, Languages, Wifi, Zap, Bookmark } from "lucide-react";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getAssessment, listAssessments } from "@/services/assessments";
import { AssessmentCard } from "@/components/assessments/assessment-card";
import { useLocalSet } from "@/hooks/use-local-set";
import { toast } from "sonner";

export const Route = createFileRoute("/assessments/$id")({
  head: () => ({
    meta: [
      { title: "Assessment — SHL Assessment AI" },
      { name: "description", content: "SHL assessment details." },
    ],
  }),
  loader: async ({ params }) => {
    const [catalog, assessment] = await Promise.all([listAssessments(), getAssessment(params.id)]);
    const a = assessment ?? catalog.find((item) => item.id === params.id);
    if (!a) throw notFound();
    return {
      assessment: a,
      related: catalog.filter((item) => item.id !== a.id && item.category === a.category).slice(0, 3),
    };
  },
  notFoundComponent: () => (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="text-5xl font-semibold">404</div>
        <p className="mt-2 text-muted-foreground">Assessment not found.</p>
        <Button asChild className="mt-6 rounded-full"><Link to="/chat">Back to chat</Link></Button>
      </div>
    </div>
  ),
  component: AssessmentDetail,
});

function AssessmentDetail() {
  const { assessment: a, related } = Route.useLoaderData();
  const compare = useLocalSet("shl-compare");
  const saved = useLocalSet("shl-saved");

  return (
    <div className="min-h-screen bg-background">
      <Navbar variant="landing" />
      <main className="mx-auto max-w-5xl px-4 sm:px-6 py-12">
        <Link to="/chat" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground transition">
          <ArrowLeft className="h-3.5 w-3.5 mr-1" /> Back to chat
        </Link>

        <header className="mt-6">
          <div className="text-xs uppercase tracking-widest text-muted-foreground">{a.category}</div>
          <h1 className="mt-2 text-3xl sm:text-5xl font-semibold tracking-tight">{a.name}</h1>
          <p className="mt-4 text-muted-foreground max-w-2xl leading-relaxed">{a.description}</p>

          <div className="mt-6 flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant={compare.has(a.id) ? "default" : "outline"}
              className="rounded-full"
              onClick={() => compare.toggle(a.id)}
            >
              <GitCompareArrows className="h-3.5 w-3.5 mr-1" />
              {compare.has(a.id) ? "In compare" : "Add to compare"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="rounded-full"
              onClick={() => {
                saved.toggle(a.id);
                toast(saved.has(a.id) ? "Removed from saved" : "Saved");
              }}
            >
              <Bookmark className="h-3.5 w-3.5 mr-1" />
              {saved.has(a.id) ? "Saved" : "Save"}
            </Button>
            <Button asChild size="sm" variant="ghost" className="rounded-full">
              <a href={a.officialUrl} target="_blank" rel="noreferrer">
                Official catalog <ExternalLink className="h-3.5 w-3.5 ml-1" />
              </a>
            </Button>
          </div>
        </header>

        <section className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Meta icon={<Clock className="h-3.5 w-3.5" />} label="Duration" value={`${a.durationMinutes} minutes`} />
          <Meta icon={<Zap className="h-3.5 w-3.5" />} label="Adaptive" value={a.adaptive ? "Yes" : "No"} />
          <Meta icon={<Wifi className="h-3.5 w-3.5" />} label="Remote" value={a.remote ? "Yes" : "No"} />
          <Meta icon={<Languages className="h-3.5 w-3.5" />} label="Languages" value={a.languages.join(", ")} />
          <Meta label="Job levels" value={a.jobLevels.join(", ")} />
          <Meta label="Skills" value={a.skills.join(", ")} />
        </section>

        {related.length > 0 && (
          <section className="mt-16">
            <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-widest">Related assessments</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {related.map((r, i) => (
                <AssessmentCard
                  key={r.id}
                  assessment={r}
                  index={i}
                  compareActive={compare.has(r.id)}
                  savedActive={saved.has(r.id)}
                  onCompare={compare.toggle}
                  onSave={saved.toggle}
                />
              ))}
            </div>
          </section>
        )}
      </main>
      <Footer />
    </div>
  );
}

function Meta({ icon, label, value }: { icon?: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-card/60 p-4">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground uppercase tracking-wider">
        {icon}{label}
      </div>
      <div className="mt-1.5 text-sm">{value}</div>
    </div>
  );
}
