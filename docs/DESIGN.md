# ExpenseEye Design System — "Vault Terminal"

ExpenseEye is styled as an **instrument-grade dark console**: a private terminal
pointed at your own money. Deep OLED canvas, machined graphite panels, a hairline
ledger grid, every figure set in mono. The guiding rule is that **color is signal,
never decoration** — a hue only appears when it carries meaning.

The system is fully themeable through CSS variables (dark by default, light under
`<html class="light">`). Surface/text/line tokens are full color values; chromatic
tokens are stored as RGB channels so Tailwind's `/opacity` modifiers still work.
See `viewer/src/index.css` and `viewer/tailwind.config.js` for the source of truth.

## Signal Philosophy

| Hue | Meaning |
|-----|---------|
| Phosphor green (brand) | live, positive, primary action / "go" |
| Cyan (accent) | ML, forecast, technical readouts |
| Amber (warning) | caution |
| Rose (danger) | alert, anomaly, negative |
| Sky (info) | secondary information |

Positive money and the primary signal share the same phosphor green — in a terminal,
green simply means "good / active". Red means bad, amber means watch.

## Color — Dark (default)

### Surfaces & text
- Canvas: `#05080e` (deep OLED, faint blue-green undertone)
- Panel: `#0a0f18`
- Panel raised: `#0f1623`
- Panel hover: `#161f30`
- Text default: `#e9eff5`
- Text muted: `#93a1b5`
- Text faint: `#74809a` (≥4.5:1 on panel/canvas)

### Hairlines & textures
- Line: `rgba(140, 162, 190, 0.11)`
- Line strong: `rgba(140, 162, 190, 0.22)`
- Header fill (sticky, translucent): `rgba(5, 8, 14, 0.82)`
- Ledger grid line: `rgba(140, 162, 190, 0.028)` (48px graph-paper grid on the canvas)
- Scanline: `rgba(140, 200, 180, 0.022)` (static CRT veil, fixed + `pointer-events-none`)

### Signal colors
- Brand (phosphor green): `#34d399` / light `#6ee7b7`
- Accent (cyan): `#22d3ee` / light `#67e8f9`
- Success: `#34d399` (= brand green)
- Danger (rose): `#fb7185`
- Warning (amber): `#fbbf24`
- Info (sky): `#38bdf8`
- Focus ring: `#34d399`
- On-brand (text on green buttons): `#03130c`

## Color — Light instrument

Cool paper with deep ink and the same signal hues, deepened so they stay legible
and high-contrast on white.

- Canvas: `#f1f4f9` · Panel: `#ffffff` · Panel raised: `#f2f5fa` · Panel hover: `#e7edf5`
- Text default: `#0c1320` · muted: `#475569` · faint: `#5a6577` (≥4.5:1 on white)
- Brand: `#047857` (emerald-700) / light `#059669`
- Accent: `#0e7490` (cyan-700) / light `#0891b2`
- Danger: `#e11d48` (rose-600) · Warning: `#b45309` (amber-700) · Info: `#0284c7` (sky-600)
- Focus ring: `#047857`

## Typography

### Font families
- Display: Manrope, system-ui, sans-serif
- Sans: Manrope, system-ui, Avenir, Helvetica, Arial, sans-serif
- Mono: IBM Plex Mono, ui-monospace, SFMono-Regular, monospace

All numeric figures use mono with `tabular-nums` so currency columns align to the
digit. Mono/uppercase is also the voice of instrument legends (KPI labels, the
session tape, table headers).

### Type scale (rem, respects user zoom)
- micro: 0.6875rem (11px) — eyebrows, tags, table headers, tape cells
- caption: 0.75rem (12px) — captions, fine print
- data: 0.8125rem (13px) — dense table / data rows
- subhead: 1.125rem (18px) — module / section titles

### Letter spacing
- Eyebrow: 0.18em

## Shadows

- Panel: `0 1px 0 0 rgba(255,255,255,0.025) inset, 0 14px 34px -14px rgba(0,4,10,0.74)`
  — a machined edge highlight over a deep well (not a generic drop shadow).

## Components

