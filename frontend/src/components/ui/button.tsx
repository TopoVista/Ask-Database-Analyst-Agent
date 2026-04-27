import { cn } from "@/lib/utils";

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "secondary" | "ghost" | "outline";
  size?: "sm" | "md" | "lg";
};

export function Button({ className, variant = "default", size = "md", ...props }: Props) {
  const base =
    "inline-flex items-center justify-center rounded-xl font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:pointer-events-none disabled:opacity-50";
  const variants = {
    default: "bg-accent text-accent-fg shadow-glow hover:brightness-110",
    secondary: "bg-white/8 text-fg hover:bg-white/12 border border-white/10",
    ghost: "bg-transparent text-fg hover:bg-white/8",
    outline: "border border-white/14 bg-transparent text-fg hover:bg-white/8",
  };
  const sizes = {
    sm: "h-8 px-3 text-sm",
    md: "h-10 px-4 text-sm",
    lg: "h-12 px-5 text-base",
  };
  return <button className={cn(base, variants[variant], sizes[size], className)} {...props} />;
}

