import { useState, useEffect, useRef } from 'react';
import type { ComponentType } from 'react';
import { LogOut, TrendingUp, Tags, ShieldAlert, CalendarClock, BarChart3 } from 'lucide-react';
import { FileUpload } from '@/components/FileUpload';
import { SessionTape } from '@/components/SessionTape';
import { SubscriptionsTable } from '@/components/SubscriptionsTable';
import { OverspendingAnalysis } from '@/components/OverspendingAnalysis';
import { CashFlowForecast } from '@/components/CashFlowForecast';
import { TransactionCategories } from '@/components/TransactionCategories';
import { AnomalyDetection } from '@/components/AnomalyDetection';
import { ThemeToggle } from '@/components/ThemeToggle';
import { useInView } from '@/lib/useInView';
import { cn } from '@/lib/utils';

/** GitHub mark (not in this lucide-react build, so inlined). */
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
    icon: TrendingUp,
    ml: true,
    span: 'lg:col-span-3',
    render: (s) => <CashFlowForecast sessionId={s} />,
  },
  {
    id: 'categories',
    nav: 'Categories',
    title: 'Smart Categorization',
    desc: 'Every transaction sorted by a trained model, with a rule-based fallback.',
    icon: Tags,
    ml: true,
    span: 'lg:col-span-2',
    render: (s) => <TransactionCategories sessionId={s} />,
  },
  {
    id: 'anomalies',
    nav: 'Anomalies',
    title: 'Anomaly Detection',
    desc: 'Charges that fall outside your normal pattern, ranked by how far they deviate.',
    icon: ShieldAlert,
    ml: true,
    span: 'lg:col-span-2',
    render: (s) => <AnomalyDetection sessionId={s} />,
  },
  {
    id: 'subscriptions',
    nav: 'Subscriptions',
    title: 'Recurring Subscriptions',
    desc: 'Regular payments detected from the cadence of your statement.',
    icon: CalendarClock,
    span: 'lg:col-span-3',
    render: (s) => <SubscriptionsTable sessionId={s} />,
  },
  {
    id: 'overspending',
    nav: 'Overspending',
    title: 'Overspending Analysis',
    desc: 'Months that ran hot against your trailing three-month baseline.',
    icon: BarChart3,
    span: 'lg:col-span-5',
    render: (s) => <OverspendingAnalysis sessionId={s} />,
  },
];

const REPO_URL = 'https://github.com/shan3520/expenseeye';

/** Module header: icon + title, no scaffolding numbers or eyebrows. */
function ModuleHeader({ mod }: { mod: ModuleDef }) {
  const Icon = mod.icon;
  return (
    <header className="mb-5">
      <div className="flex items-center gap-2.5">
        <span className="module-rail" aria-hidden="true" />
        <Icon className="h-[18px] w-[18px] text-txt-muted" />
        <h2 className="font-display text-subhead font-semibold tracking-tight text-txt">
          {mod.title}
        </h2>
        {mod.ml && <span className="tag-ml">ML</span>}
      </div>
      <p className="mt-2 max-w-[68ch] pl-[14px] text-sm leading-relaxed text-txt-muted text-pretty">{mod.desc}</p>
    </header>
  );
}

/** One bento tile: header + panel, sprung into view on first scroll-in. The
    `index` gives the opening rows a short cascade; later tiles reveal as reached. */
