import { cn } from "@/lib/utils";

type Props = React.InputHTMLAttributes<HTMLInputElement>;

export function Input({ className, ...props }: Props) {
  return (
    <input
      className={cn(
        "h-11 w-full rounded-2xl border border-white/10 bg-[rgba(8,14,24,0.92)] px-4 text-[15px] text-fg placeholder:text-muted-fg shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] outline-none transition-[border-color,box-shadow,background-color] focus:border-accent/60 focus:ring-2 focus:ring-accent/18",
        className
      )}
      {...props}
    />
  );
}
