"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, History, Database, Sigma, FileSpreadsheet, FileText, FlaskConical, Brain, BarChart3 } from "lucide-react";
import { UserButton } from "@clerk/nextjs";
import { ConnectionSelector } from "./ConnectionSelector";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Chat" },
  { href: "/history", icon: History, label: "History" },
  { href: "/connections", icon: Database, label: "Connections" },
  { href: "/schema", icon: Sigma, label: "Schema" },
  { href: "/datasets", icon: FileSpreadsheet, label: "Datasets" },
  { href: "/documents", icon: FileText, label: "Documents" },
  { href: "/simulation", icon: FlaskConical, label: "Simulation" },
  { href: "/specialists", icon: Brain, label: "Specialists" },
  { href: "/evaluation", icon: BarChart3, label: "Evaluation" },
];

const PAGE_LABELS: Record<string, string> = {
  "/dashboard": "Analytical workspace",
  "/history": "Session history",
  "/connections": "Connection management",
  "/schema": "Schema explorer",
  "/datasets": "Dataset management",
  "/documents": "RAG document search",
  "/simulation": "What-if simulation",
  "/specialists": "Specialist agents",
  "/evaluation": "Benchmarks and audits",
};

export function Header() {
  const pathname = usePathname();
  const currentLabel = PAGE_LABELS[pathname] ?? "Decision Intelligence";

  return (
    <header className="sticky top-0 z-20 border-b border-white/10 bg-[rgba(6,10,17,0.82)] px-4 py-4 backdrop-blur-xl md:px-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <Badge className="border-accent/20 bg-accent/10 text-accent">Decision Intelligence</Badge>
            <p className="hidden text-xs text-muted-fg md:block">Schema-first analytical reasoning</p>
          </div>
          <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="min-w-0">
              <p className="text-[11px] uppercase tracking-[0.24em] text-muted-fg">Workspace</p>
              <h2 className="mt-1 truncate text-xl font-semibold text-fg">{currentLabel}</h2>
            </div>
            <nav className="hidden items-center gap-2 md:flex lg:hidden">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.href}
                    href={item.href}
                    icon={<Icon className="h-3.5 w-3.5" />}
                    label={item.label}
                    active={pathname === item.href}
                  />
                );
              })}
            </nav>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 xl:justify-end">
          <ConnectionSelector />
          <UserButton afterSignOutUrl="/" />
        </div>
      </div>
    </header>
  );
}

function NavLink({ href, icon, label, active }: { href: string; icon: React.ReactNode; label: string; active: boolean }) {
  return (
    <Link
      href={href}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-2 text-xs font-medium transition-[background-color,border-color,color]",
        active
          ? "border-white/16 bg-white/10 text-fg"
          : "border-white/10 bg-white/5 text-fg/76 hover:border-white/14 hover:bg-white/8 hover:text-fg"
      )}
    >
      {icon}
      {label}
    </Link>
  );
}
