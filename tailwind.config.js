/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.html",
    "./index.html",
    "./cgv.html",
    "./confidentialite.html",
    "./mentions-legales.html",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink:    "#0f0f0f",
        muted:  "#6b7280",
        border: "#e5e7eb",
        card:   "#ffffff",
        surface:"#fafaf9",
        "surface-hi":  "#fff7ed",
        "surface-mid": "#ffedd5",
        primary:"#f97316",
        "primary-dk":  "#ea580c",
        "primary-lt":  "#fff7ed",
        success:"#16a34a",
        danger: "#dc2626",
        "d-bg":   "#0f0f0f",
        "d-card": "#1a1a1a",
        "d-border":"#2a2a2a",
        "d-muted": "#71717a",
      },
      fontFamily: {
        sans:    ["Inter","sans-serif"],
        display: ["Space Grotesk","sans-serif"],
      },
      borderRadius: { lg:"12px", xl:"16px", "2xl":"20px" },
    }
  },
  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/container-queries"),
  ],
}
