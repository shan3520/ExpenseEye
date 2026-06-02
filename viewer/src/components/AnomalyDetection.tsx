import { useState, useEffect } from 'react';
import { ShieldAlert, AlertCircle, CheckCircle } from 'lucide-react';
import axios from 'axios';
import api from '@/lib/api';
import type { AnomaliesResponse } from '@/types';

interface Props {
  sessionId: string;
}

const fmt = (n: number) => '₹' + n.toLocaleString(undefined, { maximumFractionDigits: 0 });

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

  if (loading) return (
    <div className="flex justify-center p-8" role="status" aria-live="polite">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      <span className="sr-only">Detecting anomalies</span>
    </div>
  );
  if (error) return (
    <div className="bg-red-50 text-red-800 p-4 rounded-lg flex items-start gap-3">
      <AlertCircle className="w-5 h-5 text-red-500 mt-0.5" /><p>{error}</p>
    </div>
  );
  if (!data?.success) return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center text-gray-500">
      <ShieldAlert className="w-12 h-12 mx-auto text-gray-400 mb-3" />
      <p className="text-lg font-medium text-gray-900">No data to analyze</p>
    </div>
  );

  if (data.anomaly_count === 0) return (
    <div className="bg-green-50 border border-green-100 rounded-lg p-8 text-center">
      <CheckCircle className="w-12 h-12 mx-auto text-green-500 mb-3" />
      <p className="text-lg font-medium text-gray-900">No unusual transactions found</p>
      <p className="mt-1 text-gray-500">Scanned {data.total_transactions} transactions with {data.method}.</p>
    </div>
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          <span className="font-semibold text-red-600">{data.anomaly_count}</span> unusual of {data.total_transactions} transactions
        </p>
        <span className="text-xs text-gray-400">{data.method} · z &gt; {data.z_threshold}</span>
      </div>
      <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {['Date', 'Description', 'Category', 'Amount', 'Z-score', 'Why flagged'].map((h, i) => (
                <th key={i} className={`px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${i === 3 || i === 4 ? 'text-right' : 'text-left'}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {data.anomalies.map((a, i) => (
              <tr key={i} className="bg-red-50/40 hover:bg-red-50">
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">{a.txn_date}</td>
                <td className="px-4 py-3 text-sm font-medium text-gray-900">{a.description}</td>
                <td className="px-4 py-3 text-sm text-gray-600 capitalize">{a.category}</td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-900">{fmt(a.spend)}</td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-right font-semibold text-red-600">{a.z_score.toFixed(1)}</td>
                <td className="px-4 py-3 text-xs text-gray-500 max-w-xs">{a.explanation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
