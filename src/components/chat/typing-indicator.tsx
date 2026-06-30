export function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 py-1.5" aria-label="Assistant is thinking" role="status">
      <span className="relative inline-flex h-2 w-2">
        <span className="absolute inset-0 rounded-full bg-foreground/60 animate-ping" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-foreground/70" />
      </span>
      <span className="text-[13px] text-muted-foreground shimmer-text">Thinking</span>
    </div>
  );
}
