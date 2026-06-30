import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import { Suggestions } from "./suggestions";

export function EmptyState({ onPick }: { onPick: (p: string) => void }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center px-4 py-10">
      <motion.div
        initial={{ opacity: 0, scale: 0.92 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="relative"
      >
        <div className="h-14 w-14 rounded-2xl bg-foreground text-background flex items-center justify-center shadow-xl shadow-foreground/10">
          <Sparkles className="h-6 w-6" />
        </div>
        <div className="absolute -inset-3 rounded-3xl border border-border/80" />
        <div className="absolute -inset-6 rounded-[28px] border border-border/40" />
      </motion.div>
      <motion.h2
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="mt-8 text-2xl sm:text-[28px] font-semibold tracking-tight text-balance"
      >
        What are you hiring for?
      </motion.h2>
      <motion.p
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.16 }}
        className="mt-2 text-sm text-muted-foreground max-w-md text-balance"
      >
        Describe the role in your own words. I'll ask a few clarifying questions and assemble
        a shortlist of validated SHL assessments.
      </motion.p>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.22 }}
        className="mt-8 w-full flex justify-center"
      >
        <Suggestions onPick={onPick} />
      </motion.div>
    </div>
  );
}
