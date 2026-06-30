import { Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 grid-bg [mask-image:radial-gradient(ellipse_60%_50%_at_50%_30%,black,transparent)]" />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 pt-24 pb-20 md:pt-32 md:pb-28 text-center">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 rounded-full border border-border/80 bg-card/40 px-3 py-1 text-xs text-muted-foreground backdrop-blur"
        >
          <Sparkles className="h-3 w-3" />
          New — Conversational assessment discovery
        </motion.div>
        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.05 }}
          className="mt-6 text-4xl sm:text-6xl md:text-7xl font-semibold tracking-tight text-balance leading-[1.02]"
        >
          Find the right SHL <br className="hidden sm:block" />
          assessment with AI.
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.12 }}
          className="mt-6 mx-auto max-w-xl text-base sm:text-lg text-muted-foreground text-balance"
        >
          Describe the role. Answer a few clarifying questions. Get a curated shortlist
          of validated assessments — ready to compare and deploy.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.18 }}
          className="mt-9 flex items-center justify-center gap-3"
        >
          <Button asChild size="lg" className="rounded-full px-6">
            <Link to="/chat">
              Start chatting
              <ArrowRight className="ml-1.5 h-4 w-4" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="ghost" className="rounded-full px-6">
            <a href="#features">Learn more</a>
          </Button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.28 }}
          className="relative mt-20 mx-auto max-w-4xl"
        >
          <div className="rounded-2xl border border-border bg-card/70 shadow-2xl shadow-black/20 backdrop-blur overflow-hidden">
            <div className="flex items-center gap-1.5 border-b border-border/70 px-4 py-2.5">
              <span className="h-2.5 w-2.5 rounded-full bg-muted" />
              <span className="h-2.5 w-2.5 rounded-full bg-muted" />
              <span className="h-2.5 w-2.5 rounded-full bg-muted" />
              <span className="ml-3 text-xs text-muted-foreground">SHL Assessment AI · session</span>
            </div>
            <div className="p-6 sm:p-8 text-left space-y-4">
              <div className="flex justify-end">
                <div className="rounded-2xl rounded-br-md bg-foreground text-background px-3.5 py-2 text-sm max-w-sm">
                  I'm hiring a senior Java engineer with leadership signals.
                </div>
              </div>
              <div className="flex gap-3">
                <div className="h-7 w-7 rounded-full bg-muted flex-shrink-0" />
                <div className="text-sm space-y-2 max-w-lg">
                  <p>Two quick checks — is people-management in scope, and what time budget per candidate?</p>
                  <p className="text-muted-foreground text-xs">Drafting a shortlist…</p>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2">
                {["Java Developer (New)", "OPQ32", "Verify G+ Numerical"].map((n) => (
                  <div key={n} className="rounded-lg border border-border/80 bg-background/60 px-3 py-2 text-xs">
                    <div className="font-medium truncate">{n}</div>
                    <div className="text-muted-foreground mt-0.5">Technology · 40m</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
