import { useState, useEffect } from 'react';
import { ShieldAlert, CheckCircle } from 'lucide-react';
import axios from 'axios';
import api from '@/lib/api';
import type { AnomaliesResponse } from '@/types';
import { inr as fmt } from '@/lib/utils';
import { Loading, ErrorState, Empty } from './States';

interface Props {
  sessionId: string;
}

export function AnomalyDetection({ sessionId }: Props) {
  const [data, setData] = useState<AnomaliesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        setLoading(true);
        const res = await api.get<AnomaliesResponse>('/anomalies', { params: { session_id: sessionId } });
        setData(res.data); setError(null);
      } catch (err: unknown) {
        if (axios.isAxiosError(err)) setError(err.response?.data?.error || 'Failed to load anomalies.');
        else setError('An unexpected error occurred while detecting anomalies.');
      } finally { setLoading(false); }
    };
    if (sessionId) run();
  }, [sessionId]);

  if (loading) return <Loading label="Scanning for anomalies…" />;
  if (error) return <ErrorState message={error} />;
  if (!data?.success) return <Empty icon={ShieldAlert} title="No data to analyze" />;

  if (data.anomaly_count === 0) return (
    <div className="state-block border-success/25 bg-success/[0.06]">
      <CheckCircle className="mx-auto mb-3 h-8 w-8 text-success" />
      <p className="text-[15px] font-medium text-txt">Nothing unusual</p>
      <p className="mx-auto mt-1.5 max-w-md text-sm text-txt-muted">
        Scanned {data.total_transactions} transactions with {data.method}.
      </p>
    </div>
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-sm">
        <p className="text-txt-muted">
          <span className="font-mono font-semibold text-danger">{data.anomaly_count}</span> unusual of {data.total_transactions}
        </p>
        <span className="font-mono text-[11px] text-txt-faint">{data.method} · z &gt; {data.z_threshold}</span>
      </div>
      <div className="-mx-1 overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              {['Date', 'Description', 'Category', 'Amount', 'Z', 'Why flagged'].map((h, i) => (
                <th key={i} scope="col" className={`data-th ${i === 3 || i === 4 ? 'text-right' : 'text-left'}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.anomalies.map((a, i) => (
              <tr key={i} className="border-t border-line transition-colors hover:bg-danger/[0.06]">
                <td className="px-4 py-3 whitespace-nowrap font-mono text-[13px] text-txt-muted">{a.txn_date}</td>
                <td className="px-4 py-3 text-[13px] font-medium text-txt">{a.description}</td>
                <td className="px-4 py-3 text-[13px] capitalize text-txt-muted">{a.category}</td>
                <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-[13px] text-txt">{fmt(a.spend)}</td>
                <td className="px-4 py-3 whitespace-nowrap text-right font-mono text-[13px] font-semibold text-danger">{a.z_score.toFixed(1)}</td>
                <td className="max-w-xs px-4 py-3 text-[12px] text-txt-muted">{a.explanation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
