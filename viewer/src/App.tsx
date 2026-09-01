import { useState, useEffect, useRef, useLayoutEffect, useCallback } from 'react';
import type { ComponentType } from 'react';
// Phosphor Light across the whole app now — one icon language, finer line weight.
import {
  IconContext,
  TrendUp,
  TreeStructure,
  Fingerprint,
  ArrowsClockwise,
  ShieldCheck,
  Cpu,
  Lock,
  TrendDown,
  Tag,
  Warning,
  CalendarDots,
  ChartBar,
  SignOut,
} from '@phosphor-icons/react';
import { FileUpload } from '@/components/FileUpload';
import { warmUpBackend, deleteSession, sessionExists } from '@/lib/api';
import { SessionTape } from '@/components/SessionTape';
import { SubscriptionsTable } from '@/components/SubscriptionsTable';
import { OverspendingAnalysis } from '@/components/OverspendingAnalysis';
import { CashFlowForecast } from '@/components/CashFlowForecast';
import { TransactionCategories } from '@/components/TransactionCategories';
import { AnomalyDetection } from '@/components/AnomalyDetection';
import { Reconciliation } from '@/components/Reconciliation';
import { ThemeToggle } from '@/components/ThemeToggle';
import { useReducedMotion } from '@/lib/useReducedMotion';
import { useMediaQuery } from '@/lib/useMediaQuery';
import { useSmoothScroll } from '@/lib/useSmoothScroll';
import { useMagneticTilt } from '@/lib/useMagneticTilt';
import { gsap, ScrollTrigger, STANDARD_EASE } from '@/lib/motion';
import { cn, shortId } from '@/lib/utils';

/** GitHub mark — inlined as a brand glyph so it stays exact across themes. */
function GithubMark({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}

/** ExpenseEye logo mark — eye whose iris is a pie/donut chart. Recolored to the
    Vault Terminal signal palette: phosphor-green iris ring, cyan data wedge. */
function EyeMark({ className = 'w-6 h-6' }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" className={className} aria-hidden="true">
      <path
        d="M3 16C6.5 9.5 11 6.5 16 6.5C21 6.5 25.5 9.5 29 16C25.5 22.5 21 25.5 16 25.5C11 25.5 6.5 22.5 3 16Z"
        stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinejoin="round"
      />
      <circle cx="16" cy="16" r="5.6" fill="none" stroke="var(--brand)" strokeWidth="3.2" />
      <path d="M16 16 L16 10.4 A5.6 5.6 0 0 1 20.85 18.8 Z" fill="var(--accent)" />
      <circle cx="16" cy="16" r="2.1" fill="currentColor" />
    </svg>
  );
}

interface ModuleDef {
  id: string;
  nav: string;
  title: string;
  desc: string;
  icon: ComponentType<{ className?: string }>;
  ml?: boolean;
  /** Column span on the lg bento grid (5-col). Tiles tile two-up then full. */
  span: string;
  render: (sessionId: string) => React.ReactNode;
}

// Asymmetrical bento: forecast(3)+categories(2) | anomalies(2)+subscriptions(3) |
// overspending(5). Each row sums to 5 so it tiles cleanly; widths alternate so no
// two rows share a rhythm, and `items-start` lets every tile keep its own height.
const MODULES: ModuleDef[] = [
  {
    id: 'forecast',
    nav: 'Forecast',
    title: 'Cash-Flow Forecast',
    desc: 'Projected spend for the coming month, with a back-tested error margin.',
    icon: TrendUp,
    ml: true,
    span: 'lg:col-span-3',
    render: (s) => <CashFlowForecast sessionId={s} />,
  },
  {
    id: 'categories',
    nav: 'Categories',
    title: 'Smart Categorization',
    desc: 'Every transaction sorted by a trained model, with a rule-based fallback.',
    icon: Tag,
    ml: true,
    span: 'lg:col-span-2',
    render: (s) => <TransactionCategories sessionId={s} />,
  },
  {
    id: 'anomalies',
    nav: 'Anomalies',
    title: 'Anomaly Detection',
    desc: 'Charges that fall outside your normal pattern, ranked by how far they deviate.',
    icon: Warning,
    ml: true,
    span: 'lg:col-span-2',
    render: (s) => <AnomalyDetection sessionId={s} />,
  },
  {
    id: 'subscriptions',
    nav: 'Subscriptions',
    title: 'Recurring Subscriptions',
    desc: 'Regular payments detected from the cadence of your statement.',
    icon: CalendarDots,
    span: 'lg:col-span-3',
    render: (s) => <SubscriptionsTable sessionId={s} />,
  },
  {
    id: 'reconciliation',
    nav: 'Reconciliation',
    title: 'Recurring Reconciliation',
    desc: 'Every charge expected to recur, matched against what actually landed — with the exceptions it could not resolve.',
    icon: ArrowsClockwise,
    span: 'lg:col-span-5',
    render: (s) => <Reconciliation sessionId={s} />,
  },
  {
    id: 'overspending',
    nav: 'Overspending',
    title: 'Overspending Analysis',
    desc: 'Months that ran hot against the baseline of every prior month.',
    icon: ChartBar,
    span: 'lg:col-span-5',
    render: (s) => <OverspendingAnalysis sessionId={s} />,
  },
];

const REPO_URL = 'https://github.com/shan3520/expenseeye';

// Where the active session id is parked so it survives a page reload. sessionStorage
// -- not localStorage -- on purpose: it is scoped to the tab and dies with it, which
// is what the "session-scoped, auto-deleted" promise on screen says happens.
const SESSION_KEY = 'expenseeye.session';

