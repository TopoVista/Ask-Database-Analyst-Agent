"use client";

import Link from "next/link";
import { LayoutDashboard, History, Database, Sigma } from "lucide-react";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Chat", icon: LayoutDashboard },
  { href: "/history", label: "History", icon: History },
  { href: "/connections", label: "Connections", icon: Database },
  { href: "/schema", label: "Schema", icon: Sigma },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-72 shrink-0 border-r border-white/10 bg-slate-950/80 p-4 backdrop-blur-md lg:block">
      <div className="mb-6 rounded-2xl border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-4 shadow-glow">
        <p className="text-[10px] uppercase tracking-[0.25em] text-muted-fg">Autonomous decision intelligence</p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-fg">Insight Engine</h1>
        <p className="mt-2 text-sm leading-6 text-fg/70">
          Ask a business question and get a multi-step analytical answer instead of a raw query result.
        </p>
      </div>

      <nav className="space-y-2">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm transition",
                active
                  ? "border-accent/30 bg-accent/12 text-fg shadow-glow"
                  : "border-white/10 bg-white/5 text-fg/80 hover:bg-white/10"
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
