import { Link } from "@tanstack/react-router";
import { ArrowUpRight } from "lucide-react";
import { Logo } from "./logo";
import { ThemeToggle } from "./theme-toggle";
import { Button } from "@/components/ui/button";

export function Navbar({ variant = "landing" }: { variant?: "landing" | "app" }) {
  return (
    <header className="sticky top-0 z-40">
      <div className="glass">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-8">
            <Logo />
            {variant === "landing" && (
              <nav className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
                <a href="#features" className="hover:text-foreground transition">Features</a>
                <a href="#workflow" className="hover:text-foreground transition">How it works</a>
                <Link to="/chat" className="hover:text-foreground transition">Chat</Link>
              </nav>
            )}
            {variant === "app" && (
              <div className="hidden md:flex items-center gap-2 text-xs text-muted-foreground">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
                </span>
                Online
              </div>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            <ThemeToggle />
            {variant === "landing" ? (
              <Button asChild size="sm" className="rounded-full px-4">
                <Link to="/chat">
                  Start chatting
                  <ArrowUpRight className="ml-1 h-3.5 w-3.5" />
                </Link>
              </Button>
            ) : (
              <Button asChild size="sm" variant="ghost" className="rounded-full">
                <Link to="/">Exit</Link>
              </Button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
