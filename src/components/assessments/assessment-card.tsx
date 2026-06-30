import { Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Bookmark, BookmarkCheck, ExternalLink, GitCompareArrows, Clock, Languages, Zap, Wifi } from "lucide-react";
import type { Assessment } from "@/types/assessment";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function AssessmentCard({
  assessment: a,
  compareActive,
  savedActive,
  onCompare,
  onSave,
  index = 0,
}: {
  assessment: Assessment;
  compareActive?: boolean;
  savedActive?: boolean;
  onCompare?: (id: string) => void;
  onSave?: (id: string) => void;
  index?: number;
}) {
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4, transition: { duration: 0.15 } }}
      transition={{ duration: 0.32, delay: Math.min(index * 0.035, 0.25), ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ y: -1 }}
      className={cn(
        "group rounded-xl border bg-card/60 p-4 transition-colors hover:bg-card focus-within:border-foreground/30",
        compareActive ? "border-foreground/40 ring-1 ring-foreground/10" : "border-border",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <Link
            to="/assessments/$id"
            params={{ id: a.id }}
            className="font-medium text-[15px] hover:underline underline-offset-4 truncate block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60 rounded"
          >
            {a.name}
          </Link>
          <div className="mt-0.5 text-xs text-muted-foreground truncate">{a.category}</div>
        </div>
        <Button
          size="icon"
          variant="ghost"
          className="h-9 w-9 -m-1 rounded-full flex-shrink-0"
          onClick={() => onSave?.(a.id)}
          aria-label={savedActive ? `Remove ${a.name} from saved` : `Save ${a.name}`}
          aria-pressed={savedActive}
        >
          {savedActive ? <BookmarkCheck className="h-4 w-4" /> : <Bookmark className="h-4 w-4" />}
        </Button>
      </div>

      <p className="mt-3 text-sm text-muted-foreground line-clamp-2 leading-relaxed">{a.description}</p>

      <div className="mt-3 flex flex-wrap gap-1.5">
        <Badge variant="secondary" className="rounded-full font-normal gap-1">
          <Clock className="h-3 w-3" aria-hidden="true" /> {a.durationMinutes}m
        </Badge>
        <Badge variant="secondary" className="rounded-full font-normal">
          {a.jobLevels.join(" · ")}
        </Badge>
        {a.adaptive && (
          <Badge variant="secondary" className="rounded-full font-normal gap-1">
            <Zap className="h-3 w-3" aria-hidden="true" /> Adaptive
          </Badge>
        )}
        {a.remote && (
          <Badge variant="secondary" className="rounded-full font-normal gap-1">
            <Wifi className="h-3 w-3" aria-hidden="true" /> Remote
          </Badge>
        )}
        <Badge variant="secondary" className="rounded-full font-normal gap-1">
          <Languages className="h-3 w-3" aria-hidden="true" /> {a.languages.length}
        </Badge>
      </div>

      <div className="mt-4 flex items-center gap-2">
        <Button
          size="sm"
          variant={compareActive ? "default" : "outline"}
          className="rounded-full h-8"
          onClick={() => onCompare?.(a.id)}
          aria-pressed={compareActive}
        >
          <GitCompareArrows className="h-3.5 w-3.5 mr-1" />
          {compareActive ? "In compare" : "Compare"}
        </Button>
        <Button asChild size="sm" variant="ghost" className="rounded-full h-8 text-muted-foreground">
          <a href={a.officialUrl} target="_blank" rel="noreferrer" aria-label={`Open ${a.name} in official catalog`}>
            Official <ExternalLink className="h-3 w-3 ml-1" />
          </a>
        </Button>
      </div>
    </motion.article>
  );
}