/** Module header: icon + title, no scaffolding numbers or eyebrows. */
function ModuleHeader({ mod }: { mod: ModuleDef }) {
  const Icon = mod.icon;
  return (
    <header className="mb-5">
      <div className="flex items-center gap-2.5">
        <span className="module-rail h-5" aria-hidden="true" />
        <Icon className="h-5 w-5 text-txt-muted" aria-hidden="true" />
        <h2 className="font-display text-subhead font-semibold tracking-tight text-txt">
          {mod.title}
        </h2>
        {mod.ml && (
          <span className="tag-ml drop-shadow-[0_0_6px_rgb(var(--accent-rgb)/_0.4)]">ML</span>
        )}
      </div>
      <p className="mt-2 max-w-[68ch] pl-[14px] text-sm leading-relaxed text-txt-muted text-pretty">{mod.desc}</p>
    </header>
  );
}

/** One bento tile: header + panel. Entrance is handled by the grid's GSAP
    stagger (data-module-card); on desktop pointers the card tilts toward the
    cursor (perspective on the section, rotation on the tray). */
function ModuleCard({ mod, sessionId }: { mod: ModuleDef; sessionId: string }) {
  const tiltRef = useMagneticTilt<HTMLElement>(3);
  return (
    <section
      ref={tiltRef}
      id={mod.id}
      data-module-card
      style={{ perspective: '800px' }}
      className={cn('scroll-mt-28 lg:scroll-mt-24', mod.span)}
    >
      <ModuleHeader mod={mod} />
      {/* Double-bezel: an outer tray (subtle bg + hairline) cradles the data
          panel, whose own border + inset top-highlight + concentric radius make
          it read as a machined plate seated in the tray. The tray is the tilt
          target so the label above stays put while the card leans. */}
      <div
        data-tilt-target
        className="rounded-2xl border border-line bg-tint-1 p-1.5"
      >
        <div className="panel rounded-[0.875rem] p-5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)] sm:p-6">
          {mod.render(sessionId)}
        </div>
      </div>
    </section>
  );
}

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  // True while a stored session id is being checked against the server. Starts
  // true only when there is something to restore, so a first-time visitor goes
  // straight to the landing page with no flash.
  const [restoring, setRestoring] = useState<boolean>(() => {
    try { return !!sessionStorage.getItem(SESSION_KEY); } catch { return false; }
  });
  // `booting` gates the upload→dashboard bridge: once an upload succeeds we hold
  // on the ProcessingTerminal until its sequence finishes, then reveal the board.
  const [booting, setBooting] = useState(false);
  const [activeId, setActiveId] = useState<string>(MODULES[0].id);
  const observerRef = useRef<IntersectionObserver | null>(null);
  // Which modules are currently inside the scroll-spy band. IntersectionObserver
  // hands the callback ONLY the entries whose intersection changed, so the set
  // has to be accumulated across calls -- picking a winner from a single
  // callback's slice leaves the highlight stale.
  const visibleRef = useRef<Set<string>>(new Set());
  // Read inside the observer callback, which closes over its first render.
  const activeIdRef = useRef<string>(MODULES[0].id);
  // A nav click owns the selection until the smooth scroll settles; without
  // this the observer fires mid-scroll and overwrites the user's choice.
  const navLockRef = useRef<number>(0);

  useEffect(() => { activeIdRef.current = activeId; }, [activeId]);

  // Motion gating. Lenis smooth scroll only on a desktop pointer, a non-mobile
  // viewport, and when the user hasn't asked for reduced motion — touch and
  // reduced-motion get native scroll.
  const reduce = useReducedMotion();
  const pointerFine = useMediaQuery('(pointer: fine)');
  const notMobile = useMediaQuery('(min-width: 769px)');
  useSmoothScroll(pointerFine && notMobile && !reduce);

  // Kick off the backend cold-start on mount so it is likely warm by the time
  // the user submits a statement (P0-1). Non-blocking; failures are ignored.
  useEffect(() => { warmUpBackend(); }, []);

  // Dashboard bento entrance: stagger the module cards in once per session.
  const gridRef = useRef<HTMLDivElement>(null);
  const animatedSession = useRef<string | null>(null);

  // Restore an in-flight session across a reload. The id previously lived only
  // in component state, so any refresh -- or a stray back/forward -- dropped the
  // user on the landing page while their parsed statement was still sitting on
  // the server, now unreachable, until its TTL expired.
  useEffect(() => {
    let stored: string | null = null;
    try { stored = sessionStorage.getItem(SESSION_KEY); } catch { stored = null; }
    if (!stored) return;

    let cancelled = false;
    (async () => {
      const alive = await sessionExists(stored);
      if (cancelled) return;
      if (alive) {
        setSessionId(stored);            // straight to the board, no boot replay
      } else {
        try { sessionStorage.removeItem(SESSION_KEY); } catch { /* ignore */ }
      }
      setRestoring(false);
    })();
    return () => { cancelled = true; };
  }, []);

  const handleUploadSuccess = (id: string) => {
    try { sessionStorage.setItem(SESSION_KEY, id); } catch { /* ignore */ }
    setSessionId(id);
    setBooting(true);
  };

  // A nav click selects its module outright. The plain `href="#id"` jump left
  // the choice to the observer, which then resolved the row to the other card.
  const handleNavClick = useCallback((e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    const el = document.getElementById(id);
    if (!el) return;                       // no target: let the browser try
    e.preventDefault();
    setActiveId(id);
    activeIdRef.current = id;
    navLockRef.current = Date.now() + 900;
    el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
    history.replaceState(null, '', `#${id}`);
  }, [reduce]);

  const handleLogout = () => {
    // Delete the session's server-side data on exit, backing the UI's
    // "deleted on exit" promise (P0-4), then clear local state.
    if (sessionId) deleteSession(sessionId);
    try { sessionStorage.removeItem(SESSION_KEY); } catch { /* ignore */ }
    setSessionId(null);
    setBooting(false);
    setActiveId(MODULES[0].id);
  };

  // (5) Module cards entrance — left-to-right, top-to-bottom (DOM order), once
  // per session. useLayoutEffect sets the hidden start state before paint so the
  // cards never flash in at full opacity first. Reduced motion shows them as-is.
  useLayoutEffect(() => {
    if (!sessionId || booting) return;
    if (animatedSession.current === sessionId) return;
    const grid = gridRef.current;
    if (!grid) return;
    animatedSession.current = sessionId;
    const cards = grid.querySelectorAll('[data-module-card]');
    if (reduce || !cards.length) return;
    const ctx = gsap.context(() => {
      gsap.from(cards, {
        opacity: 0,
        y: 20,
        duration: 0.5,
        stagger: 0.08,
        ease: STANDARD_EASE,
      });
    }, grid);
    return () => ctx.revert();
  }, [sessionId, booting, reduce]);

  // Scroll-spy: highlight the module currently in view. Re-runs once booting
  // clears so it observes the modules that mount with the dashboard.
  useEffect(() => {
    if (!sessionId || booting) return;
    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) visibleRef.current.add(e.target.id);
          else visibleRef.current.delete(e.target.id);
        }
        // A click just set the selection; leave it alone while it scrolls.
        if (Date.now() < navLockRef.current) return;
        // Keep the current module selected for as long as it is still in the
        // band, so a clicked card does not snap to its row-mate on the next
        // scroll tick.
        if (visibleRef.current.has(activeIdRef.current)) return;
        // Resolve ties in DOCUMENT order. The previous code sorted by
        // intersectionRatio -- the fraction of each element's OWN area in view
        // -- and the grid puts two cards on a row (forecast+categories,
        // anomalies+subscriptions). The shorter card of a pair always had the
        // larger ratio, so the taller left-hand one could never win: Forecast
        // and Anomalies were unreachable by scrolling OR clicking, while
        // Reconciliation and Overspending, alone on their rows, worked fine.
        const winner = MODULES.find((m) => visibleRef.current.has(m.id));
        if (winner) setActiveId(winner.id);
      },
      { rootMargin: '-30% 0px -55% 0px', threshold: [0, 0.25, 0.5, 1] }
    );
    visibleRef.current.clear();
    MODULES.forEach((m) => {
      const el = document.getElementById(m.id);
      if (el) obs.observe(el);
    });
    observerRef.current = obs;
    return () => obs.disconnect();
  }, [sessionId, booting]);

  // ------------------------------------------------------------- restoring //
  // Hold the frame while a stored session is verified, so a reload does not
  // flash the landing page before the board comes back.
  if (restoring && !sessionId) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg">
        <p className="font-mono text-micro uppercase tracking-wider text-txt-faint">
          Restoring session…
        </p>
      </div>
    );
  }

  // ---------------------------------------------------------------- landing //
  if (!sessionId) {
    return <Landing onUploadSuccess={handleUploadSuccess} />;
  }

  // ------------------------------------------------------------ boot bridge //
  if (booting) {
    return <ProcessingTerminal onComplete={() => setBooting(false)} />;
  }

  // -------------------------------------------------------------- dashboard //
  const activeLabel = MODULES.find((m) => m.id === activeId)?.nav ?? MODULES[0].nav;

  return (
    // Phosphor Light for the whole dashboard surface (sidebar, modules, states).
    <IconContext.Provider value={{ weight: 'light' }}>
    <div className="min-h-dvh lg:flex">
      {/* Sidebar (desktop) */}
      <aside className="sticky top-0 z-20 hidden h-dvh w-60 shrink-0 flex-col border-r border-line bg-header backdrop-blur-sm lg:flex relative isolate">
        {/* faint vertical phosphor wash for depth, behind the nav content */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-b from-transparent via-brand/[0.02] to-transparent"
        />
        <div className="flex h-16 items-center gap-2.5 border-b border-line px-5">
          <EyeMark className="h-7 w-7 text-txt" />
          <div className="leading-none">
            <span className="font-display text-base font-bold tracking-tight text-txt">
              Expense<span className="text-brand">Eye</span>
            </span>
            <p className="mt-1 font-mono text-micro uppercase tracking-eyebrow text-txt-faint">
              Analytics Console
            </p>
          </div>
        </div>

        <nav className="flex-1 space-y-0.5 px-3 py-5">
          <p className="px-3 pb-2 font-mono text-micro uppercase tracking-eyebrow text-txt-faint">
            Modules
          </p>
          {MODULES.map((m) => {
            const Icon = m.icon;
            const active = activeId === m.id;
            return (
              <a
                key={m.id}
                href={`#${m.id}`}
                onClick={(e) => handleNavClick(e, m.id)}
                aria-current={active ? 'true' : undefined}
                className={cn(
                  'flex min-h-11 items-center gap-3 rounded-md border-l-2 px-3 py-2 text-sm transition-all duration-200 ease-out active:translate-y-px',
                  active
                    ? 'border-brand bg-brand/[0.15] font-semibold text-txt shadow-[inset_0_0_12px_rgb(var(--brand-rgb)/_0.05)]'
                    : 'border-transparent font-medium text-txt-muted hover:bg-tint-2 hover:text-txt'
                )}
              >
                <Icon
                  aria-hidden="true"
                  className={cn(
                    'h-[18px] w-[18px] shrink-0',
                    active
                      ? 'text-brand drop-shadow-[0_0_4px_rgb(var(--brand-rgb)_/_0.4)]'
                      : 'text-txt-muted'
                  )}
                />
                <span className="flex-1">{m.nav}</span>
                {m.ml && (
                  <span className="font-mono text-micro font-semibold uppercase tracking-wider text-accent">
                    ml
                  </span>
                )}
              </a>
            );
          })}
        </nav>

        <div className="space-y-0.5 border-t border-line p-3">
          <ThemeToggle withLabel />
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex min-h-11 items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-txt-muted transition-all duration-150 ease-out hover:bg-tint-2 hover:text-txt active:translate-y-px"
          >
            <GithubMark className="h-4 w-4 text-txt-muted" />
            <span>Source</span>
          </a>
          <button
            onClick={handleLogout}
            className="flex min-h-11 w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-txt-muted transition-all duration-150 ease-out hover:bg-danger/10 hover:text-danger active:translate-y-px cursor-pointer"
          >
            <SignOut className="h-4 w-4" aria-hidden="true" />
            <span>End session</span>
          </button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-20 border-b border-line bg-header backdrop-blur-sm lg:hidden">
        <div className="flex h-14 items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <EyeMark className="h-6 w-6 text-txt" />
            <span className="font-display text-base font-bold tracking-tight text-txt">
              Expense<span className="text-brand">Eye</span>
            </span>
          </div>
          <div className="-mr-1 flex items-center gap-1">
            <ThemeToggle />
            <button
              onClick={handleLogout}
              className="flex min-h-11 items-center gap-1.5 rounded-md px-3 text-sm font-medium text-txt-muted transition-all duration-150 ease-out hover:bg-danger/10 hover:text-danger active:translate-y-px cursor-pointer"
            >
              <SignOut className="h-4 w-4" aria-hidden="true" />
              End
            </button>
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto border-t border-line px-3 py-1.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {MODULES.map((m) => {
            const Icon = m.icon;
            const active = activeId === m.id;
            return (
              <a
                key={m.id}
                href={`#${m.id}`}
                onClick={(e) => handleNavClick(e, m.id)}
                aria-current={active ? 'true' : undefined}
                className={cn(
                  'flex min-h-[40px] shrink-0 items-center gap-1.5 rounded-md px-3 text-data font-medium transition-all duration-150 ease-out active:translate-y-px',
                  active ? 'bg-brand/[0.15] text-txt' : 'text-txt-muted hover:text-txt active:bg-tint-2'
                )}
              >
                <Icon className={cn('h-4 w-4 shrink-0', active ? 'text-brand' : 'text-txt-faint')} aria-hidden="true" />
                {m.nav}
              </a>
            );
          })}
        </nav>
      </header>

      {/* Main content */}
      <div className="min-w-0 flex-1">
        <SessionTape sessionId={sessionId} activeLabel={activeLabel} moduleCount={MODULES.length} />
        <main className="mx-auto max-w-6xl px-5 py-8 sm:px-8 lg:py-12">
          <div className="mb-10 border-b border-line pb-5">
            <h1 className="font-display text-2xl font-bold tracking-tight text-txt text-balance">
              Spending overview
            </h1>
            <p className="mt-2 max-w-[60ch] text-sm leading-relaxed text-txt-muted">
              {MODULES.length} read-outs on this statement, parsed server-side, per session. Scan the board or jump
              from the rail; the tape above tracks what you're looking at.
            </p>
          </div>

          <div ref={gridRef} className="grid grid-cols-1 gap-x-6 gap-y-8 lg:grid-cols-5 lg:items-start">
            {MODULES.map((mod) => (
              <ModuleCard key={mod.id} mod={mod} sessionId={sessionId} />
            ))}
          </div>

          {/* Dashboard footer: a status line, not the landing's prose sign-off.
              Echoes the live session (same handle as the tape's SES cell) so the
              board is bracketed top and bottom by its own telemetry. */}
          <footer className="mt-16 border-t border-line pt-6">
            <div className="flex flex-col gap-3 text-xs text-txt-faint sm:flex-row sm:items-center sm:justify-between">
              <p className="flex flex-wrap items-center gap-x-2.5 gap-y-1 font-mono uppercase tracking-wider">
                <span className="inline-flex items-center gap-1.5 text-txt-muted">
                  <span className="h-1.5 w-1.5 rounded-full bg-brand" aria-hidden="true" />
                  Session {shortId(sessionId)}
                </span>
                <span aria-hidden="true">·</span>
                <span>{MODULES.length} modules loaded</span>
                <span aria-hidden="true">·</span>
                <span>session-scoped, deleted on exit</span>
              </p>
              <p className="font-mono">ExpenseEye · {new Date().getFullYear()}</p>
            </div>
          </footer>
        </main>
      </div>
    </div>
    </IconContext.Provider>
  );
}

