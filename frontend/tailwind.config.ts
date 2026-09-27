import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "hsl(var(--bg))",
        fg: "hsl(var(--fg))",
        panel: "hsl(var(--panel))",
        panelFg: "hsl(var(--panel-fg))",
        border: "hsl(var(--border))",
        accent: {
          DEFAULT: "hsl(var(--accent))",
          fg: "hsl(var(--accent-fg))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          fg: "hsl(var(--muted-fg))",
        },
        success: "#45d483",
        warning: "#f5b942",
        danger: "#ff6b6b",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      boxShadow: {
        glow: "0 1px 2px rgba(0,0,0,0.24)",
      },
    },
  },
  plugins: [],
};

export default config;
