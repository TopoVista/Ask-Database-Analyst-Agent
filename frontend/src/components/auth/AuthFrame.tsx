import type { ReactNode } from "react";

export function AuthFrame({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="rounded-3xl border border-white/10 bg-white/5 p-4 shadow-glow backdrop-blur-md">
        {children}
      </div>
    </div>
  );
}
