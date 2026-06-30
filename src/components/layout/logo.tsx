import { Link } from "@tanstack/react-router";

export function Logo({ subtle = false }: { subtle?: boolean }) {
  return (
    <Link to="/" className="flex items-center gap-2.5 group">
      <span className="relative inline-flex h-7 w-7 items-center justify-center rounded-md bg-foreground text-background text-[11px] font-semibold tracking-tight">
        SHL
        <span className="absolute -inset-px rounded-md ring-1 ring-foreground/10 group-hover:ring-foreground/30 transition" />
      </span>
      {!subtle && (
        <span className="text-[15px] font-medium tracking-tight">
          Assessment <span className="text-muted-foreground">AI</span>
        </span>
      )}
    </Link>
  );
}
