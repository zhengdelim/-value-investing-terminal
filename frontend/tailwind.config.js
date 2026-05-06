/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["DM Sans", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
      colors: {
        bg: {
          primary: "#161618",
          secondary: "#1c1c1e",
          card: "#222224",
          border: "#2e2e30",
          hover: "#2a2a2c",
        },
        accent: {
          blue: "#22c55e",
          purple: "#10b981",
        },
        green: {
          DEFAULT: "#4ade80",
          dim: "#166534",
          bg: "#052e16",
        },
        yellow: {
          DEFAULT: "#f59e0b",
          dim: "#854d0e",
          bg: "#1c0e00",
        },
        red: {
          DEFAULT: "#ef4444",
          dim: "#991b1b",
          bg: "#1a0000",
        },
        muted: "#6b7280",
        subtle: "#3f3f41",
      },
    },
  },
  plugins: [],
};
