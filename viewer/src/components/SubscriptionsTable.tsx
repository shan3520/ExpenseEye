import { useState, useEffect } from 'react';
import { Calendar } from 'lucide-react';
import axios from 'axios';
import api from '@/lib/api';
import type { SubscriptionsResponse } from '@/types';
import { inr } from '@/lib/utils';
import { Loading, ErrorState, Empty } from './States';

interface SubscriptionsTableProps {
  sessionId: string;
}

export function SubscriptionsTable({ sessionId }: SubscriptionsTableProps) {
  const [data, setData] = useState<SubscriptionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSubscriptions = async () => {
      try {
        setLoading(true);
        const response = await api.get<SubscriptionsResponse>('/subscriptions', { params: { session_id: sessionId } });
        setData(response.data); setError(null);
      } catch (err: unknown) {
        if (axios.isAxiosError(err)) setError(err.response?.data?.error || "Failed to fetch subscriptions.");
        else setError("An unexpected error occurred while fetching subscriptions.");
      } finally { setLoading(false); }
    };
    if (sessionId) fetchSubscriptions();
  }, [sessionId]);

  if (loading) return <Loading label="Detecting recurring payments…" />;
  if (error) return <ErrorState message={error} />;
  if (!data?.success || data.count === 0) return (
    <Empty icon={Calendar} title="No recurring subscriptions found">
      We couldn't detect any regular recurring payments in this statement.
    </Empty>
  );

  return (
    <div className="space-y-4">
      <p className="text-sm text-txt-muted">
        <span className="font-mono font-semibold text-brand">{data.count}</span> recurring payment{data.count === 1 ? '' : 's'} detected
      </p>
      <div className="-mx-1 overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              {['Description', 'Amount', 'Frequency', 'Avg gap', 'Seen'].map((h, i) => (
                <th key={i} scope="col" className={`data-th ${i === 0 ? 'text-left' : 'text-right'}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.subscriptions.map((sub, idx) => (
              <tr key={idx} className="data-row">
                <td className="px-4 py-3 whitespace-nowrap text-[13px] font-medium text-txt">{sub.description}</td>
                <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-[13px] text-txt">{inr(Math.abs(sub.amount), 2)}</td>
                <td className="px-4 py-3 whitespace-nowrap text-right">
                  <span className="tag border border-accent/30 bg-accent/10 text-accent-light">{sub.frequency}</span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-[13px] text-txt-muted">{sub.avg_gap.toFixed(1)}d</td>
                <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-[13px] text-txt-muted">{sub.occurrences}×</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
