/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // ExpenseEye design tokens — "operator console" fintech. See docs/BRAND.md
      colors: {
        // elevation model: canvas (darkest) -> panel -> raised -> hover
        canvas: "#080d18",
        panel: {
          DEFAULT: "#0e1626",
          raised: "#141f33",
          hover: "#1a2740",
        },
        // hairline borders (cool slate, low alpha — reads as drawn lines, not glass)
        line: {
          DEFAULT: "rgba(148, 163, 184, 0.10)",
          strong: "rgba(148, 163, 184, 0.20)",
        },
        // text ramp — slightly off-white body avoids the harsh pure-white AI look
        txt: {
          DEFAULT: "#e8edf6",
          muted: "#94a3b8",
          faint: "#76829c", // ≥4.5:1 on panel/canvas (WCAG AA for small text)
        },
        brand: {
          DEFAULT: "#F59E0B", // amber-gold — trust / "watch this"
          light: "#FBBF24",
        },
        accent: {
          DEFAULT: "#8B5CF6", // violet — tech / ML / forecast
          light: "#A78BFA",
        },
        ink: {
          DEFAULT: "#0F172A",
          surface: "#1E293B",
          raised: "#334155",
        },
        success: "#10B981",
        danger: "#EF4444",
        warning: "#F59E0B",
        info: "#38BDF8",
      },
      fontFamily: {
        display: ["Manrope", "system-ui", "sans-serif"],
        sans: ["Manrope", "system-ui", "Avenir", "Helvetica", "Arial", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      letterSpacing: {
        eyebrow: "0.18em",
      },
      boxShadow: {
        panel: "0 1px 0 0 rgba(255,255,255,0.02) inset, 0 12px 32px -12px rgba(0,0,0,0.6)",
      },
      keyframes: {
        "fade-rise": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-rise": "fade-rise 0.5s cubic-bezier(0.16, 1, 0.3, 1) both",
      },
    },
  },
  plugins: [],
}
