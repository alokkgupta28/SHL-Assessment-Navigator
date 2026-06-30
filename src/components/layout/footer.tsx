import { Logo } from "./logo";

export function Footer() {
  return (
    <footer className="border-t border-border/60 mt-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 py-12 grid gap-10 md:grid-cols-4">
        <div className="space-y-3">
          <Logo />
          <p className="text-sm text-muted-foreground max-w-xs">
            Conversational discovery of the right SHL assessment for every hiring decision.
          </p>
        </div>
        {[
          { title: "Product", items: ["Chat", "Catalog", "Comparison", "API"] },
          { title: "Company", items: ["About", "Customers", "Careers", "Press"] },
          { title: "Legal", items: ["Privacy", "Terms", "Security", "DPA"] },
        ].map((col) => (
          <div key={col.title}>
            <div className="text-sm font-medium mb-3">{col.title}</div>
            <ul className="space-y-2 text-sm text-muted-foreground">
              {col.items.map((i) => (
                <li key={i}><a className="hover:text-foreground transition" href="#">{i}</a></li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-border/60">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 py-6 flex items-center justify-between text-xs text-muted-foreground">
          <span>© {new Date().getFullYear()} SHL Labs. Demo interface.</span>
          <span>Built for recruiters.</span>
        </div>
      </div>
    </footer>
  );
}
