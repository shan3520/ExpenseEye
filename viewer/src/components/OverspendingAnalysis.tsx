import { useState, useEffect } from 'react';
import { TrendUp, ChartBar, Warning, CheckCircle } from '@phosphor-icons/react';
import axios from 'axios';
import api from '@/lib/api';
import type { OverspendingResponse } from '@/types';
import { cn, inr } from '@/lib/utils';
import { Counter } from './Counter';
import { ErrorState, Empty, SkeletonKpiTable } from './States';

interface OverspendingAnalysisProps {
  sessionId: string;
}

export function OverspendingAnalysis({ sessionId }: OverspendingAnalysisProps) {
  const [data, setData] = useState<OverspendingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchOverspending = async () => {
      try {
        setLoading(true);
        const response = await api.get<OverspendingResponse>('/overspending', { headers: { 'X-Session-Id': sessionId } });
        setData(response.data); setError(null);
      } catch (err: unknown) {
        if (axios.isAxiosError(err)) setError(err.response?.data?.error || "Failed to fetch overspending data.");
        else setError("An unexpected error occurred while fetching overspending data.");
      } finally { setLoading(false); }
    };
    if (sessionId) fetchOverspending();
  }, [sessionId]);

  if (loading) return <SkeletonKpiTable label="Comparing against baseline…" cols={6} rows={4} />;
  if (error) return <ErrorState message={error} />;
  if (!data?.success || !data.months || data.months.length === 0) return (
    <Empty icon={TrendUp} title="Insufficient data">
      Needs at least four months: a three-month baseline plus one month to analyze.
    </Empty>
  );

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 divide-y divide-line rounded-md border border-line sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        <div className="p-4">
          <div className="kpi-label"><ChartBar className="h-3.5 w-3.5" aria-hidden="true" /><span>Analyzed</span></div>
          <div className="kpi-value"><Counter value={data.summary.total_analyzed} /></div>
        </div>
        <div className="p-4">
          <div className="kpi-label text-danger"><Warning className="h-3.5 w-3.5" aria-hidden="true" /><span>Over</span></div>
          <div className="kpi-value text-danger"><Counter value={data.summary.overspending_count} /></div>
        </div>
        <div className="p-4">
          <div className="kpi-label text-success"><CheckCircle className="h-3.5 w-3.5" aria-hidden="true" /><span>Normal</span></div>
          <div className="kpi-value text-success"><Counter value={data.summary.normal_count} /></div>
        </div>
      </div>
      <div className="-mx-1 overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              {['Month', 'Spending', 'Baseline', 'Deviation', 'Excess', 'Status'].map((h, i) => (
                <th key={i} scope="col" className={`data-th ${i === 0 ? 'text-left' : i === 5 ? 'text-center' : 'text-right'}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.months.map((month, idx) => {
              const isOverspending = month.status === 'OVERSPENDING';
              return (
                <tr key={idx} className={cn('border-t border-line transition-all duration-150 ease-out', isOverspending ? 'hover:bg-danger/[0.06]' : 'hover:bg-tint-2')}>
                  <td className="px-4 py-3 whitespace-nowrap text-data font-medium text-txt">
                    {isOverspending && <span className="mr-2 inline-block h-1.5 w-1.5 rounded-full bg-danger align-middle" />}
                    {month.month}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-data tabular-nums text-txt">{inr(month.spending)}</td>
                  <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-data tabular-nums text-txt-muted">{inr(month.avg_spending)}</td>
                  <td className={cn('px-4 py-3 whitespace-nowrap text-right font-mono text-data font-medium tabular-nums', month.pct_deviation > 0 ? 'text-danger' : 'text-success')}>
                    {month.pct_deviation > 0 ? '+' : ''}{month.pct_deviation.toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-data tabular-nums text-txt-muted">{month.excess > 0 ? inr(month.excess) : '—'}</td>
                  <td className="px-4 py-3 whitespace-nowrap text-center">
                    <span className={cn('tag', isOverspending ? 'border border-danger/30 bg-danger/10 text-danger' : 'border border-success/30 bg-success/10 text-success')}>
                      {isOverspending ? 'Over' : 'Normal'}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
