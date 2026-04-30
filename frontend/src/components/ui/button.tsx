import { cn } from "@/lib/utils";

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "secondary" | "ghost" | "outline";
  size?: "sm" | "md" | "lg";
};

export function Button({ className, variant = "default", size = "md", ...props }: Props) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-2xl border text-[13px] font-medium transition-[transform,background-color,border-color,box-shadow,color] duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/45 focus-visible:ring-offset-2 focus-visible:ring-offset-bg active:translate-y-px disabled:pointer-events-none disabled:opacity-50";
  const variants = {
    default:
      "border-accent/60 bg-accent text-accent-fg shadow-[0_12px_30px_rgba(252,186,73,0.18)] hover:border-accent hover:brightness-[1.03]",
    secondary:
      "border-white/10 bg-[rgba(19,27,43,0.92)] text-fg shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] hover:border-white/16 hover:bg-[rgba(24,33,51,0.96)]",
    ghost: "border-transparent bg-transparent text-fg/86 hover:bg-white/6 hover:text-fg",
    outline: "border-white/12 bg-transparent text-fg/90 hover:border-white/18 hover:bg-white/5",
  };
  const sizes = {
    sm: "h-9 px-3.5",
    md: "h-11 px-4",
    lg: "h-12 px-5 text-sm",
  };
  return <button className={cn(base, variants[variant], sizes[size], className)} {...props} />;
}
