import { useState, useEffect } from 'react';
import { TrendingUp, AlertCircle, BarChart3, AlertTriangle, CheckCircle } from 'lucide-react';
import axios from 'axios';
import api from '@/lib/api';
import type { OverspendingResponse } from '@/types';
import { cn } from '@/lib/utils';

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

  if (loading) return (
    <div className="flex justify-center p-8" role="status" aria-live="polite">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      <span className="sr-only">Loading overspending analysis</span>
    </div>
  );
  if (error) return (
    <div className="bg-red-50 text-red-800 p-4 rounded-lg flex items-start gap-3">
      <AlertCircle className="w-5 h-5 text-red-500 mt-0.5" /><p>{error}</p>
    </div>
  );
  if (!data?.success || !data.months || data.months.length === 0) return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center text-gray-500">
      <TrendingUp className="w-12 h-12 mx-auto text-gray-400 mb-3" />
      <p className="text-lg font-medium text-gray-900">Insufficient data</p>
      <p className="mt-1">Overspending analysis requires at least 4 months of data (3-month baseline + 1 month to analyze).</p>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col">
          <div className="flex items-center gap-2 text-gray-500 mb-2"><BarChart3 className="w-4 h-4" /><span className="text-sm font-medium">Total Analyzed</span></div>
          <span className="text-3xl font-bold text-gray-900">{data.summary.total_analyzed}</span>
        </div>
        <div className="bg-red-50 p-4 rounded-xl border border-red-100 shadow-sm flex flex-col">
          <div className="flex items-center gap-2 text-red-600 mb-2"><AlertTriangle className="w-4 h-4" /><span className="text-sm font-medium">Overspending Months</span></div>
          <span className="text-3xl font-bold text-red-700">{data.summary.overspending_count}</span>
        </div>
        <div className="bg-green-50 p-4 rounded-xl border border-green-100 shadow-sm flex flex-col">
          <div className="flex items-center gap-2 text-green-600 mb-2"><CheckCircle className="w-4 h-4" /><span className="text-sm font-medium">Normal Months</span></div>
          <span className="text-3xl font-bold text-green-700">{data.summary.normal_count}</span>
        </div>
      </div>
      <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {['Month','Spending','Historical Avg','Deviation','Excess Amount','Status'].map((h,i) => (
                <th key={i} scope="col" className={`px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider ${i===0?'text-left':i===5?'text-center':'text-right'}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {data.months.map((month, idx) => {
              const isOverspending = month.status === 'OVERSPENDING';
              return (
                <tr key={idx} className={cn("transition-colors", isOverspending ? "bg-red-50/50 hover:bg-red-50" : "hover:bg-gray-50")}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{month.month}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">₹{month.spending.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">₹{month.avg_spending.toFixed(2)}</td>
                  <td className={cn("px-6 py-4 whitespace-nowrap text-sm font-medium text-right", month.pct_deviation > 0 ? "text-red-600" : "text-green-600")}>
                    {month.pct_deviation > 0 ? '+' : ''}{month.pct_deviation.toFixed(1)}%
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">{month.excess > 0 ? `₹${month.excess.toFixed(2)}` : '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                    <span className={cn("inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                      isOverspending ? "bg-red-100 text-red-800" : "bg-green-100 text-green-800")}>
                      {month.status}
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
