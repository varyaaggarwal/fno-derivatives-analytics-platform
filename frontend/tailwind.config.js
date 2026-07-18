/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#000000",
        surface: "#0A0A0B",
        surface2: "#151517",
        surface3: "#1C1C1F",
        border: "#242428",
        text: "#EDEDEF",
        muted: "#8B8B92",
        bullish: "#34D399",
        bearish: "#F87171",
        accent: "#6366F1",
        warn: "#FBBF24",
      },
      fontFamily: {
        display: ["var(--font-display)", "sans-serif"],
        body: ["var(--font-body)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      borderRadius: {
        card: "14px",
        pill: "9999px",
      },
    },
  },
  plugins: [],
};
