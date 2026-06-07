import type { ComponentType, ReactNode } from 'react';
import { WarningCircle } from '@phosphor-icons/react';
import { cn } from '@/lib/utils';

/** Shared module states — keeps every analytics panel visually consistent. */

export function ErrorState({ message }: { message: string }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-md border border-danger/25 bg-danger/[0.08] p-4 text-sm text-danger">
      <WarningCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-danger" aria-hidden="true" />
      <p>{message}</p>
    </div>
  );
}

export function Empty({
  icon: Icon,
  title,
  children,
}: {
  icon: ComponentType<{ className?: string }>;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="state-block">
      <Icon className="mx-auto mb-3 h-8 w-8 text-txt-faint" aria-hidden="true" />
      <p className="text-base font-medium text-txt">{title}</p>
      {children && <p className="mx-auto mt-1.5 max-w-md text-sm text-txt-muted">{children}</p>}
    </div>
  );
}

/* ---- Skeletons --------------------------------------------------------------
   Shape-matching loaders, not spinners: each module renders a skeleton that
   mirrors its real layout so the swap to data lands with no reflow. All blocks
   pulse via the `.skeleton` class (steady under reduced motion). The whole
   skeleton is aria-hidden behind a polite status label for assistive tech. */

/** A single pulsing block. Width/height/extra classes via `className`. */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('skeleton', className)} aria-hidden="true" />;
}

/** Wraps a skeleton tree with an SR-only live label so non-visual users still
    hear that the panel is loading. */
function SkeletonShell({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div role="status" aria-live="polite">
      <span className="sr-only">{label}</span>
      {children}
    </div>
  );
}

/** Mirrors the 3-up hairline-divided KPI strip used across modules. */
export function SkeletonKpiStrip() {
  return (
    <div className="grid grid-cols-1 divide-y divide-line rounded-md border border-line sm:grid-cols-3 sm:divide-x sm:divide-y-0">
      {[0, 1, 2].map((i) => (
        <div key={i} className="space-y-3 p-4">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-7 w-28" />
        </div>
      ))}
    </div>
  );
}

/** Mirrors a data table: a header rule plus `rows` × `cols` cells. */
export function SkeletonTable({ rows = 4, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="overflow-hidden rounded-md border border-line">
      <div className="flex gap-4 border-b border-line bg-tint-1 px-4 py-2.5">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className={cn('h-2.5', i === 0 ? 'w-24' : 'flex-1')} />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex items-center gap-4 border-t border-line px-4 py-3.5 first:border-t-0">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className={cn('h-3', c === 0 ? 'w-28' : 'flex-1')} />
          ))}
        </div>
      ))}
    </div>
  );
}

/** Forecast: KPI strip + a tall chart well + legend. */
export function SkeletonForecast() {
  return (
    <SkeletonShell label="Forecasting cash flow…">
      <div className="space-y-6">
        <SkeletonKpiStrip />
        <div className="inset space-y-3 p-4">
          <div className="flex items-center justify-between">
            <Skeleton className="h-3 w-48" />
            <Skeleton className="h-3 w-16" />
          </div>
          <Skeleton className="h-40 w-full rounded-md" />
          <div className="flex gap-4">
            <Skeleton className="h-2.5 w-20" />
            <Skeleton className="h-2.5 w-20" />
          </div>
        </div>
      </div>
    </SkeletonShell>
  );
}

/** Categories: KPI strip + labelled spend bars. */
export function SkeletonBars({ rows = 6 }: { rows?: number }) {
  return (
    <SkeletonShell label="Categorizing transactions…">
      <div className="space-y-6">
        <SkeletonKpiStrip />
        <div className="space-y-3">
          {Array.from({ length: rows }).map((_, i) => (
            <div key={i} className="grid grid-cols-[10rem_1fr_auto] items-center gap-3 sm:grid-cols-[12rem_1fr_auto]">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-1.5 w-full rounded-full" />
              <Skeleton className="h-3 w-16" />
            </div>
          ))}
        </div>
      </div>
    </SkeletonShell>
  );
}

/** A summary line above a table (anomalies, subscriptions). */
export function SkeletonTablePanel({ label, cols = 5, rows = 4 }: { label: string; cols?: number; rows?: number }) {
  return (
    <SkeletonShell label={label}>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-3 w-40" />
          <Skeleton className="h-3 w-24" />
        </div>
        <SkeletonTable rows={rows} cols={cols} />
      </div>
    </SkeletonShell>
  );
}

/** Overspending: KPI strip + table. */
export function SkeletonKpiTable({ label, cols = 6, rows = 4 }: { label: string; cols?: number; rows?: number }) {
  return (
    <SkeletonShell label={label}>
      <div className="space-y-6">
        <SkeletonKpiStrip />
        <SkeletonTable rows={rows} cols={cols} />
      </div>
    </SkeletonShell>
  );
}
