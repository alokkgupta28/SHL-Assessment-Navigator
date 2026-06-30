import { Link } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronRight, Inbox, ListFilter } from "lucide-react";
import type { Assessment } from "@/types/assessment";
import { AssessmentCard } from "./assessment-card";
import { Button } from "@/components/ui/button";

function CardSkeleton({ delay = 0 }: { delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3, delay }}
      className="rounded-xl border border-border bg-card/40 p-4 space-y-3 shimmer"
    >
      <div className="flex items-center justify-between">
        <div className="h-3.5 w-2/3 rounded bg-muted/70" />
        <div className="h-7 w-7 rounded-full bg-muted/60" />
      </div>
      <div className="h-2.5 w-1/3 rounded bg-muted/50" />
      <div className="space-y-1.5">
        <div className="h-2.5 w-full rounded bg-muted/40" />
        <div className="h-2.5 w-4/5 rounded bg-muted/40" />
      </div>
      <div className="flex gap-1.5 pt-1">
        <div className="h-5 w-14 rounded-full bg-muted/50" />
        <div className="h-5 w-20 rounded-full bg-muted/50" />
        <div className="h-5 w-16 rounded-full bg-muted/40" />
      </div>
      <div className="shimmer-overlay" />
    </motion.div>
  );
}

export function RecommendationsRail({
  assessments,
  loading,
  compareIds,
  savedIds,
  onCompare,
  onSave,
}: {
  assessments: Assessment[];
  loading?: boolean;
  compareIds: string[];
  savedIds: string[];
  onCompare: (id: string) => void;
  onSave: (id: string) => void;
}) {
  const empty = !loading && assessments.length === 0;
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-5 pt-5 pb-3">
        <div>
          <div className="text-[11px] uppercase tracking-widest text-muted-foreground">Recommendations</div>
          <div className="mt-1 text-sm font-medium flex items-center gap-2">
            {loading ? (
              <>
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-foreground/60 opacity-70" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-foreground/70" />
                </span>
                <span className="shimmer-text">Drafting shortlist</span>
              </>
            ) : (
              <span>{assessments.length} assessments</span>
            )}
          </div>
        </div>
        <Button variant="ghost" size="sm" className="rounded-full text-muted-foreground" disabled={loading || empty}>
          <ListFilter className="h-3.5 w-3.5 mr-1" /> Filter
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 pb-5 space-y-3">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} delay={i * 0.05} />)
        ) : empty ? (
          <div className="h-full min-h-[280px] flex flex-col items-center justify-center text-center px-4">
            <div className="h-10 w-10 rounded-xl border border-border bg-card/60 flex items-center justify-center">
              <Inbox className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="mt-4 text-sm font-medium">No recommendations yet</div>
            <p className="mt-1 text-xs text-muted-foreground max-w-[220px]">
              Start a conversation to surface assessments tailored to the role.
            </p>
          </div>
        ) : (
          <AnimatePresence initial={false} mode="popLayout">
            {assessments.map((a, i) => (
              <AssessmentCard
                key={a.id}
                assessment={a}
                index={i}
                compareActive={compareIds.includes(a.id)}
                savedActive={savedIds.includes(a.id)}
                onCompare={onCompare}
                onSave={onSave}
              />
            ))}
          </AnimatePresence>
        )}
      </div>

      <AnimatePresence>
        {compareIds.length >= 2 && (
          <motion.div
            initial={{ y: 24, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 24, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="border-t border-border bg-card/90 backdrop-blur px-5 py-3 flex items-center justify-between"
          >
            <div className="text-sm">
              <span className="font-medium tabular-nums">{compareIds.length}</span>{" "}
              <span className="text-muted-foreground">selected for compare</span>
            </div>
            <Button asChild size="sm" className="rounded-full">
              <Link to="/compare" search={{ ids: compareIds.join(",") }}>
                Compare <ChevronRight className="h-3.5 w-3.5 ml-0.5" />
              </Link>
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
