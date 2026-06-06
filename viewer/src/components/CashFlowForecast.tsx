import { useState, useEffect } from 'react';
import { TrendingUp, Activity, Calendar, Target } from 'lucide-react';
import axios from 'axios';
import api from '@/lib/api';
import type { ForecastResponse } from '@/types';
import { inr as fmt } from '@/lib/utils';
import { Loading, ErrorState, Empty } from './States';

interface Props {
  sessionId: string;
}

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

  if (loading) return <Loading label="Forecasting cash flow…" />;
  if (error) return <ErrorState message={error} />;
  if (!data?.success) return (
    <Empty icon={TrendingUp} title="Not enough data to forecast">
      Upload a statement with more history to see a spending forecast.
    </Empty>
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
  // A trend line needs at least two history points; with less, the chart is just
  // an empty box with a lone dot — show a note instead.
  const hasTrend = histPts.length >= 2;
  const acc = data.accuracy;

  return (
    <div className="space-y-6">
      {/* headline numbers — KPI strip with hairline dividers, not boxes */}
      <div className="grid grid-cols-1 divide-y divide-line rounded-md border border-line sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        <div className="p-4">
          <div className="kpi-label text-info"><Calendar className="h-3.5 w-3.5" /><span>Next 30 days</span></div>
          <div className="kpi-value text-info">{fmt(data.next_30_day_total)}</div>
        </div>
        <div className="p-4">
          <div className="kpi-label text-accent-light"><Target className="h-3.5 w-3.5" /><span>Next month</span></div>
          <div className="kpi-value text-accent-light">{fmt(data.next_month_total)}</div>
        </div>
        <div className="p-4">
          <div className="kpi-label"><Activity className="h-3.5 w-3.5" /><span>History</span></div>
          <div className="kpi-value">{data.history_months}<span className="ml-1 text-base text-txt-faint">mo</span></div>
          <p className="mt-1 font-mono text-[11px] text-txt-faint">{data.history_days} days of data</p>
        </div>
      </div>

      {/* chart */}
      <div className="inset p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-[13px] font-semibold text-txt">Monthly spend · history &amp; forecast</h3>
          <span className="font-mono text-[11px] text-txt-faint">{data.method}</span>
        </div>
        {hasTrend ? (
          <>
            <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Monthly spend history and forecast">
              <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="var(--line-strong)" />
              <path d={histPath} fill="none" stroke="var(--brand)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
              {fc.length > 0 && (
                <>
                  <line
                    x1={x(lastHistIdx)} y1={y(histPts[lastHistIdx].spend)}
                    x2={x(points.length - 1)} y2={y(points[points.length - 1].spend)}
                    stroke="var(--accent)" strokeWidth={2} strokeDasharray="5 4"
                  />
                  <circle cx={x(points.length - 1)} cy={y(points[points.length - 1].spend)} r={5} fill="var(--accent)" />
                </>
              )}
              {histPts.map((p, i) => (
                <circle key={i} cx={x(i)} cy={y(p.spend)} r={2.5} fill="var(--brand)" />
              ))}
            </svg>
            <div className="mt-2 flex items-center gap-4 text-[11px] text-txt-muted">
              <span className="flex items-center gap-1.5"><span className="inline-block h-0.5 w-3 bg-brand" /> Historical</span>
              <span className="flex items-center gap-1.5"><span className="inline-block w-3 border-t-2 border-dashed border-accent" /> Forecast</span>
            </div>
          </>
        ) : (
          <p className="py-6 text-center text-[13px] leading-relaxed text-txt-muted">
            Not enough history to chart a trend yet — this forecast is based on{' '}
            <span className="font-mono text-txt">{data.history_days} days</span> of data.
            Upload a statement spanning more months to see the trend line.
          </p>
        )}
      </div>

      {/* accuracy */}
      {acc && (
        <div className="inset p-4">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-[13px] font-semibold text-txt">Forecast accuracy</h3>
            <span className="font-mono text-[11px] text-txt-faint">back-test</span>
          </div>
          <div className="grid grid-cols-3 gap-4">
            {[
              ['MAPE', acc.mape != null ? acc.mape.toFixed(1) + '%' : '—'],
              ['MAE', fmt(acc.mae)],
              ['RMSE', fmt(acc.rmse)],
            ].map(([label, val]) => (
              <div key={label}>
                <div className="font-mono text-xl font-semibold text-txt">{val}</div>
                <div className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-txt-faint">{label}</div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-[11px] text-txt-faint">{acc.basis}{acc.holdout_months ? ` · ${acc.holdout_months}-month holdout` : ''}</p>
        </div>
      )}
    </div>
  );
}
