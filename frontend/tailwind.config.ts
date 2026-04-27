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
        glow: "0 0 0 1px rgba(255,255,255,0.06), 0 18px 60px rgba(0,0,0,0.45)",
      },
      backgroundImage: {
        "aurora-grid":
          "radial-gradient(circle at top left, rgba(255, 183, 77, 0.16), transparent 28%), radial-gradient(circle at top right, rgba(76, 201, 240, 0.12), transparent 30%), linear-gradient(180deg, rgba(10, 13, 22, 0.95), rgba(7, 10, 15, 1))",
      },
    },
  },
  plugins: [],
};

export default config;