/** Boot log lines. The tag carries the signal color (cyan for the ML steps,
    phosphor green for the final READY), matching the console's "color is signal"
    rule. */
const BOOT_LOGS: { tag: string; text: string; tone: 'muted' | 'accent' | 'brand' }[] = [
  { tag: 'SYSTEM', text: 'Allocating local memory…', tone: 'muted' },
  { tag: 'PARSER', text: 'Reading statement rows…', tone: 'muted' },
  { tag: 'PARSER', text: 'Mapping columns: date, amount, payee…', tone: 'muted' },
  { tag: 'ML', text: 'Classifying transactions…', tone: 'accent' },
  { tag: 'ML', text: 'Forecasting next-month cash flow…', tone: 'accent' },
  { tag: 'READY', text: 'Board ready.', tone: 'brand' },
];

const TONE_CLASS = { muted: 'text-txt-faint', accent: 'text-accent', brand: 'text-brand' } as const;

/**
 * Boot bridge shown between a successful upload and the dashboard. By the time
 * this mounts the backend has already parsed and classified the statement, so
 * this isn't a fake delay padding empty time. It replays that finished work as a
 * short terminal sequence (~2.5s) so the jump to the board reads as a deliberate
 * hand-off instead of a hard snap. Under reduced motion the full log renders at
 * once and it hands off quickly. All token-styled, so it tracks both themes.
 */
