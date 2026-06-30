import { motion } from "framer-motion";
import { ArrowUpRight, Briefcase, Code2, Crown, Headphones } from "lucide-react";

const PROMPTS = [
  { icon: Code2, label: "I need to hire a Java Developer", hint: "Technology · Mid–Senior" },
  { icon: Briefcase, label: "Hiring a Front-end Engineer (React)", hint: "Technology · Mid" },
  { icon: Crown, label: "Leadership assessments for a VP role", hint: "Executive · Behavioural" },
  { icon: Headphones, label: "Entry-level sales hires — what to run?", hint: "Sales · Entry" },
];

export function Suggestions({ onPick }: { onPick: (p: string) => void }) {
  return (
    <div className="grid gap-2 sm:grid-cols-2 max-w-2xl w-full">
      {PROMPTS.map((p, i) => (
        <motion.button
          key={p.label}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.32, delay: 0.04 + i * 0.04 }}
          onClick={() => onPick(p.label)}
          className="group text-left rounded-xl border border-border bg-card/50 hover:bg-card hover:border-foreground/20 px-4 py-3 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60"
        >
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-background border border-border/80 flex items-center justify-center flex-shrink-0">
              <p.icon className="h-3.5 w-3.5 text-muted-foreground group-hover:text-foreground transition" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-sm truncate">{p.label}</div>
              <div className="text-[11px] text-muted-foreground mt-0.5 truncate">{p.hint}</div>
            </div>
            <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground group-hover:text-foreground transition flex-shrink-0" />
          </div>
        </motion.button>
      ))}
    </div>
  );
}
