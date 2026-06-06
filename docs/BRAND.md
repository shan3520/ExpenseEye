# ExpenseEye — Brand Foundation

> Modern fintech identity. Derived with `ui-ux-pro-max` (fintech / dark-mode design system)
> and the `brandkit` skill. This is the source of truth for visual identity.

---

## 1. Strategy

| Field | Value |
|---|---|
| **Category** | Personal finance / expense analytics (fintech) |
| **Audience** | Individuals who want clarity on where their money goes |
| **Product function** | Imports bank statements, categorizes spending, and uses ML to flag overspending and recurring subscriptions |
| **Emotional promise** | "You're being watched over, not judged." Calm control over money. |
| **Personality** | Modern · sharp · trustworthy · quietly intelligent |
| **Core metaphor** | **The Eye** — vigilant insight. It sees patterns you miss. |
| **Trust level** | High — it handles financial data, so it must read as credible and secure |
| **Avoid** | Cute/playful piggy-bank clichés, rainbow gradients, generic SaaS purple glow, light "bank brochure" look |

**One-line positioning:** *ExpenseEye watches your spending so you don't have to.*

---

## 2. Voice & Tone

- **Clear, not clinical.** Plain language about money. No jargon, no shame.
- **Confident, not loud.** State insights directly: "You spent 32% more on dining this month."
- **Supportive, not preachy.** Flag, don't scold. "3 subscriptions you may have forgotten."

**Taglines (pick one):**
- "See where it goes."
- "Insight on every rupee."
- "Your spending, in focus."
- "Nothing slips past."

---

## 3. Color System — Modern Fintech (Dark)

Data-backed base: *gold trust + purple tech on deep navy* (Fintech/Crypto palette), tuned for an
analytics product that must show **good vs. bad spending** clearly.

### Core
| Role | Hex | Use |
|---|---|---|
| **Background** | `#0F172A` | App canvas (deep navy/slate) |
| **Surface** | `#1E293B` | Cards, panels |
| **Surface-2** | `#334155` | Raised elements, hover |
| **Brand / Primary** | `#F59E0B` | Logo, key accents (amber-gold = trust) |
| **Brand-light** | `#FBBF24` | Hover / highlight of primary |
| **CTA / Accent** | `#8B5CF6` | Primary buttons, links (violet = tech) |
| **Text** | `#F8FAFC` | Primary text |
| **Text-muted** | `#94A3B8` | Secondary text, labels |
| **Border** | `#334155` | Dividers, card borders |

### Semantic (critical for a spending app)
| Role | Hex | Meaning |
|---|---|---|
| **Success / under-budget** | `#10B981` | Savings, money in, on-track |
| **Danger / overspend** | `#EF4444` | Overspending alerts, money out |
| **Warning / watch** | `#F59E0B` | Subscriptions, approaching limit |
| **Info** | `#38BDF8` | Neutral insights |

> Note: brand amber doubles as the "warning" hue — fine, since "watch this" *is* the brand's job.

---

## 4. Typography

Modern fintech pairing. Display font gives a contemporary edge; body stays highly legible;
**a monospace is mandatory for figures** so currency columns align (tabular numbers).

| Role | Font | Why |
|---|---|---|
| **Display / Headings** | **Space Grotesk** | Geometric, slightly technical — modern fintech character |
| **Body / UI** | **Inter** | Workhorse, superb at small sizes (already your current font) |
| **Numbers / Data** | **IBM Plex Mono** | Tabular figures for aligned money columns & tables |

```css
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
```

*Data-backed alternative (more conservative/banking):* IBM Plex Sans for both heading & body.

---

## 5. Style & Effects

- **Style:** Glassmorphism on a dark canvas — frosted cards over a vibrant navy field.
  Best-for: financial dashboards. (Use sparingly; `backdrop-filter` is GPU-heavy.)
- **Effects:** backdrop blur 12–16px · 1px `rgba(255,255,255,0.08)` borders · soft z-depth shadows.
- **Motion:** 150–250ms color/opacity transitions. No layout-shifting scale on hover. Respect `prefers-reduced-motion`.
- **Anti-patterns to avoid:** light backgrounds, missing security cues, emoji icons (use Lucide/Heroicons SVG), text under 4.5:1 contrast.

---

## 6. Logo Concept — "The Eye"

The mark fuses **an eye** with a **financial signal**. Five directions, strongest first:

1. **Negative-space eye + pie** *(recommended)* — an almond eye whose **iris is a pie/donut chart**;
   the slice gap forms the pupil. Says "insight + breakdown of spending" in one mark.
2. **Eye = coin** — the iris is a subtly embossed coin; pupil is a small upward chart tick.
3. **Eye + radar** — concentric radar rings inside the eye; one ring is a spend-trend line. (Leans "monitoring".)
4. **Monogram E + eye** — the counter of a geometric `E` curves into an eyelid/lash; pupil dot as accent.
5. **Eye + waveform** — lower lash is a spending sparkline. (Most "data", least iconic.)

**Standards:** simple, scalable to a 16px favicon, single-accent (amber on navy), works as icon /
wordmark / badge. No clipart, no literal eyeball, no lightning bolts.

---

## 7. brandkit Image Prompt (paste into Midjourney / DALL·E / etc.)

```
Create a premium brand-kit overview image for "ExpenseEye".

Brand strategy:
- category: personal finance / expense analytics (fintech)
- audience: individuals seeking clarity on their spending
- personality: modern, sharp, trustworthy, quietly intelligent
- core metaphor: the eye — vigilant financial insight
- logo idea: an almond eye whose iris is a minimal pie/donut chart, the slice gap
  forming the pupil; fuses "insight" with "spending breakdown"

Layout:
3x3 grid on a dark charcoal-navy presentation canvas with strong gutters, clean
alignment, and refined negative space.

Panels:
- logo cover (large mark + "ExpenseEye" wordmark, sparse)
- logo construction (geometry of the eye/pie mark on a grid)
- digital application (dark dashboard fragment with frosted-glass cards)
- tagline ("See where it goes.")
- color system (swatches: deep navy #0F172A, amber #F59E0B, violet #8B5CF6, emerald #10B981, red #EF4444)
- typography (Space Grotesk + Inter + IBM Plex Mono specimen)
- physical application (matte card / badge)
- image direction (cinematic dark, subtle halftone, amber light accent)
- system detail (UI chips, a money figure in mono, an alert chip)

Visual mode: Dark Product / Operator — near-black panels, glowing UI chips, amber + violet accents.
Palette: deep navy base, amber primary accent, violet secondary, emerald/red semantic chips.
Style: premium, sparse, cinematic, intentional, brand-guidelines deck, no clutter, no copied real-world logos.
Typography: readable, minimal, strong hierarchy, no tiny fake text.
Logo: professional, symbolic, simple, ownable, repeated consistently across panels.
```

---

## 8. Next steps (optional)

- Wire these tokens into `viewer/tailwind.config.js` + `viewer/src/index.css`.
- Add an SVG favicon based on the eye/pie mark (currently missing — `index.html` references `/favicon.svg`).
- Generate the logo board with the prompt above, then vectorize the chosen mark.