function ProcessingTerminal({ onComplete }: { onComplete: () => void }) {
  const reduce = useReducedMotion();
  const [shown, setShown] = useState(reduce ? BOOT_LOGS.length : 0);
  // Hold the latest callback in a ref so the timer effect runs once on mount and
  // never restarts the sequence if the parent re-renders.
  const done = useRef(onComplete);
  useEffect(() => { done.current = onComplete; }, [onComplete]);

  useEffect(() => {
    if (reduce) {
      const t = window.setTimeout(() => done.current(), 500);
      return () => window.clearTimeout(t);
    }
    const STEP = 360; // ms between lines; six lines + a tail beat ≈ 2.5s
    const timers = BOOT_LOGS.map((_, i) =>
      window.setTimeout(() => setShown(i + 1), i * STEP)
    );
    timers.push(window.setTimeout(() => done.current(), BOOT_LOGS.length * STEP + 340));
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [reduce]);

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center px-5">
      <div className="w-full max-w-lg">
        {/* tape-style header, mirroring the dashboard's session tape */}
        <div className="flex h-9 items-center gap-2.5 rounded-t-lg border border-line bg-header px-4">
          <span className="live-dot" aria-hidden="true" />
          <span className="font-mono text-micro font-semibold uppercase tracking-wider text-brand">
            Initializing
          </span>
          <span className="ml-auto font-mono text-micro uppercase tracking-wider text-txt-faint">
            Local session
          </span>
        </div>

        <div
          className="rounded-b-lg border border-t-0 border-line bg-panel p-5 shadow-panel"
          role="status"
          aria-live="polite"
        >
          <ul className="space-y-2.5 font-mono text-data">
            {BOOT_LOGS.slice(0, shown).map((l, i) => {
              const isLast = i === shown - 1;
              return (
                <li key={i} className="flex animate-fade-rise items-start gap-2.5">
                  <span
                    className={cn('shrink-0 font-semibold uppercase tracking-wider', TONE_CLASS[l.tone])}
                  >
                    [{l.tag}]
                  </span>
                  <span className="text-txt-muted">
                    {l.text}
                    {isLast && shown < BOOT_LOGS.length && (
                      <span
                        aria-hidden="true"
                        className="ml-1 inline-block h-3.5 w-[7px] translate-y-[2px] animate-pulse bg-brand align-baseline"
                      />
                    )}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </div>
  );
}

/**
 * Stylized, non-interactive preview of the Vault Terminal console. Built from the
 * real design-system primitives (the session tape, .kpi-label/.kpi-value legends,
 * the cyan ML tag, the live-dot, the .inset surface) so it reads as a faithful
 * mini-instance of the actual board, not a generic fake screenshot. Purely
 * decorative: aria-hidden, no pointer events, figures are illustrative mocks
 * (never fetched, never shown after a real upload). Fills the desktop hero's
 * right half with a concrete promise of what the upload unlocks. Themes via
 * tokens, so it tracks light/dark automatically.
 */
function ConsolePreview() {
  // mock — illustrative figures only; the live board derives everything from the
  // user's own statement. Last three bars are the projected (ML) horizon.
  const bars = [42, 55, 47, 63, 51, 74, 60, 81, 58, 88, 72, 79];
  const subs = [
    { name: 'Netflix', amount: '₹649' },
    { name: 'Adobe CC', amount: '₹4,230' },
  ];

  return (
    <div aria-hidden="true" className="pointer-events-none select-none">
      {/* Telemetry strip — the console's signature status line */}
      <div className="flex h-9 items-center overflow-hidden rounded-t-lg border border-line bg-header">
        <div className="flex shrink-0 items-center gap-2 pl-4 pr-3.5">
          <span className="live-dot" />
          <span className="font-mono text-micro font-semibold uppercase tracking-wider text-brand">Demo</span>
        </div>
        <div className="tape-cell border-l border-line">
          <span className="tape-key">SES</span>
          <span className="readout tape-val">7F3A9C2E</span>
        </div>
        <div className="tape-cell border-l border-line">
          <span className="tape-key">MOD</span>
          <span className="readout text-brand">Forecast</span>
        </div>
      </div>

      {/* Body */}
      <div className="rounded-b-lg border border-t-0 border-line bg-panel p-4 shadow-panel sm:p-5">
        {/* KPI pair — instrument legends over mono readouts, hairline-divided */}
        <div className="grid grid-cols-2 rounded-md border border-line">
          <div className="p-3.5">
            <span className="kpi-label">Monthly spend</span>
            <div className="kpi-value text-[1.4rem]">₹1,24,500</div>
            <div className="mt-1.5 flex items-center gap-1 font-mono text-micro text-brand">
              <TrendDown className="h-3 w-3" aria-hidden="true" />
              6.2% vs prior
            </div>
          </div>
          <div className="border-l border-line p-3.5">
            <div className="flex items-center gap-1.5">
              <span className="kpi-label">Forecast</span>
              <span className="tag-ml">ML</span>
            </div>
            <div className="kpi-value text-[1.4rem] text-accent-light">₹1,16,800</div>
            <div className="mt-1.5 font-mono text-micro text-txt-faint">next 30 days</div>
          </div>
        </div>

        {/* Cash-flow bars — solid history in phosphor, projected horizon in cyan */}
        <div className="inset mt-4 p-3.5">
          <div className="mb-3 flex items-center justify-between">
            <span className="font-mono text-micro uppercase tracking-wider text-txt-faint">Cash flow · 12 wk</span>
            <span className="flex items-center gap-1 font-mono text-micro text-accent">
              <span className="h-1.5 w-1.5 rounded-sm bg-accent/60" />
              projected
            </span>
          </div>
          {/* pointer-events re-enabled here (the preview is otherwise inert) so
              each bar can lift on hover — transform-only, neutralized under
              reduced motion by the global transition override. */}
          <div className="pointer-events-auto flex h-20 items-end gap-1.5">
            {bars.map((h, i) => (
              <div
                key={i}
                className={cn(
                  'flex-1 origin-bottom rounded-sm transition-transform duration-200 ease-out hover:scale-y-110',
                  i >= 9 ? 'bg-accent/35 hover:bg-accent/55' : 'bg-brand/25 hover:bg-brand/45'
                )}
                style={{ height: `${h}%` }}
              />
            ))}
          </div>
        </div>

        {/* Recurring subscriptions — a compact slice of the radar */}
        <div className="mt-4 overflow-hidden rounded-md border border-line">
          <div className="flex items-center justify-between border-b border-line bg-tint-1 px-3.5 py-2">
            <span className="font-mono text-micro uppercase tracking-wider text-txt-faint">Recurring detected</span>
            <span className="font-mono text-micro text-txt-faint">{subs.length}</span>
          </div>
          {subs.map((s, i) => (
            <div
              key={s.name}
              className={cn('flex items-center justify-between px-3.5 py-2', i > 0 && 'border-t border-line')}
            >
              <span className="text-data text-txt-muted">{s.name}</span>
              <span className="font-mono text-data text-txt">
                {s.amount}
                <span className="text-txt-faint">/mo</span>
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Trust + privacy block below the hero. A privacy-first finance tool has to earn
 * the right to ask for a bank statement, so this section trades on what's
 * verifiable rather than invented social proof: it's open source, self-hostable,
 * accountless, and ephemeral. The three guarantees are worded to the real
 * architecture (the CSV is parsed by ExpenseEye's own backend, not a third
 * party, and you can run the whole stack yourself), never the false "it never
 * leaves your browser" claim. Hairline-divided columns, not boxed cards, per the
 * Vault Terminal "one flat surface, dividers not boxes" rule. Tokens throughout,
 * so it tracks both themes.
 */
function PrivacyTrust() {
  // Verifiable claims only — each is true whether ExpenseEye runs on the public
  // demo or a machine you host yourself. No fabricated customers.
  const signals = ['Open source', 'Self-hostable', 'No account', 'Auto-deleted'];

  const guarantees = [
    {
      icon: ShieldCheck,
      title: 'No third-party services',
      body: 'Your statement is parsed by ExpenseEye itself, never handed off to an outside processor.',
    },
    {
      icon: Cpu,
      title: 'Models you can run yourself',
      body: 'Categorization and forecasting are part of the open-source stack. Self-host them on your own machine.',
    },
    {
      icon: Lock,
      title: 'Ephemeral by default',
      body: 'When the session ends your data is deleted. Nothing is persisted, nothing is sold.',
    },
  ];

  return (
    <section
      aria-labelledby="privacy-heading"
      data-anim="privacy-section"
      className="mt-20 border-t border-line pt-12 lg:mt-28 lg:pt-16"
    >
      {/* Open-source credibility — the verifiable signals scroll as one seamless,
          edge-faded loop (CSS-only, pauses on hover). Decorative repetition, so
          it's aria-hidden: the same claims are stated for assistive tech in the
          heading + paragraph just below. */}
      <div
        aria-hidden="true"
        className="marquee relative mb-12 overflow-hidden border-y border-line py-3.5"
      >
        <div className="marquee-track flex w-max items-center">
          {[0, 1].map((copy) => (
            <div key={copy} className="flex shrink-0 items-center">
              {[...signals, ...signals, ...signals].map((s, i) => (
                <span key={`${copy}-${i}`} className="flex items-center">
                  <span className="px-6 font-mono text-micro uppercase tracking-eyebrow text-txt-faint">
                    {s}
                  </span>
                  <span className="h-1 w-1 rounded-full bg-brand/40" />
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>

      <h2
        id="privacy-heading"
        className="font-display text-2xl font-bold tracking-tight text-txt text-balance sm:text-3xl"
      >
        Private by architecture
      </h2>
      <p className="mt-3 max-w-[60ch] text-base leading-relaxed text-txt-muted text-pretty">
        ExpenseEye is open source and self-hostable. No accounts, no third-party processors, and
        nothing kept once your session ends.
      </p>
      <a
        href={REPO_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-5 inline-flex items-center gap-2 font-mono text-micro uppercase tracking-wider text-txt-muted transition-colors hover:text-brand active:translate-y-px"
      >
        <GithubMark className="h-4 w-4" />
        Read the source
      </a>

      {/* Three guarantees, broken out of the symmetric three-column row: the
          first claim leads at double width over a faint brand wash; the other two
          stack beside it. On mobile all three fall to a plain icon + h3 + p
          stack, no backgrounds. */}
      <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-3">
        <div data-anim="privacy-lead" className="sm:col-span-2 sm:rounded-xl sm:bg-brand/[0.04] sm:p-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-md border border-line bg-tint-1 sm:h-14 sm:w-14">
            <ShieldCheck className="h-6 w-6 text-brand sm:h-7 sm:w-7" aria-hidden="true" />
          </div>
          <h3 className="mt-5 text-lg font-semibold text-txt text-balance sm:text-xl">
            {guarantees[0].title}
          </h3>
          <p className="mt-2.5 max-w-[55ch] text-sm leading-relaxed text-txt-muted text-pretty sm:text-base">
            {guarantees[0].body}
          </p>
        </div>

        <div className="grid gap-6 sm:col-span-1 sm:grid-rows-2">
          {guarantees.slice(1).map(({ icon: Icon, title, body }) => (
            <div key={title} data-anim="privacy-card">
              <div className="flex h-10 w-10 items-center justify-center rounded-md border border-line bg-tint-1">
                <Icon className="h-[18px] w-[18px] text-brand" aria-hidden="true" />
              </div>
              <h3 className="mt-4 text-base font-semibold text-txt">{title}</h3>
              <p className="mt-2 max-w-[42ch] text-sm leading-relaxed text-txt-muted text-pretty">
                {body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/**
 * One capability in the hero's 2×2 grid. Entrance is driven by the hero GSAP
 * timeline (data-anim="feature", staggered on load); this component owns only
 * the hover nudge. `.will-animate` keeps it hidden until the timeline runs.
 */
function CapabilityItem({
  icon: Icon,
  label,
  note,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  note: string;
}) {
  return (
    <li data-anim="feature" className="will-animate group cursor-default">
      <div className="flex items-center gap-3 transition-transform duration-200 ease-out group-hover:translate-x-1">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-line bg-tint-1 transition-colors duration-200 group-hover:border-line-strong">
          <Icon
            className="h-[18px] w-[18px] text-brand transition-[filter] duration-200 group-hover:drop-shadow-[0_0_5px_rgb(var(--brand-rgb)_/_0.5)]"
            aria-hidden="true"
          />
        </span>
        <div className="leading-tight">
          <span className="block text-sm font-medium text-txt">{label}</span>
          <span className="block font-mono text-micro text-txt-faint transition-colors duration-200 group-hover:text-txt-muted">
            {note}
          </span>
        </div>
      </div>
    </li>
  );
}

// ------------------------------------------------------------------ Landing //
function Landing({ onUploadSuccess }: { onUploadSuccess: (id: string) => void }) {
  const capabilities = [
    { icon: TrendUp, label: 'Cash-flow forecast', note: 'next-month projection' },
    { icon: TreeStructure, label: 'Smart categorization', note: 'trained classifier' },
    { icon: Fingerprint, label: 'Anomaly detection', note: 'outlier charges' },
    { icon: ArrowsClockwise, label: 'Subscription radar', note: 'recurring payments' },
  ];

  const [menuOpen, setMenuOpen] = useState(false);
  // (8) Nav scroll state, driven by a ScrollTrigger in the effect below.
  const [scrolled, setScrolled] = useState(false);
  const reduce = useReducedMotion();
  const rootRef = useRef<HTMLDivElement>(null);
  // (10) The console preview tilts toward the cursor on desktop pointers.
  const previewTiltRef = useMagneticTilt<HTMLDivElement>(3);

  // Landing motion: (2) the hero load timeline, (8) the nav scroll state, and
  // (4) the "Private by architecture" scroll reveals. All scoped to a gsap
  // context so a single revert() on unmount kills every tween + ScrollTrigger.
  // useLayoutEffect sets hidden start states before paint (with .will-animate as
  // the pre-JS guard). Reduced motion: nav state still tracks, everything else
  // snaps visible.
  useLayoutEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    const ctx = gsap.context(() => {
      // (8) Floating nav — prominent at the top, recedes once past 80px.
      ScrollTrigger.create({
        trigger: document.documentElement,
        start: 'top top',
        end: 'bottom bottom',
        onUpdate: (self) => setScrolled(self.scroll() > 80),
      });

      if (reduce) {
        gsap.set('.will-animate', { opacity: 1, clearProps: 'transform' });
        return;
      }

      // (2) Hero load stagger. Neutralize .will-animate first so each .from()
      // resolves to the visible end state, then tween up from hidden.
      gsap.set('[data-anim]', { opacity: 1 });
      const tl = gsap.timeline({ defaults: { ease: STANDARD_EASE } });
      tl.from('[data-anim="nav"]', { opacity: 0, y: -8, duration: 0.6 }, 0)
        .from('[data-anim="headline"]', { opacity: 0, y: 24, duration: 0.8 }, 0.15)
        .from('[data-anim="subtext"]', { opacity: 0, y: 16, duration: 0.7 }, 0.3)
        .from('[data-anim="feature"]', { opacity: 0, y: 12, duration: 0.6, stagger: 0.12 }, 0.45)
        .from('[data-anim="upload"]', { opacity: 0, y: 16, duration: 0.7 }, 0.5)
        .from('[data-anim="preview"]', { opacity: 0, scale: 0.96, duration: 0.9 }, 0.2);

      // (4) Private by architecture — lead card scrubs 0.4 → 1 as it enters;
      // the two stacked cards rise + fade with a 150ms stagger at 80% in view.
      const lead = root.querySelector('[data-anim="privacy-lead"]');
      if (lead) {
        gsap.fromTo(
          lead,
          { opacity: 0.4 },
          {
            opacity: 1,
            ease: 'none',
            scrollTrigger: { trigger: lead, start: 'top 85%', end: 'top 45%', scrub: true },
          }
        );
      }
      const rightCards = root.querySelectorAll('[data-anim="privacy-card"]');
      const privacy = root.querySelector('[data-anim="privacy-section"]');
      if (rightCards.length && privacy) {
        gsap.from(rightCards, {
          opacity: 0,
          y: 32,
          duration: 0.7,
          stagger: 0.15,
          ease: STANDARD_EASE,
          scrollTrigger: { trigger: privacy, start: 'top 80%' },
        });
      }

      // Recompute trigger positions once everything is laid out.
      ScrollTrigger.refresh();
    }, root);

    return () => ctx.revert();
  }, [reduce]);

  return (
    // Phosphor Light weight for every icon on the landing surface (the dashboard
    // keeps its own lucide set). One context beats threading `weight` per icon.
    <IconContext.Provider value={{ weight: 'light' }}>
      <div ref={rootRef} className="relative flex min-h-dvh flex-col">
        {/* Floating glass-pill nav — detached from the top, the one place glass is
            allowed. Sticks with a 20px gap held by the wrapper's padding (not a
            margin, which would collapse on stick). Prominent at the top, recedes
            (ring/shadow off) once scrolled past 80px — toggled by ScrollTrigger. */}
        <header className="sticky top-0 z-30 px-4 pt-5">
          <div
            data-anim="nav"
            // State colors/shadow driven inline from theme tokens (white overlays
            // in dark, frosted white + ink shadow in light) so the rest→scrolled
            // jump reads on either canvas. Inline avoids Tailwind parsing a bare
            // var() shadow as a shadow-color. The transition lives in the class.
            style={{
              backgroundColor: scrolled ? 'var(--nav-bg-active)' : 'var(--nav-bg)',
              borderColor: scrolled ? 'var(--nav-border-active)' : 'var(--nav-border)',
              boxShadow: scrolled ? 'var(--nav-shadow-active)' : '0 0 0 0 rgba(0,0,0,0)',
            }}
            className="will-animate mx-auto flex w-full max-w-2xl items-center justify-between gap-6 rounded-full border px-5 py-2.5 backdrop-blur-xl transition-[background-color,border-color,box-shadow] duration-[400ms] ease-out sm:w-max sm:gap-12 sm:px-6 sm:py-3"
          >
            <div className="flex items-center gap-2.5">
              <EyeMark className="h-7 w-7 text-txt" />
              <span className="font-display text-base font-bold tracking-tight text-txt">
                Expense<span className="text-brand">Eye</span>
              </span>
            </div>

            {/* Desktop actions */}
            <div className="hidden items-center gap-0.5 sm:flex">
              <ThemeToggle />
              <a
                href={REPO_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="flex h-11 w-11 items-center justify-center rounded-full text-txt-faint transition-colors hover:text-txt active:translate-y-px"
                aria-label="GitHub repository"
              >
                <GithubMark className="h-5 w-5" />
              </a>
            </div>

            {/* Mobile hamburger → X (transform-only morph) */}
            <button
              type="button"
              onClick={() => setMenuOpen((o) => !o)}
              aria-expanded={menuOpen}
              aria-controls="landing-menu"
              aria-label={menuOpen ? 'Close menu' : 'Open menu'}
              className="relative h-9 w-9 shrink-0 rounded-full text-txt transition-colors hover:bg-tint-2 active:translate-y-px sm:hidden"
            >
              <span
                aria-hidden="true"
                className={cn(
                  'absolute left-2.5 right-2.5 top-1/2 h-[1.5px] rounded-full bg-current transition-transform duration-300 ease-out',
                  menuOpen ? 'rotate-45' : '-translate-y-[4px]'
                )}
              />
              <span
                aria-hidden="true"
                className={cn(
                  'absolute left-2.5 right-2.5 top-1/2 h-[1.5px] rounded-full bg-current transition-transform duration-300 ease-out',
                  menuOpen ? '-rotate-45' : 'translate-y-[4px]'
                )}
              />
            </button>
          </div>

          {/* Mobile menu — absolute, so opening it never shifts layout; fades and
              slides on transform + opacity only. */}
          <div
            id="landing-menu"
            className={cn(
              'absolute inset-x-4 top-full origin-top rounded-2xl border border-line bg-header p-2 shadow-panel backdrop-blur-xl transition-all duration-300 ease-out sm:hidden',
              menuOpen ? 'translate-y-2 opacity-100' : 'pointer-events-none -translate-y-1 opacity-0'
            )}
          >
            <ThemeToggle withLabel />
            <a
              href={REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex min-h-11 items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-txt-muted transition-colors hover:bg-tint-2 hover:text-txt active:translate-y-px"
            >
              <GithubMark className="h-4 w-4" />
              <span>Read the source</span>
            </a>
          </div>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 px-5 py-12 sm:px-8 lg:py-20">
          {/* Two-up on desktop: positioning + intake on the left, a preview of the
              console on the right so the empty half carries the product's promise.
              Collapses to a single stacked column below lg. */}
          <div className="grid grid-cols-1 items-center gap-x-16 gap-y-14 lg:grid-cols-2">
            {/* Left — positioning + the intake instrument */}
            <div className="min-w-0">
              <div>
                <h1 data-anim="headline" className="will-animate max-w-4xl font-display text-[2.75rem] font-bold leading-[1.03] tracking-[-0.03em] text-txt text-balance sm:text-6xl">
                  Drop. Parse.
                  <br />
                  <span className="text-brand">Know.</span>
                </h1>
                <p data-anim="subtext" className="will-animate mt-6 max-w-xl text-base leading-relaxed text-txt-muted text-pretty">
                  Drop in a bank statement and ExpenseEye reads it the way an analyst would:
                  forecasting next month, flagging the charges that don't fit, and surfacing the
                  subscriptions you forgot about.
                </p>

                {/* Capability grid — a true 2×2 on sm+, each row staggered in by
                    the hero load timeline. Stacks to one column on mobile. */}
                <ul className="mt-9 grid grid-cols-1 gap-x-8 gap-y-5 sm:grid-cols-2">
                  {capabilities.map(({ icon, label, note }) => (
                    <CapabilityItem key={label} icon={icon} label={label} note={note} />
                  ))}
                </ul>
              </div>

              {/* The instrument */}
              <div data-anim="upload" className="will-animate mt-10 max-w-xl">
                <FileUpload onUploadSuccess={onUploadSuccess} />
              </div>
            </div>

            {/* Right — a stylized peek at the board the upload unlocks, set in a
                double-bezel shell (aluminium tray + glass plate) over a soft
                phosphor glow so it reads as physical hardware, not a flat mock.
                Scales in on load (data-anim) and tilts toward the cursor on
                desktop pointers (perspective here, rotation on the tray). */}
            <div
              ref={previewTiltRef}
              data-anim="preview"
              style={{ perspective: '800px' }}
              className="will-animate relative mx-auto w-full min-w-0 max-w-md lg:max-w-none"
            >
              <div
                aria-hidden="true"
                className="pointer-events-none absolute -inset-4 rounded-[3rem] bg-brand/[0.08] blur-3xl"
              />
              <div data-tilt-target className="relative rounded-[2rem] border border-line bg-tint-1 p-2">
                <div className="overflow-hidden rounded-[1.5rem]">
                  <ConsolePreview />
                </div>
              </div>
            </div>
          </div>

          {/* Earn the right to ask for a bank statement */}
          <PrivacyTrust />
        </main>

        <footer className="mt-8 border-t border-line">
          <div className="mx-auto flex max-w-6xl flex-col gap-3 px-5 py-7 sm:flex-row sm:items-center sm:justify-between sm:px-8">
            <p className="font-mono text-xs uppercase tracking-wider text-txt-muted">
              Expense<span className="text-brand">Eye</span> · {new Date().getFullYear()}
            </p>
            <div className="flex flex-col gap-2 text-xs text-txt-faint sm:flex-row sm:items-center sm:gap-5">
              <a
                href={REPO_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-txt-muted transition-colors hover:text-brand active:translate-y-px"
              >
                <GithubMark className="h-4 w-4" />
                <span>GitHub</span>
              </a>
              <span className="text-txt-faint">Open source. Private by design.</span>
            </div>
          </div>
        </footer>
      </div>
    </IconContext.Provider>
  );
}

export default App;
