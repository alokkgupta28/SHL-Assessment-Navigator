import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Sparkles, User } from "lucide-react";
import type { ChatMessage } from "@/types/chat";
import { cn } from "@/lib/utils";
import { TypingIndicator } from "./typing-indicator";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
      className={cn("flex gap-3 w-full", isUser ? "justify-end" : "justify-start")}
      role="article"
      aria-label={isUser ? "Your message" : "Assistant message"}
    >
      {!isUser && (
        <div
          aria-hidden="true"
          className="h-7 w-7 rounded-full bg-foreground text-background flex items-center justify-center flex-shrink-0 mt-0.5 ring-1 ring-border"
        >
          <Sparkles className="h-3.5 w-3.5" />
        </div>
      )}
      <div
        className={cn(
          "text-[14.5px] leading-relaxed min-w-0",
          isUser
            ? "max-w-[80%] sm:max-w-[68ch] rounded-2xl rounded-br-md bg-foreground text-background px-3.5 py-2 break-words"
            : "max-w-[80ch] text-foreground",
        )}
      >
        {message.streaming && !message.content ? (
          <TypingIndicator />
        ) : isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div
            className="prose-chat"
            aria-live={message.streaming ? "polite" : undefined}
            aria-busy={message.streaming || undefined}
          >
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => <p className="mb-2.5 last:mb-0">{children}</p>,
                ul: ({ children }) => <ul className="mb-2.5 list-disc pl-5 space-y-1">{children}</ul>,
                ol: ({ children }) => <ol className="mb-2.5 list-decimal pl-5 space-y-1">{children}</ol>,
                strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                code: ({ children }) => (
                  <code className="font-mono text-[13px] rounded-md bg-muted px-1.5 py-0.5">{children}</code>
                ),
                pre: ({ children }) => (
                  <pre className="font-mono text-[13px] my-3 rounded-lg bg-muted p-3 overflow-x-auto">{children}</pre>
                ),
                table: ({ children }) => (
                  <div className="my-3 overflow-x-auto rounded-lg border border-border">
                    <table className="w-full text-sm">{children}</table>
                  </div>
                ),
                th: ({ children }) => (
                  <th className="text-left font-medium px-3 py-2 bg-muted/60 border-b border-border">{children}</th>
                ),
                td: ({ children }) => <td className="px-3 py-2 border-b border-border/60">{children}</td>,
                a: ({ children, href }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    className="underline underline-offset-4 hover:text-foreground"
                  >
                    {children}
                  </a>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
            {message.streaming && (
              <span
                aria-hidden="true"
                className="inline-block w-[6px] h-[14px] align-[-2px] ml-0.5 bg-foreground/80 animate-pulse rounded-[1px]"
              />
            )}
          </div>
        )}
      </div>
      {isUser && (
        <div
          aria-hidden="true"
          className="h-7 w-7 rounded-full bg-muted flex items-center justify-center flex-shrink-0 mt-0.5 ring-1 ring-border"
        >
          <User className="h-3.5 w-3.5" />
        </div>
      )}
    </motion.div>
  );
}
