import { useState, useEffect } from 'react';
import { Calendar } from '@phosphor-icons/react';
import axios from 'axios';
import api from '@/lib/api';
import type { SubscriptionsResponse } from '@/types';
import { cn, inr } from '@/lib/utils';
import { ErrorState, Empty, SkeletonTablePanel } from './States';

interface SubscriptionsTableProps {
  sessionId: string;
}

/**
 * Map a merchant name to a category accent. The API doesn't label
 * subscriptions, so this is a lightweight client-side heuristic purely for the
 * leading colour dot — streaming, software, finance, else neutral. Tokens only.
 */
function categoryDot(description: string): string {
  const d = description.toLowerCase();
  if (/netflix|spotify|hotstar|prime|disney|youtube|hulu|hbo|max|jiocinema|sony ?liv|zee|audible|apple ?music/.test(d)) return 'bg-brand';
  if (/adobe|microsoft|office ?365|google|github|figma|notion|slack|zoom|dropbox|icloud|canva|openai|chatgpt/.test(d)) return 'bg-accent';
  if (/insurance|loan|emi|sip|mutual|premium|policy|finance|invest|broker|nps/.test(d)) return 'bg-success';
  return 'bg-txt-faint';
}

export function SubscriptionsTable({ sessionId }: SubscriptionsTableProps) {
  const [data, setData] = useState<SubscriptionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSubscriptions = async () => {
      try {
        setLoading(true);
        const response = await api.get<SubscriptionsResponse>('/subscriptions', { headers: { 'X-Session-Id': sessionId } });
        setData(response.data); setError(null);
      } catch (err: unknown) {
        if (axios.isAxiosError(err)) setError(err.response?.data?.error || "Failed to fetch subscriptions.");
        else setError("An unexpected error occurred while fetching subscriptions.");
      } finally { setLoading(false); }
    };
    if (sessionId) fetchSubscriptions();
  }, [sessionId]);

  if (loading) return <SkeletonTablePanel label="Detecting recurring payments…" cols={5} rows={4} />;
  if (error) return <ErrorState message={error} />;
  if (!data?.success || data.count === 0) return (
    <Empty icon={Calendar} title="No recurring subscriptions found">
      We couldn't detect any regular recurring payments in this statement.
    </Empty>
  );

  return (
    <div className="space-y-4">
      {/* Instrument-style header: mono label + a brand count pill on the right. */}
      <div className="flex items-center justify-between">
        <span className="font-mono text-micro uppercase tracking-wider text-txt-faint">Recurring detected</span>
        <span className="inline-flex items-center rounded-full bg-brand/10 px-2.5 py-0.5 font-mono text-micro font-semibold tabular-nums text-brand">
          {data.count}
        </span>
      </div>
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
              <tr key={idx} className="data-row transition-all duration-150 ease-out hover:bg-tint-2">
                <td className="px-4 py-3 whitespace-nowrap text-data font-medium text-txt">
                  <span className={cn('mr-2.5 inline-block h-1.5 w-1.5 rounded-full align-middle', categoryDot(sub.description))} aria-hidden="true" />
                  {sub.description}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-data font-medium tabular-nums text-brand">{inr(Math.abs(sub.amount), 2)}</td>
                <td className="px-4 py-3 whitespace-nowrap text-right">
                  <span className="tag border border-accent/30 bg-accent/10 text-accent-light">{sub.frequency}</span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-data tabular-nums text-txt-muted">{sub.avg_gap.toFixed(1)}d</td>
                <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-data tabular-nums text-txt-muted">{sub.occurrences}×</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
