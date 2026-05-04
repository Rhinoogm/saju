import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "media",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--color-background)",
        foreground: "var(--color-foreground)",
        surface: "var(--color-surface)",
        "surface-muted": "var(--color-surface-muted)",
        border: "var(--color-border)",
        sage: "#5A6B5D",
        terracotta: "#C57B57",
        "warm-gray": "#F7F6F3",
        "deep-gray": "#1E1E1E",
        cream: "#f7f1e6",
        cloud: "#f2f5f8",
        ink: "#24211f",
        berry: "#7d3f5f",
        coral: "#dd6654",
        mint: "#2f9d8c",
        honey: "#f1be4d",
      },
      boxShadow: {
        soft: "0 18px 60px rgba(38, 34, 29, 0.10)",
        ritual: "0 18px 44px rgba(31, 29, 25, 0.08)",
        "ritual-dark": "0 18px 44px rgba(0, 0, 0, 0.32)",
      },
      fontFamily: {
        sans: [
          "Pretendard",
          "-apple-system",
          "BlinkMacSystemFont",
          "system-ui",
          "Segoe UI",
          "sans-serif",
        ],
        serif: [
          "KoPub Batang",
          "MapoAemin",
          "Noto Serif KR",
          "Apple SD Gothic Neo",
          "serif",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
