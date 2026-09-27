import { cn } from "@/lib/utils";

export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn("min-h-28 w-full rounded-2xl border border-white/10 bg-[rgba(8,14,24,0.92)] px-4 py-3 text-sm text-fg outline-none transition focus:border-accent/60 focus:ring-2 focus:ring-accent/18", className)} {...props} />;
}
