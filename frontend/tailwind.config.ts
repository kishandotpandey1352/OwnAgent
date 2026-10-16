import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}", "./types/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#0b1020",
        panel: "#11182d",
        panelSoft: "#16213a",
        accent: {
          50: "#ecfeff",
          100: "#cffafe",
          200: "#a5f3fc",
          300: "#67e8f9",
          400: "#22d3ee",
          500: "#06b6d4",
          600: "#0891b2",
          700: "#0e7490",
        },
        ink: {
          100: "#e5eefc",
          200: "#c7d7f5",
          300: "#9fb3e8",
          400: "#6e88cf",
          500: "#4760ad",
          600: "#31437d",
          700: "#1d294f",
        },
      },
      boxShadow: {
        halo: "0 0 0 1px rgba(255,255,255,0.08), 0 24px 80px rgba(0,0,0,0.42)",
      },
      backgroundImage: {
        "grid-faint": "linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)",
      },
      backgroundSize: {
        grid: "32px 32px",
      },
    },
  },
  plugins: [],
};

export default config;