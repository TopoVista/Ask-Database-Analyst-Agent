"use client";

import Link from "next/link";
import { LayoutDashboard, History, Database, Sigma } from "lucide-react";
import { usePathname } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Chat", icon: LayoutDashboard },
  { href: "/history", label: "History", icon: History },
  { href: "/connections", label: "Connections", icon: Database },
  { href: "/schema", label: "Schema", icon: Sigma },
];

const NAV_COPY: Record<string, string> = {
  "/dashboard": "Run and inspect analysis",
  "/history": "Review previous sessions",
  "/connections": "Manage database access",
  "/schema": "Inspect connected tables",
};

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-80 shrink-0 border-r border-white/10 bg-[rgba(6,10,17,0.76)] px-5 py-6 backdrop-blur-xl lg:block">
      <div className="rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(23,31,48,0.96),rgba(11,17,28,0.96))] p-5 shadow-glow">
        <Badge className="border-accent/20 bg-accent/10 text-accent">Control room</Badge>
        <h1 className="mt-4 text-[28px] font-semibold leading-[1.1] text-fg">Insight engine for operational decisions</h1>
        <p className="mt-3 text-sm leading-6 text-fg/70">
          Connect a warehouse, inspect the schema, and turn broad business questions into traced analytical answers.
        </p>
        <div className="mt-5 grid grid-cols-2 gap-3">
          <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-3">
            <p className="text-[10px] uppercase tracking-[0.24em] text-muted-fg">Mode</p>
            <p className="mt-2 text-sm font-medium text-fg">Schema first</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-3">
            <p className="text-[10px] uppercase tracking-[0.24em] text-muted-fg">Output</p>
            <p className="mt-2 text-sm font-medium text-fg">Traceable insight</p>
          </div>
        </div>
      </div>

      <nav className="mt-6 space-y-2">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-[22px] border px-4 py-3.5 text-sm transition-[background-color,border-color,transform,color]",
                active
                  ? "border-white/14 bg-white/10 text-fg shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
                  : "border-white/8 bg-transparent text-fg/72 hover:border-white/10 hover:bg-white/6 hover:text-fg"
              )}
            >
              <div
                className={cn(
                  "flex h-9 w-9 items-center justify-center rounded-2xl border transition-colors",
                  active ? "border-accent/20 bg-accent/12 text-accent" : "border-white/10 bg-white/5 text-muted-fg"
                )}
              >
                <Icon className="h-4 w-4" />
              </div>
              <div>
                <span className="block font-medium">{item.label}</span>
                <span className="block text-xs text-muted-fg">{NAV_COPY[item.href]}</span>
              </div>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
