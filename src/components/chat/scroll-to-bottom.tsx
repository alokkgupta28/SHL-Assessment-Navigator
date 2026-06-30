import { AnimatePresence, motion } from "framer-motion";
import { ArrowDown } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ScrollToBottom({
  visible,
  onClick,
}: {
  visible: boolean;
  onClick: () => void;
}) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: 6, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 6, scale: 0.95 }}
          transition={{ duration: 0.18 }}
          className="absolute left-1/2 -translate-x-1/2 bottom-4 z-10"
        >
          <Button
            size="sm"
            variant="outline"
            onClick={onClick}
            className="rounded-full h-8 px-3 shadow-md bg-card/90 backdrop-blur border-border"
            aria-label="Scroll to latest message"
          >
            <ArrowDown className="h-3.5 w-3.5 mr-1" /> Latest
          </Button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