function ModuleCard({ mod, sessionId, index }: { mod: ModuleDef; sessionId: string; index: number }) {
  const { ref, inView } = useInView<HTMLElement>();
  return (
    <section
      ref={ref}
      id={mod.id}
      data-reveal={inView ? 'in' : 'out'}
      style={{ transitionDelay: `${Math.min(index, 3) * 80}ms` }}
      className={cn('scroll-mt-28 lg:scroll-mt-24', mod.span)}
    >
      <ModuleHeader mod={mod} />
      <div className="panel p-5 sm:p-6">{mod.render(sessionId)}</div>
    </section>
  );
}

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string>(MODULES[0].id);
  const observerRef = useRef<IntersectionObserver | null>(null);

  const handleLogout = () => {
    setSessionId(null);
    setActiveId(MODULES[0].id);
  };

  // Scroll-spy: highlight the module currently in view.
  useEffect(() => {
    if (!sessionId) return;
    const obs = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]) setActiveId(visible[0].target.id);
      },
      { rootMargin: '-30% 0px -55% 0px', threshold: [0, 0.25, 0.5, 1] }
    );
    MODULES.forEach((m) => {
      const el = document.getElementById(m.id);
      if (el) obs.observe(el);
    });
    observerRef.current = obs;
    return () => obs.disconnect();
  }, [sessionId]);

  // ---------------------------------------------------------------- landing //
  if (!sessionId) {
    return <Landing onUploadSuccess={setSessionId} />;
  }

  // -------------------------------------------------------------- dashboard //
  const activeLabel = MODULES.find((m) => m.id === activeId)?.nav ?? MODULES[0].nav;

  return (
    <div className="min-h-dvh lg:flex">
      {/* Sidebar (desktop) */}
      <aside className="sticky top-0 z-20 hidden h-dvh w-60 shrink-0 flex-col border-r border-line bg-header backdrop-blur-sm lg:flex">
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
                aria-current={active ? 'true' : undefined}
                className={cn(
                  'flex min-h-11 items-center gap-3 rounded-md border-l-2 px-3 py-2 text-sm transition-colors',
                  active
                    ? 'border-brand bg-brand/[0.15] font-semibold text-txt'
                    : 'border-transparent font-medium text-txt-muted hover:bg-tint-2 hover:text-txt'
                )}
              >
                <Icon
                  className={cn(
                    'h-[18px] w-[18px] shrink-0',
                    active
                      ? 'text-brand drop-shadow-[0_0_4px_rgb(var(--brand-rgb)_/_0.4)]'
                      : 'text-txt-muted'
                  )}
                />
                <span className="flex-1">{m.nav}</span>
                {m.ml && (
                  <span className="font-mono text-micro font-semibold uppercase tracking-wider text-accent/80">
                    ml
                  </span>
                )}
              </a>
            );
          })}
        </nav>

        <div className="space-y-1 border-t border-line p-3">
          <ThemeToggle withLabel />
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex min-h-11 items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-txt-muted transition-colors hover:bg-tint-2 hover:text-txt"
          >
            <GithubMark className="h-4 w-4 text-txt-muted" />
            <span>Source</span>
          </a>
          <button
            onClick={handleLogout}
            className="flex min-h-11 w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-txt-muted transition-colors hover:bg-danger/10 hover:text-danger cursor-pointer"
          >
            <LogOut className="h-4 w-4" />
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
              className="flex min-h-11 items-center gap-1.5 rounded-md px-3 text-sm font-medium text-txt-muted transition-colors hover:bg-danger/10 hover:text-danger cursor-pointer"
            >
              <LogOut className="h-4 w-4" />
              End
            </button>
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto border-t border-line px-3 py-1.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {MODULES.map((m) => (
            <a
              key={m.id}
              href={`#${m.id}`}
              aria-current={activeId === m.id ? 'true' : undefined}
              className={cn(
                'flex min-h-[40px] shrink-0 items-center rounded-md px-3 text-data font-medium transition-colors',
                activeId === m.id ? 'bg-brand/[0.12] text-txt' : 'text-txt-muted'
              )}
            >
              {m.nav}
            </a>
          ))}
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
              Five read-outs on this statement, parsed locally. Scan the board or jump from the
              rail; the tape above tracks what you're looking at.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-x-6 gap-y-8 lg:grid-cols-5 lg:items-start">
            {MODULES.map((mod, i) => (
              <ModuleCard key={mod.id} mod={mod} sessionId={sessionId} index={i} />
            ))}
          </div>

          <footer className="mt-16 border-t border-line pt-6">
            <div className="flex flex-col gap-2 text-xs text-txt-faint sm:flex-row sm:items-center sm:justify-between">
              <p>
                Processed locally · files deleted when the session ends · nothing stored or shared.
              </p>
              <p className="font-mono">ExpenseEye · {new Date().getFullYear()}</p>
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ Landing //
function Landing({ onUploadSuccess }: { onUploadSuccess: (id: string) => void }) {
  const capabilities = [
    { icon: TrendingUp, label: 'Cash-flow forecast', note: 'next-month projection' },
    { icon: Tags, label: 'Smart categorization', note: 'trained classifier' },
    { icon: ShieldAlert, label: 'Anomaly detection', note: 'outlier charges' },
    { icon: CalendarClock, label: 'Subscription radar', note: 'recurring payments' },
  ];

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-line">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8">
          <div className="flex items-center gap-2.5">
            <EyeMark className="h-8 w-8 text-txt" />
            <div className="leading-none">
              <span className="font-display text-lg font-bold tracking-tight text-txt">
                Expense<span className="text-brand">Eye</span>
              </span>
              <p className="mt-1 font-mono text-micro uppercase tracking-eyebrow text-txt-faint">
                Analytics Console
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <a
              href={REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex h-9 w-9 items-center justify-center text-txt-faint transition-colors hover:text-txt"
              aria-label="GitHub repository"
            >
              <GithubMark className="h-5 w-5" />
            </a>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-5 py-12 sm:px-8 lg:py-16">
        {/* Positioning — full-width, left-aligned */}
        <div className="animate-fade-rise">
          <h1 className="font-display text-5xl font-bold leading-[1.0] tracking-tight text-txt sm:text-6xl">
            Drop. Parse.
            <br />
            <span className="text-brand">Know.</span>
          </h1>
          <p className="mt-6 max-w-xl text-base leading-relaxed text-txt-muted text-pretty">
            Drop in a bank statement and ExpenseEye reads it the way an analyst would:
            forecasting next month, flagging the charges that don't fit, and surfacing the
            subscriptions you forgot about.
          </p>

          {/* Capability strip — inline legend, not a boxed grid */}
          <ul className="mt-8 flex flex-wrap gap-x-8 gap-y-4">
            {capabilities.map(({ icon: Icon, label, note }) => (
              <li key={label} className="flex items-center gap-2.5">
                <Icon className="h-4 w-4 shrink-0 text-brand" />
                <div className="leading-tight">
                  <span className="block text-sm font-medium text-txt">{label}</span>
                  <span className="block font-mono text-micro text-txt-faint">{note}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* The instrument */}
        <div className="mt-10 max-w-2xl animate-fade-rise [animation-delay:80ms]">
          <FileUpload onUploadSuccess={onUploadSuccess} />
        </div>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-1 px-5 py-5 text-xs text-txt-faint sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <p>Processed locally · deleted after the session · nothing stored or shared.</p>
          <p className="font-mono">ExpenseEye · {new Date().getFullYear()}</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
