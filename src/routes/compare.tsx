import { createFileRoute, Link } from "@tanstack/react-router";
import { zodValidator, fallback } from "@tanstack/zod-adapter";
import { z } from "zod";
import { motion } from "framer-motion";
import { ArrowLeft, Check, GitCompareArrows, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { getAssessment } from "@/services/assessments";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Assessment } from "@/types/assessment";

const search = z.object({
  ids: fallback(z.string(), "").default(""),
});

export const Route = createFileRoute("/compare")({
  validateSearch: zodValidator(search),
  head: () => ({
    meta: [
      { title: "Compare assessments — SHL Assessment AI" },
      { name: "description", content: "Side-by-side comparison of SHL assessments." },
    ],
  }),
  component: ComparePage,
});

interface Row {
  label: string;
  values: (a: Assessment) => unknown;
  render: (a: Assessment) => React.ReactNode;
}

function ComparePage() {
  const { ids } = Route.useSearch() as { ids: string };
  const navigate = Route.useNavigate();
  const [list, setList] = useState<Assessment[]>([]);

  useEffect(() => {
    let cancelled = false;
    const resolvedIds = ids
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    Promise.all(resolvedIds.map(async (id) => getAssessment(id))).then((items) => {
      if (cancelled) return;
      setList(items.filter((a): a is Assessment => Boolean(a)));
    });

    return () => {
      cancelled = true;
    };
  }, [ids]);

  const remove = (id: string) => {
    const next = list.filter((a) => a.id !== id).map((a) => a.id).join(",");
    navigate({ search: { ids: next } });
  };
  const clearAll = () => navigate({ search: { ids: "" } });

  if (list.length === 0) {
    return (
      <div className="min-h-dvh bg-background flex flex-col">
        <Navbar variant="landing" />
        <main className="flex-1 mx-auto max-w-3xl px-4 sm:px-6 py-24 text-center">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <div className="mx-auto h-12 w-12 rounded-2xl border border-border bg-card/60 flex items-center justify-center">
              <GitCompareArrows className="h-5 w-5 text-muted-foreground" />
            </div>
            <h1 className="mt-6 text-2xl font-semibold tracking-tight">Nothing to compare yet</h1>
            <p className="mt-2 text-muted-foreground max-w-md mx-auto">
              Open the chat, tap <span className="text-foreground">Compare</span> on at least two
              assessments, and we'll line them up here.
            </p>
            <Button asChild className="mt-7 rounded-full">
              <Link to="/chat">Open chat</Link>
            </Button>
          </motion.div>
        </main>
        <Footer />
      </div>
    );
  }

  const rows: Row[] = [
    { label: "Category", values: (a) => a.category, render: (a) => a.category },
    {
      label: "Duration",
      values: (a) => a.durationMinutes,
      render: (a) => <span className="tabular-nums">{a.durationMinutes} min</span>,
    },
    { label: "Adaptive", values: (a) => a.adaptive, render: (a) => <BoolCell on={a.adaptive} /> },
    { label: "Remote", values: (a) => a.remote, render: (a) => <BoolCell on={a.remote} /> },
    {
      label: "Job levels",
      values: (a) => a.jobLevels.slice().sort().join("|"),
      render: (a) => a.jobLevels.join(", "),
    },
    {
      label: "Languages",
      values: (a) => a.languages.length,
      render: (a) => <span>{a.languages.join(", ")}</span>,
    },
    {
      label: "Skills",
      values: (a) => a.skills.slice().sort().join("|"),
      render: (a) => a.skills.join(", "),
    },
    {
      label: "Description",
      values: () => null, // never highlight description diffs
      render: (a) => <span className="text-muted-foreground">{a.description}</span>,
    },
  ];

  const isDiff = (row: Row) => {
    if (list.length < 2) return false;
    const vals = list.map(row.values);
    return new Set(vals.map((v) => JSON.stringify(v))).size > 1;
  };

  return (
    <div className="min-h-dvh bg-background">
      <Navbar variant="landing" />

      <div className="sticky top-14 z-30 glass border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <Link
            to="/chat"
            className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground transition"
          >
            <ArrowLeft className="h-3.5 w-3.5 mr-1" /> Back to chat
          </Link>
          <div className="flex items-center gap-3">
            <div className="text-sm text-muted-foreground hidden sm:block">
              Comparing <span className="text-foreground font-medium tabular-nums">{list.length}</span> assessments
            </div>
            <Button
              size="sm"
              variant="ghost"
              onClick={clearAll}
              className="rounded-full text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="h-3.5 w-3.5 mr-1" /> Clear
            </Button>
          </div>
        </div>
      </div>

      <main className="mx-auto max-w-7xl px-4 sm:px-6 py-8 sm:py-10">
        {/* Mobile: stacked cards */}
        <div className="grid gap-3 md:hidden">
          {list.map((a, idx) => (
            <motion.div
              key={a.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: idx * 0.05 }}
              className="rounded-2xl border border-border bg-card/50 p-4"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-[11px] uppercase tracking-widest text-muted-foreground">{a.category}</div>
                  <Link
                    to="/assessments/$id"
                    params={{ id: a.id }}
                    className="block mt-1 font-medium hover:underline underline-offset-4"
                  >
                    {a.name}
                  </Link>
                </div>
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8 rounded-full shrink-0"
                  onClick={() => remove(a.id)}
                  aria-label={`Remove ${a.name}`}
                >
                  <X className="h-3.5 w-3.5" />
                </Button>
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-[13px]">
                {rows.map((row) => (
                  <div key={row.label} className={cn("col-span-1", row.label === "Description" && "col-span-2")}>
                    <dt className="text-[11px] uppercase tracking-wider text-muted-foreground">{row.label}</dt>
                    <dd className={cn("mt-0.5", isDiff(row) && "text-foreground font-medium")}>{row.render(a)}</dd>
                  </div>
                ))}
              </dl>
            </motion.div>
          ))}
        </div>

        {/* Desktop: side-by-side table */}
        <div className="hidden md:block overflow-x-auto rounded-2xl border border-border bg-card/40">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="sticky left-0 bg-card/80 backdrop-blur text-left px-5 py-4 align-bottom w-40 text-[11px] uppercase tracking-widest text-muted-foreground z-10">
                  Feature
                </th>
                {list.map((a) => (
                  <th key={a.id} className="text-left px-5 py-4 align-bottom min-w-65">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="text-[11px] uppercase tracking-widest text-muted-foreground">{a.category}</div>
                        <Link
                          to="/assessments/$id"
                          params={{ id: a.id }}
                          className="block mt-1 font-medium text-base hover:underline underline-offset-4"
                        >
                          {a.name}
                        </Link>
                      </div>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7 rounded-full shrink-0"
                        onClick={() => remove(a.id)}
                        aria-label={`Remove ${a.name}`}
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const diff = isDiff(row);
                return (
                  <tr key={row.label} className="border-t border-border/60 group">
                    <td className="sticky left-0 bg-card/80 backdrop-blur px-5 py-4 text-[11px] uppercase tracking-widest text-muted-foreground align-top z-10">
                      <span className="inline-flex items-center gap-1.5">
                        {row.label}
                        {diff && (
                          <span
                            className="h-1 w-1 rounded-full bg-amber-400"
                            aria-label="Values differ"
                            title="Values differ"
                          />
                        )}
                      </span>
                    </td>
                    {list.map((a) => (
                      <td
                        key={a.id}
                        className={cn(
                          "px-5 py-4 align-top text-[14px] transition-colors",
                          diff && "bg-amber-400/3",
                        )}
                      >
                        {row.render(a)}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <p className="mt-4 text-xs text-muted-foreground inline-flex items-center gap-1.5">
          <span className="h-1 w-1 rounded-full bg-amber-400" /> rows where values differ across assessments
        </p>
      </main>
      <Footer />
    </div>
  );
}

function BoolCell({ on }: { on: boolean }) {
  return on ? (
    <span className="inline-flex items-center gap-1 text-foreground">
      <Check className="h-3.5 w-3.5" /> Yes
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-muted-foreground">
      <X className="h-3.5 w-3.5" /> No
    </span>
  );
}
