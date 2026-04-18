import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
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
      },
    },
  },
  plugins: [],
};

export default config;
