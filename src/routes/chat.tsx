import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { PanelRightOpen, RefreshCw, RotateCcw } from "lucide-react";
import { Navbar } from "@/components/layout/navbar";
import { useChat } from "@/hooks/use-chat";
import { useLocalSet } from "@/hooks/use-local-set";
import { MessageBubble } from "@/components/chat/message-bubble";
import { Composer } from "@/components/chat/composer";
import { EmptyState } from "@/components/chat/empty-state";
import { ErrorBanner } from "@/components/chat/error-banner";
import { ScrollToBottom } from "@/components/chat/scroll-to-bottom";
import { RecommendationsRail } from "@/components/assessments/recommendations-rail";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetHeader } from "@/components/ui/sheet";
import { toast } from "sonner";


export const Route = createFileRoute("/chat")({
  head: () => ({
    meta: [
      { title: "Chat — SHL Assessment AI" },
      { name: "description", content: "Conversational interface for discovering SHL assessments." },
    ],
  }),
  component: ChatPage,
});

function ChatPage() {
  const { messages, status, error, recommendations, send, stop, reset, regenerate } = useChat();
  const compare = useLocalSet("shl-compare");
  const saved = useLocalSet("shl-saved");

  const scrollerRef = useRef<HTMLDivElement>(null);
  const [stuckToBottom, setStuckToBottom] = useState(true);

  const scrollToBottom = (behavior: ScrollBehavior = "smooth") => {
    const el = scrollerRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior });
  };

  // Track whether the user has scrolled away from the bottom.
  useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const onScroll = () => {
      const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
      setStuckToBottom(distance < 80);
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, []);

  // Auto-stick to bottom while streaming, but respect user's manual scroll.
  useLayoutEffect(() => {
    if (stuckToBottom) scrollToBottom(messages.length <= 1 ? "auto" : "smooth");
  }, [messages, stuckToBottom]);

  const [recsOpen, setRecsOpen] = useState(false);
  const recs = recommendations;
  const hasConversation = messages.length > 0;
  const busy = status === "thinking" || status === "streaming";

  const statusLabel =
    status === "thinking"
      ? "Thinking"
      : status === "streaming"
      ? "Streaming"
      : status === "error"
      ? "Error"
      : "Ready";

  return (
    <div className="h-dvh flex flex-col bg-background overflow-hidden">
      <Navbar variant="app" />

      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_400px] xl:grid-cols-[minmax(0,1fr)_440px]">
        {/* Conversation column */}
        <section className="min-w-0 flex flex-col border-r border-border min-h-0">
          <div className="flex items-center justify-between gap-2 px-4 sm:px-8 py-2.5 border-b border-border/60">
            <div className="flex items-center gap-3 min-w-0">
              <div className="text-[11px] uppercase tracking-widest text-muted-foreground hidden sm:block">
                Session
              </div>
              <span
                className="inline-flex items-center gap-1.5 text-xs text-muted-foreground"
                role="status"
                aria-live="polite"
              >
                <span
                  className={
                    "h-1.5 w-1.5 rounded-full " +
                    (status === "idle"
                      ? "bg-emerald-400"
                      : status === "error"
                      ? "bg-red-400"
                      : "bg-amber-400 animate-pulse")
                  }
                  aria-hidden="true"
                />
                {statusLabel}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              {hasConversation && !busy && status !== "error" && (
                <Button
                  size="sm"
                  variant="ghost"
                  className="rounded-full text-muted-foreground hidden sm:inline-flex"
                  onClick={regenerate}
                  aria-label="Regenerate last response"
                >
                  <RotateCcw className="h-3.5 w-3.5 mr-1" /> Regenerate
                </Button>
              )}
              <Button
                size="sm"
                variant="ghost"
                className="rounded-full text-muted-foreground"
                onClick={() => {
                  reset();
                  toast("Conversation cleared");
                }}
                aria-label="Start a new conversation"
              >
                <RefreshCw className="h-3.5 w-3.5 sm:mr-1" />
                <span className="hidden sm:inline">New</span>
              </Button>
              <Sheet open={recsOpen} onOpenChange={setRecsOpen}>
                <SheetTrigger asChild>
                  <Button size="sm" variant="outline" className="rounded-full lg:hidden">
                    <PanelRightOpen className="h-3.5 w-3.5 sm:mr-1" />
                    <span className="hidden sm:inline">Recommendations</span>
                  </Button>
                </SheetTrigger>
                <SheetContent side="right" className="w-full sm:max-w-md p-0">
                  <SheetHeader className="sr-only">
                    <SheetTitle>Recommendations</SheetTitle>
                  </SheetHeader>
                  <RecommendationsRail
                    assessments={recs}
                    loading={status === "thinking"}
                    compareIds={compare.ids}
                    savedIds={saved.ids}
                    onCompare={(id) => compare.toggle(id)}
                    onSave={(id) => {
                      saved.toggle(id);
                      toast(saved.has(id) ? "Removed from saved" : "Saved");
                    }}
                  />
                </SheetContent>
              </Sheet>
            </div>
          </div>

          <div className="relative flex-1 min-h-0">
            <div
              ref={scrollerRef}
              className="absolute inset-0 overflow-y-auto"
              role="log"
              aria-label="Conversation"
              aria-live="polite"
            >
              {!hasConversation ? (
                <div className="h-full flex">
                  <EmptyState onPick={(p) => send(p)} />
                </div>
              ) : (
                <div className="mx-auto max-w-3xl px-4 sm:px-8 py-8 space-y-6">
                  <AnimatePresence initial={false}>
                    {messages.map((m) => (
                      <MessageBubble key={m.id} message={m} />
                    ))}
                  </AnimatePresence>
                  <ErrorBanner message={error} onRetry={regenerate} />
                </div>
              )}
            </div>
            <ScrollToBottom
              visible={hasConversation && !stuckToBottom}
              onClick={() => {
                setStuckToBottom(true);
                scrollToBottom();
              }}
            />
          </div>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="border-t border-border/60 px-4 sm:px-8 py-3 sm:py-4 pb-[max(0.75rem,env(safe-area-inset-bottom))]"
          >
            <div className="mx-auto max-w-3xl">
              <Composer onSend={send} onStop={stop} status={status} />
              <p className="mt-2 text-[11px] text-muted-foreground text-center">
                Recommendations are grounded in the SHL catalog served by the local FastAPI backend.
              </p>
            </div>
          </motion.div>
        </section>

        {/* Recommendations column (desktop) */}
        <aside className="hidden lg:block min-w-0 bg-card/30" aria-label="Recommended assessments">
          <RecommendationsRail
            assessments={recs}
            loading={status === "thinking"}
            compareIds={compare.ids}
            savedIds={saved.ids}
            onCompare={(id) => compare.toggle(id)}
            onSave={(id) => {
              saved.toggle(id);
              toast(saved.has(id) ? "Removed from saved" : "Saved");
            }}
          />
        </aside>
      </div>
    </div>
  );
}
