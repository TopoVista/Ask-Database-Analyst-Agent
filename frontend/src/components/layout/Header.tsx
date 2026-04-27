"use client";

import Link from "next/link";
import { LayoutDashboard, History, Database, Sigma } from "lucide-react";
import { UserButton } from "@clerk/nextjs";
import { ConnectionSelector } from "./ConnectionSelector";
import { Badge } from "@/components/ui/badge";

export function Header() {
  return (
    <header className="border-b border-white/10 bg-slate-950/70 px-4 py-3 backdrop-blur-md md:px-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <Badge className="border-accent/30 bg-accent/12 text-accent">Decision Agent</Badge>
          <nav className="hidden items-center gap-1 md:flex">
            <NavLink href="/dashboard" icon={<LayoutDashboard className="h-3.5 w-3.5" />} label="Chat" />
            <NavLink href="/history" icon={<History className="h-3.5 w-3.5" />} label="History" />
            <NavLink href="/connections" icon={<Database className="h-3.5 w-3.5" />} label="Connections" />
            <NavLink href="/schema" icon={<Sigma className="h-3.5 w-3.5" />} label="Schema" />
          </nav>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <ConnectionSelector />
          <UserButton afterSignOutUrl="/" />
        </div>
      </div>
    </header>
  );
}

function NavLink({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-fg transition hover:bg-white/10"
    >
      {icon}
      {label}
    </Link>
  );
}
