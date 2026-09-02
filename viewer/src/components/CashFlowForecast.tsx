import { useState, useEffect } from 'react';
import { TrendUp, Pulse, Calendar, Target } from '@phosphor-icons/react';
import axios from 'axios';
import api from '@/lib/api';
import type { ForecastResponse } from '@/types';
import { inr as fmt } from '@/lib/utils';
import { Counter } from './Counter';
import { ErrorState, Empty, SkeletonForecast } from './States';

interface Props {
  sessionId: string;
}

export function CashFlowForecast({ sessionId }: Props) {
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Which chart point the pointer is over (index into `points`), or null.
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        setLoading(true);
        const res = await api.get<ForecastResponse>('/forecast', { headers: { 'X-Session-Id': sessionId } });
        setData(res.data); setError(null);
      } catch (err: unknown) {
        if (axios.isAxiosError(err)) setError(err.response?.data?.error || 'Failed to load forecast.');
        else setError('An unexpected error occurred while loading the forecast.');
      } finally { setLoading(false); }
    };
    if (sessionId) run();
  }, [sessionId]);

  if (loading) return <SkeletonForecast />;
  if (error) return <ErrorState message={error} />;
  if (!data?.success) return (
    <Empty icon={TrendUp} title="Not enough data to forecast">
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
  // Closed path under the history line, for the gradient area fill: trace the
  // line, drop to the baseline at the last point, run back along the baseline.
  const areaPath = `${histPath} L ${x(lastHistIdx)} ${H - PAD} L ${x(0)} ${H - PAD} Z`;
  // A trend line needs at least two history points; with less, the chart is just
  // an empty box with a lone dot — show a note instead.
  const hasTrend = histPts.length >= 2;
  const acc = data.accuracy;
  const fcIdx = points.length - 1;

  return (
    <div className="space-y-6">
      {/* headline numbers — KPI strip with hairline dividers, not boxes */}
      <div className="grid grid-cols-1 divide-y divide-line rounded-md border border-line sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        <div className="p-4">
          <div className="kpi-label"><Calendar className="h-3.5 w-3.5" aria-hidden="true" /><span>Next 30 days</span></div>
          <div className="kpi-value"><Counter value={data.next_30_day_total} format={fmt} /></div>
        </div>
        <div className="p-4">
          <div className="kpi-label text-accent-light"><Target className="h-3.5 w-3.5" aria-hidden="true" /><span>Next month</span></div>
          <div className="kpi-value text-accent-light"><Counter value={data.next_month_total} format={fmt} /></div>
          {/* These two used to come from two independent models and openly
              disagreed on screen (₹1,02,366 beside ₹69,594). One model now
              drives both; say so rather than leaving the reader to wonder. */}
          {data.totals_basis && (
            <p className="mt-1 font-mono text-micro text-txt-faint">same model as the 30-day figure</p>
          )}
        </div>
        <div className="p-4">
          <div className="kpi-label"><Pulse className="h-3.5 w-3.5" aria-hidden="true" /><span>History</span></div>
          <div className="kpi-value">{data.history_months}<span className="ml-1 text-base text-txt-faint">mo</span></div>
          {/* "22 mo" from "645 days" looks like bad arithmetic (645/30.4 = 21.2)
              but is not: a span starting mid-month TOUCHES 22 calendar months,
              and that count is what the monthly model has to learn from. Say
              which quantity each number is. */}
          <p className="mt-1 font-mono text-micro text-txt-faint">
            {data.history_days} days · {data.history_months} calendar months
          </p>
        </div>
      </div>

      {/* chart */}
      <div className="inset p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-data font-semibold text-txt">Monthly spend · history &amp; forecast</h3>
          <span className="font-mono text-micro text-txt-faint">{data.method}</span>
        </div>
        {hasTrend ? (
          <>
            <div className="relative">
              <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full overflow-visible" role="img" aria-label="Monthly spend history and forecast">
                <defs>
                  <linearGradient id="forecast-area-fill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--brand)" stopOpacity="0.3" />
                    <stop offset="100%" stopColor="var(--brand)" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="var(--line-strong)" />
                {/* area fill under the historical line */}
                <path d={areaPath} fill="url(#forecast-area-fill)" stroke="none" />
                <path d={histPath} fill="none" stroke="var(--brand)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
                {fc.length > 0 && (
                  <>
                    <line
                      x1={x(lastHistIdx)} y1={y(histPts[lastHistIdx].spend)}
                      x2={x(fcIdx)} y2={y(points[fcIdx].spend)}
                      stroke="var(--accent)" strokeWidth={2} strokeDasharray="5 4"
                    />
                    <circle
                      className="chart-dot"
                      cx={x(fcIdx)} cy={y(points[fcIdx].spend)}
                      r={hoveredIdx === fcIdx ? 6 : 5} fill="var(--accent)"
                      style={{ filter: 'drop-shadow(0 0 4px rgb(var(--accent-rgb) / 0.6))' }}
                    />
                  </>
                )}
                {histPts.map((p, i) => (
                  <circle key={i} className="chart-dot" cx={x(i)} cy={y(p.spend)} r={hoveredIdx === i ? 4 : 2.5} fill="var(--brand)" />
                ))}
                {/* transparent hit targets — generous radius so the tooltip is easy to trigger */}
                {points.map((p, i) => (
                  <circle
                    key={`hit-${i}`}
                    cx={x(i)} cy={y(p.spend)} r={16} fill="transparent"
                    className="cursor-pointer"
                    onMouseEnter={() => setHoveredIdx(i)}
                    onMouseLeave={() => setHoveredIdx(null)}
                  />
                ))}
              </svg>
              {hoveredIdx != null && (
                <div
                  className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-[130%] whitespace-nowrap rounded-lg border border-line bg-panel px-3 py-2 text-[12px] font-mono shadow-panel"
                  style={{ left: `${(x(hoveredIdx) / W) * 100}%`, top: `${(y(points[hoveredIdx].spend) / H) * 100}%` }}
                >
                  <div className="text-txt-faint">{points[hoveredIdx].label}</div>
                  <div className="tabular-nums text-txt">
                    {fmt(points[hoveredIdx].spend)}
                    {points[hoveredIdx].forecast && <span className="ml-1.5 text-accent">· forecast</span>}
                  </div>
                </div>
              )}
            </div>
            <div className="mt-2 flex items-center gap-4 text-micro text-txt-muted">
              <span className="flex items-center gap-1.5"><span className="inline-block h-0.5 w-3 bg-brand" /> Historical</span>
              <span className="flex items-center gap-1.5"><span className="inline-block w-3 border-t-2 border-dashed border-accent" /> Forecast</span>
            </div>
          </>
        ) : (
          <p className="py-6 text-center text-data leading-relaxed text-txt-muted">
            Not enough history to chart a trend yet. This forecast is based on{' '}
            <span className="font-mono text-txt">{data.history_days} days</span> of data;
            upload a statement spanning more months to see the trend line.
          </p>
        )}
      </div>

      {/* accuracy */}
      {acc ? (
        <div className="inset p-4">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-data font-semibold text-txt">Forecast accuracy</h3>
            <span className="font-mono text-micro text-txt-faint">back-test</span>
          </div>
          {/* Three currency figures cannot fit three columns at 375px -- MAE and
              RMSE collided with no gap. Stack them below sm and go 3-up above. */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 sm:gap-4">
            {[
              ['MAPE', acc.mape != null ? acc.mape.toFixed(1) + '%' : '—'],
              ['MAE', fmt(acc.mae)],
              ['RMSE', fmt(acc.rmse)],
            ].map(([label, val]) => (
              <div key={label}>
                <div className="font-mono text-xl font-semibold tabular-nums text-txt">{val}</div>
                <div className="mt-0.5 font-mono text-micro uppercase tracking-wider text-txt-faint">{label}</div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-micro text-txt-faint">{acc.basis}{acc.holdout_months ? ` · ${acc.holdout_months}-month holdout` : ''}</p>

          {/* One-off charges are excluded from what the model LEARNS, never
              hidden: the charges are named, and the accuracy of the model that
              was NOT used is printed beside it so the choice can be checked. */}
          {data.one_offs_excluded_from_training && data.one_offs && data.one_offs.count > 0 && (
            <div className="mt-4 rounded-md border border-line bg-tint-1 p-3">
              <p className="text-micro leading-relaxed text-txt-muted">
                <span className="font-semibold text-txt">
                  {data.one_offs.count} one-off charge{data.one_offs.count === 1 ? '' : 's'}
                </span>{' '}
                ({fmt(data.one_offs.total)}) left out of the trend — one-time spending is not
                a recurring pattern to project. {data.one_offs.count === 1 ? 'It is' : 'They are'}{' '}
                still counted in the history above and flagged under Anomalies.
              </p>
              <ul className="mt-2 space-y-1">
                {data.one_offs.charges.map((c) => (
                  <li key={`${c.date}-${c.description}`} className="flex items-baseline justify-between gap-3 font-mono text-micro">
                    <span className="truncate text-txt-faint">{c.date} · {c.description}</span>
                    <span className="shrink-0 tabular-nums text-txt-muted">{fmt(c.amount)}</span>
                  </li>
                ))}
              </ul>
              {data.accuracy_alternative?.mape != null && (
                <p className="mt-2 border-t border-line pt-2 font-mono text-micro text-txt-faint">
                  Kept in, the same back-test gives MAPE{' '}
                  <span className="text-danger">{data.accuracy_alternative.mape.toFixed(1)}%</span>
                  {' '}— which is why they are out.
                </p>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="inset p-4">
          <p className="text-data leading-relaxed text-txt-muted">
            Not enough history to back-test accuracy yet — upload a statement spanning
            more months to see MAE / RMSE / MAPE.
          </p>
        </div>
      )}
    </div>
  );
}
