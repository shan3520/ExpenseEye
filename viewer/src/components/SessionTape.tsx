import { useEffect, useState } from 'react';
import { Lock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SessionTapeProps {
  sessionId: string;
  /** Nav label of the module currently in view (from scroll-spy). */
  activeLabel: string;
  moduleCount: number;
}

/** Short, stable, human-scannable handle for a session id. */
export function shortId(id: string): string {
  const clean = id.replace(/[^a-z0-9]/gi, '');
  return (clean.slice(0, 8) || 'SESSION').toUpperCase();
}

function formatUptime(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  const pad = (n: number) => String(n).padStart(2, '0');
  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
}

/**
 * The Vault Terminal signature: a slim telemetry strip pinned to the top of the
 * console. Reads like a hardware status line — live indicator, session handle,
 * uptime, the module currently in view, and a standing privacy assurance. Mono,
 * uppercase, hairline-celled. Sticky on desktop; scrolls away on mobile to keep
 * clear of the mobile top bar.
 */
export function SessionTape({ sessionId, activeLabel, moduleCount }: SessionTapeProps) {
  const [uptime, setUptime] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => setUptime((s) => s + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  // `flash` marks values whose change is meaningful enough to pulse (the module
  // in view). Uptime ticks every second, so it stays steady — flashing it would
  // be noise, not signal.
  const cells: { key: string; val: string; valClass?: string; flash?: boolean }[] = [
    { key: 'SES', val: shortId(sessionId) },
    { key: 'UP', val: formatUptime(uptime) },
    { key: 'MOD', val: activeLabel, valClass: 'text-brand', flash: true },
    { key: 'LOADED', val: `${moduleCount} modules` },
  ];

  return (
    <div className="relative z-10 overflow-hidden border-b border-line bg-header backdrop-blur-sm lg:sticky lg:top-0">
      {/* Slow phosphor scan — a barely-visible sweep across the strip, like a CRT. */}
      <div className="tape-sweep pointer-events-none absolute inset-0" aria-hidden="true" />
      <div className="relative flex h-9 items-center overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {/* live state — always first, never scrolls past the rail */}
        <div className="flex shrink-0 items-center gap-2 pl-4 pr-3.5">
          <span className="live-dot" aria-hidden="true" />
          <span className="font-mono text-micro font-semibold uppercase tracking-wider text-brand">Live</span>
        </div>

        {cells.map((c) => (
          <div key={c.key} className="tape-cell border-l border-line">
            <span className="tape-key">{c.key}</span>
            {/* Re-key flashing values on change so the pulse animation replays. */}
            <span
              key={c.flash ? c.val : undefined}
              className={cn('readout', c.valClass ?? 'tape-val', c.flash && 'animate-tape-flash')}
            >
              {c.val}
            </span>
          </div>
        ))}

        {/* standing privacy assurance, pushed to the right edge */}
        <div className="ml-auto flex shrink-0 items-center gap-1.5 border-l border-line py-1 pl-3.5 pr-4 font-mono text-micro uppercase tracking-wider text-txt-faint">
          <Lock className="h-3 w-3 text-brand/70" aria-hidden="true" />
          <span>Local · nothing stored</span>
        </div>
      </div>
    </div>
  );
}
