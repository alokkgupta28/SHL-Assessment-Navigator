import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, RotateCcw, X } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ErrorBanner({
  message,
  onRetry,
  onDismiss,
}: {
  message: string | null;
  onRetry?: () => void;
  onDismiss?: () => void;
}) {
  return (
    <AnimatePresence>
      {message && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.2 }}
          role="alert"
          className="mx-auto max-w-3xl my-3 flex items-center gap-3 rounded-xl border border-destructive/40 bg-destructive/5 text-destructive px-3 py-2.5"
        >
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <div className="text-sm flex-1 min-w-0 truncate">{message}</div>
          {onRetry && (
            <Button
              size="sm"
              variant="ghost"
              onClick={onRetry}
              className="h-7 rounded-full text-destructive hover:bg-destructive/10 hover:text-destructive"
            >
              <RotateCcw className="h-3.5 w-3.5 mr-1" /> Retry
            </Button>
          )}
          {onDismiss && (
            <Button
              size="icon"
              variant="ghost"
              onClick={onDismiss}
              className="h-7 w-7 rounded-full text-destructive hover:bg-destructive/10 hover:text-destructive"
              aria-label="Dismiss error"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
