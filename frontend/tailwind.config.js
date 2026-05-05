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
          primary: "#0b0d14",
          secondary: "#12141f",
          card: "#181b28",
          border: "#242736",
          hover: "#1e2133",
        },
        accent: {
          blue: "#4f8ef7",
          purple: "#8b5cf6",
        },
        green: {
          DEFAULT: "#22c55e",
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
        subtle: "#374151",
      },
    },
  },
  plugins: [],
};
