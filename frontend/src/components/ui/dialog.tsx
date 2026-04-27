"use client";

import { createContext, useContext, useState } from "react";
import { cn } from "@/lib/utils";

type DialogContextValue = {
  open: boolean;
  setOpen: (open: boolean) => void;
};

const DialogContext = createContext<DialogContextValue | null>(null);

export function Dialog({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return <DialogContext.Provider value={{ open, setOpen }}>{children}</DialogContext.Provider>;
}

export function DialogTrigger({ children }: { children: React.ReactNode }) {
  const ctx = useContext(DialogContext);
  if (!ctx) return null;
  return <div onClick={() => ctx.setOpen(true)}>{children}</div>;
}

export function DialogContent({ className, children }: { className?: string; children: React.ReactNode }) {
  const ctx = useContext(DialogContext);
  if (!ctx?.open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className={cn("w-full max-w-lg rounded-2xl border border-white/10 bg-slate-950 p-6 shadow-glow", className)}>
        {children}
      </div>
    </div>
  );
}

export function DialogHeader({ children }: { children: React.ReactNode }) {
  return <div className="mb-4">{children}</div>;
}

export function DialogTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-lg font-semibold text-fg">{children}</h3>;
}

