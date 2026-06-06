# ExpenseEye Design System

## Color

### Canvas
- Canvas: #080d18 (dark background)

### Panel
- Panel: #0e1626 (default panel background)
- Panel raised: #141f33 (elevated panel state)
- Panel hover: #1a2740 (hover state)

### Line (Borders)
- Line: rgba(148, 163, 184, 0.10) (hairline borders)
- Line strong: rgba(148, 163, 184, 0.20) (stronger borders)

### Text
- Text default: #e8edf6 (primary text)
- Text muted: #94a3b8 (secondary text)
- Text faint: #5d6b85 (tertiary text/disabled)

### Brand
- Brand default: #F59E0B (amber-gold - trust/watch this)
- Brand light: #FBBF24

### Accent
- Accent default: #8B5CF6 (violet - tech/ML/forecast)
- Accent light: #A78BFA

### Ink
- Ink default: #0F172A (primary ink color)
- Ink surface: #1E293B (surface level)
- Ink raised: #334155 (raised surface)

### Semantic Colors
- Success: #10B981
- Danger: #EF4444
- Warning: #F59E0B
- Info: #38BDF8

## Typography

### Font Families
- Display: Manrope, system-ui, sans-serif
- Sans: Manrope, system-ui, Avenir, Helvetica, Arial, sans-serif
- Mono: IBM Plex Mono, ui-monospace, SFMono-Regular, monospace

### Letter Spacing
- Eyebrow: 0.18em

## Shadows

### Panel Shadow
- Panel: 0 1px 0 0 rgba(255,255,255,0.02) inset, 0 12px 32px -12px rgba(0,0,0,0.6)

## Animation

### Keyframes
- Fade rise: 
  - 0%: opacity 0, transform translateY(8px)
  - 100%: opacity 1, transform translateY(0)

### Animation
- Fade rise: fade-rise 0.5s cubic-bezier(0.16, 1, 0.3, 1) both

## Components

### Panel
- Base: rounded-lg border border-line bg-panel shadow-panel
- States: default, hover, active, disabled

### Inset
- Base: rounded-md border border-line bg-white/[0.015]

### Eyebrow
- Base: font-mono text-[11px] uppercase tracking-eyebrow text-txt-faint

### KPI Label
- Base: flex items-center gap-2 text-[12px] font-medium text-txt-muted

### KPI Value
- Base: mt-2 font-mono text-2xl font-semibold tracking-tight text-txt

### Data Table
- Base: min-w-full text-sm
- Header: px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-txt-faint
- Row: border-t border-line transition-colors hover:bg-white/[0.025]
- Cell: px-4 py-3 whitespace-nowrap text-txt-muted

### Tag
- Base: inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] font-medium
- ML Tag: inline-flex items-center rounded border border-accent/30 bg-accent/10 px-1.5 py-px font-mono text-[10px] font-semibold uppercase tracking-wider text-accent-light

### Button Primary
- Base: inline-flex items-center justify-center gap-2 rounded-md bg-brand px-5 py-2.5 text-sm font-semibold text-ink transition-colors hover:bg-brand-light disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer

### Button Ghost
- Base: inline-flex items-center justify-center gap-2 rounded-md border border-line-strong bg-white/[0.03] px-4 py-2 text-sm font-medium text-txt-muted transition-colors hover:text-txt hover:bg-white/[0.06] cursor-pointer

### State Block
- Base: rounded-md border border-line bg-white/[0.015] px-6 py-10 text-center

## Motion

### Transition Duration
- Standard: 150–250 ms for most transitions
- Purpose: conveys state change, feedback, loading, reveal

### Reduced Motion
- When prefers-reduced-motion: reduce
- Scroll behavior: auto
- Animation duration: 0.01ms !important
- Animation iteration count: 1 !important
- Transition duration: 0.01ms !important

## Accessibility

### WCAG Compliance
- Target: WCAG 2.1 AA
- Color contrast: minimum 4.5:1 for body text, 3:1 for large text
- Focus visible: clear focus indicators
- Reduced motion: respected via media query

### Color Blindness
- Palette tested for deuteranopia, protanopia, tritanopia
- Information conveyed through multiple channels (color + icon + text)

## Layout

### Responsive Behavior
- Structural changes: sidebar collapse, responsive tables, breakpoint-driven columns
- Grid system: repeat(auto-fit, minmax(280px, 1fr)) for fluid grids
- Spacing: varied for rhythm and hierarchy

### Z-index Scale
- Dropdown: 1000
- Sticky: 1100
- Modal backdrop: 1200
- Modal: 1300
- Toast: 1400
- Tooltip: 1500

## Component Vocabulary

### Interactive Components
All interactive components include states: default, hover, focus, active, disabled, loading, error

### Loading States
- Skeleton states preferred over spinners in content
- Spinners only for full-page loads

### Empty States
- Educational: teach the interface, not just "nothing here"
- Include illustration or icon when appropriate
- Provide clear next steps

### Affordances
- Consistent button shapes
- Consistent form-control vocabulary
- Consistent icon style