import { motion } from "framer-motion";
import { MessagesSquare, Sparkles, GitCompareArrows, ShieldCheck } from "lucide-react";

const items = [
  {
    icon: MessagesSquare,
    title: "Conversation AI",
    body: "A natural back-and-forth replaces filter panels. The assistant asks only what it needs.",
  },
  {
    icon: Sparkles,
    title: "Smart recommendations",
    body: "Curated shortlists from the SHL catalog, ranked against role, level, and constraints.",
  },
  {
    icon: GitCompareArrows,
    title: "Comparison engine",
    body: "Pin two or more assessments and inspect duration, languages, adaptiveness side-by-side.",
  },
  {
    icon: ShieldCheck,
    title: "Enterprise ready",
    body: "SSO, audit logs, role-based access and regional data residency. Built for hiring teams.",
  },
];

export function FeatureCards() {
  return (
    <section id="features" className="mx-auto max-w-7xl px-4 sm:px-6 py-24">
      <div className="max-w-2xl">
        <div className="text-xs uppercase tracking-widest text-muted-foreground">Capabilities</div>
        <h2 className="mt-3 text-3xl sm:text-4xl font-semibold tracking-tight">
          A single surface for assessment discovery.
        </h2>
        <p className="mt-3 text-muted-foreground">
          Built around the way recruiters actually work — fewer dropdowns, more decisions.
        </p>
      </div>

      <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((item, i) => (
          <motion.div
            key={item.title}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.45, delay: i * 0.06 }}
            className="group relative rounded-2xl border border-border bg-card/60 p-5 hover:bg-card transition"
          >
            <div className="h-9 w-9 rounded-lg bg-background flex items-center justify-center border border-border/80">
              <item.icon className="h-4 w-4" />
            </div>
            <div className="mt-5 font-medium">{item.title}</div>
            <p className="mt-1.5 text-sm text-muted-foreground leading-relaxed">{item.body}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
