import { useState, useEffect } from 'react';
import { ArrowsClockwise, CheckCircle } from '@phosphor-icons/react';
import axios from 'axios';
import api from '@/lib/api';
import type { ReconcileResponse } from '@/types';
import { cn, inr } from '@/lib/utils';
import { Counter } from './Counter';
import { ErrorState, Empty, SkeletonKpiTable } from './States';

interface Props {
  sessionId: string;
}

/**
 * Reconciliation read-out: every charge the statement said should recur, matched
 * against what actually landed. The headline is the match rate over the whole
 * expected batch; below it, the two-sided exception list — expected charges that
 * never arrived, and recurring-merchant charges no schedule accounts for. Uses
 * the existing KPI strip / data-table primitives so it reads as one more module
 * on the board, not a new surface.
 */
export function Reconciliation({ sessionId }: Props) {
  const [data, setData] = useState<ReconcileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        setLoading(true);
        const res = await api.get<ReconcileResponse>('/reconcile', {
          headers: { 'X-Session-Id': sessionId },
        });
        setData(res.data);
        setError(null);
      } catch (err: unknown) {
        if (axios.isAxiosError(err)) setError(err.response?.data?.error || 'Failed to reconcile.');
        else setError('An unexpected error occurred while reconciling.');
      } finally {
        setLoading(false);
      }
    };
    if (sessionId) run();
  }, [sessionId]);

  if (loading) return <SkeletonKpiTable label="Reconciling expected charges…" cols={5} rows={4} />;
  if (error) return <ErrorState message={error} />;
  if (!data?.success) return (
    <Empty icon={ArrowsClockwise} title="Nothing to reconcile">
      No recurring series were detected, so there is no expected ledger to check against.
    </Empty>
  );

  const s = data.summary;
  const missing = data.exceptions.missing;
  const unscheduled = data.exceptions.unscheduled;
  const exceptionCount = missing.length + unscheduled.length;

  return (
    <div className="space-y-6">
      {/* headline: match rate over the whole expected batch */}
      <div className="grid grid-cols-1 divide-y divide-line rounded-md border border-line sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        <div className="p-4">
          <div className="kpi-label"><ArrowsClockwise className="h-3.5 w-3.5" aria-hidden="true" /><span>Match rate</span></div>
          <div className="kpi-value text-brand">
            <Counter value={s.match_rate} format={(n) => `${n.toFixed(1)}%`} />
          </div>
          <p className="mt-1 font-mono text-micro text-txt-faint">
            {s.matched}/{s.expected_occurrences} expected charges
          </p>
        </div>
        <div className="p-4">
          <div className="kpi-label text-danger"><span>Missing</span></div>
          <div className="kpi-value text-danger"><Counter value={s.missing} /></div>
          <p className="mt-1 font-mono text-micro text-txt-faint">never landed</p>
        </div>
        <div className="p-4">
          <div className="kpi-label text-warning"><span>Unscheduled</span></div>
          <div className="kpi-value text-warning"><Counter value={s.unscheduled} /></div>
          <p className="mt-1 font-mono text-micro text-txt-faint">off-cycle or duplicate</p>
        </div>
      </div>

      {/* per-series ledger */}
      <div className="-mx-1 overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              {['Merchant', 'Cadence', 'Expected', 'Matched', 'Missing'].map((h, i) => (
                <th key={i} scope="col" className={`data-th ${i === 0 ? 'text-left' : i === 1 ? 'text-center' : 'text-right'}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.series.map((row, idx) => (
              <tr key={idx} className="data-row border-t border-line transition-all duration-150 ease-out hover:bg-tint-2">
                <td className="px-4 py-3 whitespace-nowrap text-data font-medium text-txt">
                  {row.merchant}
                  {row.lapsed && (
                    <span className="ml-2 font-mono text-micro uppercase tracking-wider text-txt-faint">lapsed</span>
                  )}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-center">
                  <span className="tag border border-accent/30 bg-accent/10 text-accent-light">{row.frequency}</span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-data tabular-nums text-txt-muted">{row.expected}</td>
                <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-data tabular-nums text-brand">{row.matched}</td>
                <td className={cn(
                  'px-4 py-3 whitespace-nowrap text-right font-mono text-data font-medium tabular-nums',
                  row.missing > 0 ? 'text-danger' : 'text-txt-faint'
                )}>
                  {row.missing > 0 ? row.missing : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* the honest exception list: everything the loop could not resolve */}
      {exceptionCount === 0 ? (
        <div className="state-block border-success/25 bg-success/[0.06]">
          <CheckCircle className="mx-auto mb-3 h-8 w-8 text-success" aria-hidden="true" />
          <p className="text-base font-medium text-txt">Every expected charge accounted for</p>
          <p className="mx-auto mt-1.5 max-w-md text-sm text-txt-muted">
            {s.expected_occurrences} expected occurrences across {s.series_reconciled} series, with no
            exceptions outstanding.
          </p>
        </div>
      ) : (
        <div className="inset p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-data font-semibold text-txt">Exceptions it could not resolve</h3>
            <span className="font-mono text-micro text-txt-faint">{exceptionCount} open</span>
          </div>
          <ul className="space-y-1.5 font-mono text-micro">
            {missing.map((m, i) => (
              <li key={`m-${i}`} className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                <span className="shrink-0 uppercase tracking-wider text-danger">missing</span>
                <span className="text-txt">{m.merchant}</span>
                <span className="text-txt-muted">expected {m.expected_date}</span>
                <span className="tabular-nums text-txt-faint">{inr(Math.abs(m.expected_amount))}</span>
              </li>
            ))}
            {unscheduled.map((u, i) => (
              <li key={`u-${i}`} className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                <span className="shrink-0 uppercase tracking-wider text-warning">unscheduled</span>
                <span className="text-txt">{u.merchant}</span>
                <span className="text-txt-muted">on {u.txn_date}</span>
                <span className="tabular-nums text-txt-faint">{inr(Math.abs(u.amount))}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="font-mono text-micro text-txt-faint">{data.method}</p>
    </div>
  );
}