### Panel
- Base: `rounded-lg border border-line bg-panel shadow-panel`
- One module = one flat panel. No glass, no stacked card-in-card.

### Inset
- Base: `rounded-md border border-line bg-tint-1` (one quieter level for sub-content)

### Eyebrow
- Base: `font-mono text-micro uppercase tracking-eyebrow text-txt-faint`

### Session tape (signature)
- A slim sticky telemetry strip at the top of the console: live indicator, session
  handle, ticking uptime, the module currently in view, and a standing
  `LOCAL · NOTHING STORED` assurance.
- Cells: `flex items-center gap-2 whitespace-nowrap px-3.5 font-mono text-micro uppercase tracking-wider`, hairline-separated (`border-l border-line`).
- Sticky on desktop (`lg:sticky lg:top-0`); scrolls away on mobile to clear the mobile top bar.

### Live dot
- Base: `.live-dot` — phosphor-green dot with a slow expanding `live-pulse` ring
  (2.4s). Collapses to a steady dot under reduced motion.

### Module rail
- Base: `.module-rail` — a short phosphor tick before each module header.

### KPI label / value
- Label: `font-mono text-micro font-medium uppercase tracking-wider text-txt-muted` (instrument legend)
- Value: `mt-2.5 font-mono text-[1.7rem] font-semibold leading-none tracking-tight tabular-nums text-txt`
- Headline values roll up from zero on mount via the `Counter` component (see Motion).

### Data table
- Base: `min-w-full text-sm`
- Header: `px-4 py-2.5 text-micro font-semibold uppercase tracking-wider text-txt-faint`
- Row: `border-t border-line transition-colors hover:bg-tint-2`
- Cell: `px-4 py-3 whitespace-nowrap text-txt-muted`

### Tag
- Base: `inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-micro font-medium`
- ML tag: `border border-accent/30 bg-accent/10 ... text-accent-light` (cyan)

### Button primary
- Base: `inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-brand px-5 py-2.5 text-sm font-semibold text-[color:var(--on-brand)] transition-colors hover:bg-brand-light disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer`

### Button ghost
- Base: `inline-flex min-h-11 items-center justify-center gap-2 rounded-md border border-line-strong bg-tint-2 px-4 py-2.5 text-sm font-medium text-txt-muted transition-colors hover:text-txt hover:bg-tint-3 cursor-pointer`

### State block
- Base: `rounded-md border border-line bg-tint-1 px-6 py-10 text-center`

### Console preview (landing)
- A non-interactive, decorative mini-instrument in the landing hero's right column
  (`aria-hidden`, `pointer-events-none`, `select-none`). Composed from the real
  primitives (session-tape header, `.kpi-label`/`.kpi-value` legends, the cyan ML
  tag, a phosphor/cyan cash-flow bar strip, a recurring-subscriptions slice) so it
  reads as a faithful preview of the board, not a div-based fake screenshot. All
  figures are illustrative mocks. Pure tokens, so it tracks both themes; stacks
  below the hero copy below `lg`.

### Processing terminal (boot bridge)
- The full-viewport hand-off between a successful upload and the dashboard
  (`ProcessingTerminal` in `App.tsx`). A tape-style header (`Initializing` /
  `Local session`) over a `.panel` that reveals mono boot logs sequentially
  (`[SYSTEM]` / `[PARSER]` / `[ML]` / `[READY]`) across ~2.5s, then reveals the
  board. Tags carry the signal color (cyan for the ML steps, phosphor green for
  `[READY]`). The backend has already parsed and classified by the time it mounts,
  so it replays finished work rather than padding a fake delay (see Motion).

### Terminal alert (upload error)
- The upload failure state is a terminal readout, not a generic red box: a
  `[SYS_ERR]` tag in the danger signal followed by the message in high-contrast
  `text-txt`, mono, `rounded-md border border-danger/30 bg-danger/[0.07]`. The
  shared `ErrorState` (dashboard module fetch errors) keeps its icon + message
  form; this terminal variant is specific to the intake panel.

