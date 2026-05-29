import { useState, useEffect } from 'react';
import { Calendar, AlertCircle } from 'lucide-react';
import axios from 'axios';
import api from '@/lib/api';
import type { SubscriptionsResponse } from '@/types';

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

  if (loading) return (
    <div className="flex justify-center p-8" role="status" aria-live="polite">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      <span className="sr-only">Loading...</span>
    </div>
  );
  if (error) return (
    <div className="bg-red-50 text-red-800 p-4 rounded-lg flex items-start gap-3">
      <AlertCircle className="w-5 h-5 text-red-500 mt-0.5" /><p>{error}</p>
    </div>
  );
  if (!data?.success || data.count === 0) return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center text-gray-500">
      <Calendar className="w-12 h-12 mx-auto text-gray-400 mb-3" />
      <p className="text-lg font-medium text-gray-900">No recurring subscriptions found</p>
      <p className="mt-1">We couldn't detect any regular recurring payments in your data.</p>
    </div>
  );

  return (
    <div className="space-y-4">
      <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg flex items-center gap-2">
        <span className="font-semibold">{data.count}</span> recurring subscription(s) detected.
      </div>
      <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {['Description','Amount','Frequency','Avg Gap (days)','Occurrences'].map((h,i) => (
                <th key={i} scope="col" className={`px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${i===0?'text-left':'text-right'}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {data.subscriptions.map((sub, idx) => (
              <tr key={idx} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{sub.description}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">₹{Math.abs(sub.amount).toFixed(2)}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">{sub.frequency}</span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">{sub.avg_gap.toFixed(1)}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">{sub.occurrences}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
