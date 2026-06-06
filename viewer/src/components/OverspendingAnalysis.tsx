import { useState, useEffect } from 'react';
import { TrendingUp, BarChart3, AlertTriangle, CheckCircle } from 'lucide-react';
import axios from 'axios';
import api from '@/lib/api';
import type { OverspendingResponse } from '@/types';
import { cn, inr } from '@/lib/utils';
import { Loading, ErrorState, Empty } from './States';

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
        const response = await api.get<OverspendingResponse>('/overspending', { params: { session_id: sessionId } });
        setData(response.data); setError(null);
      } catch (err: unknown) {
        if (axios.isAxiosError(err)) setError(err.response?.data?.error || "Failed to fetch overspending data.");
        else setError("An unexpected error occurred while fetching overspending data.");
      } finally { setLoading(false); }
    };
    if (sessionId) fetchOverspending();
  }, [sessionId]);

  if (loading) return <Loading label="Comparing against baseline…" />;
  if (error) return <ErrorState message={error} />;
  if (!data?.success || !data.months || data.months.length === 0) return (
    <Empty icon={TrendingUp} title="Insufficient data">
      Needs at least four months: a three-month baseline plus one month to analyze.
    </Empty>
  );

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 divide-x divide-line rounded-md border border-line">
        <div className="p-4">
          <div className="kpi-label"><BarChart3 className="h-3.5 w-3.5" /><span>Analyzed</span></div>
          <div className="kpi-value">{data.summary.total_analyzed}</div>
        </div>
        <div className="p-4">
          <div className="kpi-label text-danger"><AlertTriangle className="h-3.5 w-3.5" /><span>Over</span></div>
          <div className="kpi-value text-danger">{data.summary.overspending_count}</div>
        </div>
        <div className="p-4">
          <div className="kpi-label text-success"><CheckCircle className="h-3.5 w-3.5" /><span>Normal</span></div>
          <div className="kpi-value text-success">{data.summary.normal_count}</div>
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
                <tr key={idx} className={cn('border-t border-line transition-colors', isOverspending ? 'hover:bg-danger/[0.06]' : 'hover:bg-tint-2')}>
                  <td className="px-4 py-3 whitespace-nowrap text-[13px] font-medium text-txt">
                    {isOverspending && <span className="mr-2 inline-block h-1.5 w-1.5 rounded-full bg-danger align-middle" />}
                    {month.month}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-[13px] text-txt">{inr(month.spending)}</td>
                  <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-[13px] text-txt-muted">{inr(month.avg_spending)}</td>
                  <td className={cn('px-4 py-3 whitespace-nowrap text-right font-mono text-[13px] font-medium', month.pct_deviation > 0 ? 'text-danger' : 'text-success')}>
                    {month.pct_deviation > 0 ? '+' : ''}{month.pct_deviation.toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-[13px] text-txt-muted">{month.excess > 0 ? inr(month.excess) : '—'}</td>
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
