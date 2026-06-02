import { useState, useEffect } from 'react';
import { TrendingUp, AlertCircle, Activity, Calendar, Target } from 'lucide-react';
import axios from 'axios';
import api from '@/lib/api';
import type { ForecastResponse } from '@/types';

interface Props {
  sessionId: string;
}

const fmt = (n: number) =>
  '₹' + n.toLocaleString(undefined, { maximumFractionDigits: 0 });

export function CashFlowForecast({ sessionId }: Props) {
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        setLoading(true);
        const res = await api.get<ForecastResponse>('/forecast', { params: { session_id: sessionId } });
        setData(res.data); setError(null);
      } catch (err: unknown) {
        if (axios.isAxiosError(err)) setError(err.response?.data?.error || 'Failed to load forecast.');
        else setError('An unexpected error occurred while loading the forecast.');
      } finally { setLoading(false); }
    };
    if (sessionId) run();
  }, [sessionId]);

  if (loading) return (
    <div className="flex justify-center p-8" role="status" aria-live="polite">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      <span className="sr-only">Loading cash-flow forecast</span>
    </div>
  );
  if (error) return (
    <div className="bg-red-50 text-red-800 p-4 rounded-lg flex items-start gap-3">
      <AlertCircle className="w-5 h-5 text-red-500 mt-0.5" /><p>{error}</p>
    </div>
  );
  if (!data?.success) return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center text-gray-500">
      <TrendingUp className="w-12 h-12 mx-auto text-gray-400 mb-3" />
      <p className="text-lg font-medium text-gray-900">Not enough data to forecast</p>
      <p className="mt-1">Upload a statement with more history to see a spending forecast.</p>
    </div>
  );

  // ----- build the monthly chart (history + 1 forecast point) -------------- //
  const hist = data.monthly.history;
  const fc = data.monthly.forecast;
  const points = [
    ...hist.map((m) => ({ label: m.month, spend: m.spend, forecast: false })),
    ...fc.map((m) => ({ label: m.month, spend: m.spend, forecast: true })),
  ];
  const W = 720, H = 220, PAD = 36;
  const maxSpend = Math.max(...points.map((p) => p.spend), 1);
  const x = (i: number) => PAD + (i * (W - 2 * PAD)) / Math.max(points.length - 1, 1);
  const y = (v: number) => H - PAD - (v / maxSpend) * (H - 2 * PAD);
  const histPts = points.filter((p) => !p.forecast);
  const histPath = histPts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(p.spend)}`).join(' ');
  const lastHistIdx = histPts.length - 1;
  const acc = data.accuracy;

  return (
    <div className="space-y-6">
      {/* headline numbers */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-blue-50 p-4 rounded-xl border border-blue-100 shadow-sm flex flex-col">
          <div className="flex items-center gap-2 text-blue-600 mb-2"><Calendar className="w-4 h-4" /><span className="text-sm font-medium">Next 30 Days (forecast)</span></div>
          <span className="text-3xl font-bold text-blue-700">{fmt(data.next_30_day_total)}</span>
        </div>
        <div className="bg-indigo-50 p-4 rounded-xl border border-indigo-100 shadow-sm flex flex-col">
          <div className="flex items-center gap-2 text-indigo-600 mb-2"><Target className="w-4 h-4" /><span className="text-sm font-medium">Next Month (forecast)</span></div>
          <span className="text-3xl font-bold text-indigo-700">{fmt(data.next_month_total)}</span>
        </div>
        <div className="bg-gray-50 p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col">
          <div className="flex items-center gap-2 text-gray-600 mb-2"><Activity className="w-4 h-4" /><span className="text-sm font-medium">History</span></div>
          <span className="text-3xl font-bold text-gray-800">{data.history_months} mo</span>
          <span className="text-xs text-gray-500 mt-1">{data.history_days} days of data</span>
        </div>
      </div>

      {/* chart */}
      <div className="rounded-xl border border-gray-200 shadow-sm p-4 bg-white">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-semibold text-gray-700">Monthly Spend — history &amp; forecast</h4>
          <span className="text-xs text-gray-500">{data.method}</span>
        </div>
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label="Monthly spend history and forecast">
          {/* baseline */}
          <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#e5e7eb" />
          {/* history line */}
          <path d={histPath} fill="none" stroke="#2563eb" strokeWidth={2} />
          {/* forecast connector + point */}
          {fc.length > 0 && (
            <>
              <line
                x1={x(lastHistIdx)} y1={y(histPts[lastHistIdx].spend)}
                x2={x(points.length - 1)} y2={y(points[points.length - 1].spend)}
                stroke="#6366f1" strokeWidth={2} strokeDasharray="5 4"
              />
              <circle cx={x(points.length - 1)} cy={y(points[points.length - 1].spend)} r={5} fill="#6366f1" />
            </>
          )}
          {/* history points */}
          {histPts.map((p, i) => (
            <circle key={i} cx={x(i)} cy={y(p.spend)} r={2.5} fill="#2563eb" />
          ))}
        </svg>
        <div className="flex items-center gap-4 text-xs text-gray-500 mt-1">
          <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5 bg-blue-600" /> Historical</span>
          <span className="flex items-center gap-1"><span className="inline-block w-3 h-0.5 border-t-2 border-dashed border-indigo-500" /> Forecast</span>
        </div>
      </div>

      {/* accuracy */}
      {acc && (
        <div className="rounded-xl border border-gray-200 bg-gray-50/60 p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Forecast Accuracy (back-test)</h4>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{acc.mape != null ? acc.mape.toFixed(1) + '%' : '—'}</div>
              <div className="text-xs text-gray-500 uppercase tracking-wide">MAPE</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{fmt(acc.mae)}</div>
              <div className="text-xs text-gray-500 uppercase tracking-wide">MAE</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{fmt(acc.rmse)}</div>
              <div className="text-xs text-gray-500 uppercase tracking-wide">RMSE</div>
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-3">{acc.basis}{acc.holdout_months ? ` · ${acc.holdout_months}-month holdout` : ''}</p>
        </div>
      )}
    </div>
  );
}
