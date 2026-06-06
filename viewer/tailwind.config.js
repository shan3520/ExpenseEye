/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // ExpenseEye design tokens — "operator console" fintech, themeable via CSS
      // variables (dark by default, light under <html class="light">). The
      // surface/text/line tokens are full-value vars; chromatic tokens are RGB
      // channels so Tailwind's /opacity modifiers still work. See index.css.
      colors: {
        // elevation model: canvas -> panel -> raised -> hover
        canvas: "var(--canvas)",
        panel: {
          DEFAULT: "var(--panel)",
          raised: "var(--panel-raised)",
          hover: "var(--panel-hover)",
        },
        // translucent canvas for sticky headers (alpha baked in so it can theme)
        header: "var(--header)",
        // hairline borders (reads as drawn lines, not glass)
        line: {
          DEFAULT: "var(--line)",
          strong: "var(--line-strong)",
        },
        // text ramp
        txt: {
          DEFAULT: "var(--txt)",
          muted: "var(--txt-muted)",
          faint: "var(--txt-faint)",
        },
        // elevation tints — light overlays on dark, dark overlays on light
        tint: {
          1: "var(--tint-1)",
          2: "var(--tint-2)",
          3: "var(--tint-3)",
        },
        brand: {
          DEFAULT: "rgb(var(--brand-rgb) / <alpha-value>)", // amber-gold — trust / "watch this"
          light: "rgb(var(--brand-light-rgb) / <alpha-value>)",
        },
        accent: {
          DEFAULT: "rgb(var(--accent-rgb) / <alpha-value>)", // violet — tech / ML / forecast
          light: "rgb(var(--accent-light-rgb) / <alpha-value>)",
        },
        ink: {
          DEFAULT: "#0F172A",
          surface: "#1E293B",
          raised: "#334155",
        },
        success: "rgb(var(--success-rgb) / <alpha-value>)",
        danger: "rgb(var(--danger-rgb) / <alpha-value>)",
        warning: "rgb(var(--warning-rgb) / <alpha-value>)",
        info: "rgb(var(--info-rgb) / <alpha-value>)",
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
        panel: "var(--shadow-panel)",
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
