import { useEffect, useRef, useState } from "react";
import { ArrowUp, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ChatStatus } from "@/types/chat";
import { cn } from "@/lib/utils";

const MAX_CHARS = 4000;

export function Composer({
  onSend,
  onStop,
  status,
}: {
  onSend: (text: string) => void;
  onStop: () => void;
  status: ChatStatus;
}) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);
  const busy = status === "thinking" || status === "streaming";

  useEffect(() => {
    ref.current?.focus();
  }, []);

  useEffect(() => {
    if (!busy) ref.current?.focus();
  }, [busy]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 220) + "px";
  }, [value]);

  const submit = () => {
    const v = value.trim();
    if (!v || busy) return;
    onSend(v.slice(0, MAX_CHARS));
    setValue("");
  };

  const tooLong = value.length > MAX_CHARS;

  return (
    <div
      className={cn(
        "relative rounded-2xl border bg-card/80 backdrop-blur shadow-sm transition",
        "focus-within:border-foreground/40 focus-within:shadow-md",
        tooLong ? "border-destructive/60" : "border-border",
      )}
    >
      <label htmlFor="composer-textarea" className="sr-only">
        Message
      </label>
      <textarea
        id="composer-textarea"
        ref={ref}
        rows={1}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder="Describe the role you're hiring for…"
        aria-label="Describe the role you're hiring for"
        aria-invalid={tooLong || undefined}
        className="w-full resize-none bg-transparent px-4 pt-3.5 pb-12 text-[15px] outline-none placeholder:text-muted-foreground/70"
      />
      <div className="absolute bottom-2 left-3 right-2.5 flex items-center justify-between gap-2">
        <div className="text-[11px] text-muted-foreground hidden sm:flex items-center gap-2 min-w-0">
          <span>
            <kbd className="font-mono rounded border border-border bg-background px-1.5 py-0.5">↵</kbd> send
          </span>
          <span className="opacity-50">·</span>
          <span>
            <kbd className="font-mono rounded border border-border bg-background px-1.5 py-0.5">⇧ ↵</kbd> new line
          </span>
          {value.length > MAX_CHARS * 0.8 && (
            <>
              <span className="opacity-50">·</span>
              <span className={cn(tooLong ? "text-destructive" : "text-muted-foreground")}>
                {value.length}/{MAX_CHARS}
              </span>
            </>
          )}
        </div>
        <div className="ml-auto">
          {busy ? (
            <Button
              size="icon"
              variant="outline"
              className="h-9 w-9 rounded-full"
              onClick={onStop}
              aria-label="Stop generating"
            >
              <Square className="h-3.5 w-3.5 fill-current" />
            </Button>
          ) : (
            <Button
              size="icon"
              className="h-9 w-9 rounded-full"
              onClick={submit}
              disabled={!value.trim() || tooLong}
              aria-label="Send message"
            >
              <ArrowUp className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