### Radius ladder
- sm 6px (tags) · md/DEFAULT 8px (buttons, inputs, insets) · lg 12px (panels) · xl 16px (large containers)

## Motion

Motion is instrument-grade: minimal, mechanical, and always motivated (feedback or
state change), never decorative.

### Count-up readouts
- `Counter` rolls KPI figures from zero to value on mount (easeOutExpo, ~900ms),
  the "data just landed" feedback. Driven by a single `requestAnimationFrame`
  loop, not per-frame React churn.

### Live pulse
- `live-pulse` keyframe: a phosphor ring that expands and fades (2.4s loop).

### Fade rise
- `fade-rise`: opacity 0 → 1, translateY(8px) → 0, `0.5s cubic-bezier(0.16, 1, 0.3, 1)`.
  Also used to stagger the landing hero blocks and the trust section in on load.

### Boot sequence
- The Processing terminal reveals one log line at a time (~360ms apart, ~2.5s
  total) via `fade-rise`, with a blinking caret on the active line. This is a
  reveal that narrates a real state transition (upload → parsed board), not
  decoration. It is the one place motion intentionally paces the user.

### Hover micro-interactions
- Landing capability items: on hover, a subtle `translate-x` shift, a phosphor
  `drop-shadow` glow on the icon (the same treatment as the active sidebar nav),
  and the mono note brightening faint → muted. `cursor-default` (they are legends,
  not links).
- Panels lift 2px with a deeper well on hover; primary/ghost buttons press 1px on
  `:active`.

### Scanline
- Static (no animation) so it never costs a repaint and never fights reduced motion.

### Reduced motion (`prefers-reduced-motion: reduce`)
- Scroll behavior → auto; animation/transition durations clamped to ~0.
- `Counter` snaps directly to its final value (via `useReducedMotion`).
- Live pulse collapses to a steady dot.
- The Processing terminal renders its full log at once and hands off in ~0.5s; the
  per-line reveal and caret are suppressed. Hover shifts/glows resolve instantly.

## Accessibility

### WCAG compliance
- Target: WCAG 2.1 AA — minimum 4.5:1 for body text, 3:1 for large text.
- One focus convention everywhere: `2px solid var(--ring)` with `2px` offset.
- Reduced motion respected via media query and `useReducedMotion`.

### Color blindness
- Palette chosen for deuteranopia / protanopia / tritanopia legibility.
- Information is conveyed through multiple channels (color + icon + text), never color alone.

## Layout

### Landing
- Two-column hero on `lg` (`grid lg:grid-cols-2`, `items-center`): the left column
  carries the headline, description, the capability strip, and the upload
  instrument; the right column carries the decorative Console preview. Collapses to
  a single stacked column below `lg` (preview drops under the upload, capped width).
- Below the hero, a trust block: a hairline-celled open-source signal strip
  (`Open source / Self-hostable / No account / No data kept` plus a link to the
  source) and a "Private by architecture" section of three hairline-divided
  guarantee columns (no boxed cards; vertical rules on `sm+`, horizontal rules when
  stacked).
- On a successful upload the landing hands off to the Processing terminal boot
  bridge, which holds until its sequence finishes before the dashboard shell mounts.

### Shell
- Desktop: sticky left sidebar (module rail + theme + source + end session) beside a
  scrolling main column topped by the sticky session tape.
- Mobile: sticky top bar with a horizontal module nav; the tape scrolls inline.

### Responsive behavior
- Asymmetric / multi-column layouts collapse to single column with `w-full` below `md`.
- Tables scroll horizontally on narrow viewports.
- Use `min-h-screen` / `min-h-[100dvh]` for full-height regions, never `h-screen` content traps.

### Z-index
- Reserved for systemic layers only: sticky tape (z-10), sidebar / mobile header (z-20),
  scanline veil (z-index -1, behind all content).

## Component Vocabulary

- Every interactive component carries states: default, hover, focus, active, disabled, loading, error.
- Loading: skeletons preferred in content; spinners only for module/page loads.
- Empty states: educational — name what's missing and the next step.
- Affordances: consistent button shapes, form-control vocabulary, and icon style (Lucide, light strokes).
