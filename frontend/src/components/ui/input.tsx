import { cn } from "@/lib/utils";

type Props = React.InputHTMLAttributes<HTMLInputElement>;

export function Input({ className, ...props }: Props) {
  return (
    <input
      className={cn(
        "h-10 w-full rounded-xl border border-white/10 bg-white/5 px-3 text-sm text-fg placeholder:text-muted-fg shadow-sm outline-none transition focus:border-accent/60 focus:ring-2 focus:ring-accent/20",
        className
      )}
      {...props}
    />
  );
}

