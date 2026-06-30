import { motion } from "framer-motion";
import { User, MessagesSquare, BrainCircuit, ClipboardCheck } from "lucide-react";

const steps = [
  { icon: User, label: "Recruiter", desc: "Describes the hiring need." },
  { icon: MessagesSquare, label: "Conversation", desc: "Clarifying questions surface constraints." },
  { icon: BrainCircuit, label: "AI", desc: "Ranks assessments from the SHL catalog." },
  { icon: ClipboardCheck, label: "Assessments", desc: "Curated shortlist, ready to deploy." },
];

export function Workflow() {
  return (
    <section id="workflow" className="mx-auto max-w-7xl px-4 sm:px-6 py-24">
      <div className="max-w-2xl">
        <div className="text-xs uppercase tracking-widest text-muted-foreground">How it works</div>
        <h2 className="mt-3 text-3xl sm:text-4xl font-semibold tracking-tight">
          From requirement to shortlist in one conversation.
        </h2>
      </div>

      <div className="mt-12 relative">
        <div className="hidden md:block absolute left-0 right-0 top-[34px] h-px bg-gradient-to-r from-transparent via-border to-transparent" />
        <div className="grid gap-6 md:grid-cols-4">
          {steps.map((s, i) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.45, delay: i * 0.08 }}
              className="relative rounded-2xl border border-border bg-card/60 p-5"
            >
              <div className="h-[68px] flex items-center">
                <div className="h-12 w-12 rounded-xl bg-background border border-border flex items-center justify-center">
                  <s.icon className="h-5 w-5" />
                </div>
              </div>
              <div className="mt-2 text-xs text-muted-foreground">Step {i + 1}</div>
              <div className="font-medium mt-0.5">{s.label}</div>
              <p className="text-sm text-muted-foreground mt-1">{s.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
