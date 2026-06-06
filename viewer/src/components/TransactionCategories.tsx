import { useState, useEffect } from 'react';
import { Tags, ChevronDown, Cpu, BookOpen } from 'lucide-react';
import axios from 'axios';
import api from '@/lib/api';
import type { CategorizeResponse, ModelCardResponse } from '@/types';
import { inr as fmt } from '@/lib/utils';
import { Loading, ErrorState, Empty } from './States';

interface Props {
  sessionId: string;
}

export function TransactionCategories({ sessionId }: Props) {
  const [data, setData] = useState<CategorizeResponse | null>(null);
  const [card, setCard] = useState<ModelCardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCard, setShowCard] = useState(false);

  useEffect(() => {
    const run = async () => {
      try {
        setLoading(true);
        const [c, mc] = await Promise.all([
          api.get<CategorizeResponse>('/categorize', { params: { session_id: sessionId } }),
          api.get<ModelCardResponse>('/model-card'),
        ]);
        setData(c.data);
        setCard(mc.data.success ? mc.data : null);
        setError(null);
      } catch (err: unknown) {
        if (axios.isAxiosError(err)) setError(err.response?.data?.error || 'Failed to categorize transactions.');
        else setError('An unexpected error occurred while categorizing transactions.');
      } finally { setLoading(false); }
    };
    if (sessionId) run();
  }, [sessionId]);

  if (loading) return <Loading label="Categorizing transactions…" />;
  if (error) return <ErrorState message={error} />;
  if (!data?.success) return <Empty icon={Tags} title="No transactions to categorize" />;

  const modelPct = data.counts.total ? Math.round((data.counts.model / data.counts.total) * 100) : 0;
  const maxSpend = Math.max(...data.breakdown.map((b) => b.total_spend), 1);

  return (
    <div className="space-y-6">
      {/* coverage summary */}
      <div className="grid grid-cols-1 divide-y divide-line rounded-md border border-line sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        <div className="p-4">
          <div className="kpi-label"><Cpu className="h-3.5 w-3.5" /><span>Model coverage</span></div>
          <div className="kpi-value text-brand">{modelPct}%</div>
          <p className="mt-1 font-mono text-[11px] text-txt-faint">{data.counts.model}/{data.counts.total} classified</p>
        </div>
        <div className="p-4">
          <div className="kpi-label"><BookOpen className="h-3.5 w-3.5" /><span>Rule fallback</span></div>
          <div className="kpi-value">{data.counts.rule_fallback}</div>
          <p className="mt-1 font-mono text-[11px] text-txt-faint">low-confidence rows</p>
        </div>
        <div className="p-4">
          <div className="kpi-label"><Tags className="h-3.5 w-3.5" /><span>Categories</span></div>
          <div className="kpi-value">{data.breakdown.length}</div>
          <p className="mt-1 font-mono text-[11px] text-txt-faint">detected</p>
        </div>
      </div>

      {/* spend breakdown — labelled bars read better than a 2-col table */}
      <div className="space-y-2.5">
        {data.breakdown.map((b, i) => (
          <div key={i} className="grid grid-cols-[10rem_1fr_auto] items-center gap-3 sm:grid-cols-[12rem_1fr_auto]">
            <span className="truncate text-sm font-medium capitalize text-txt">{b.category}</span>
            <span className="h-1.5 overflow-hidden rounded-full bg-tint-2">
              <span
                className="block h-full rounded-full bg-brand/70"
                style={{ width: `${Math.max((b.total_spend / maxSpend) * 100, 2)}%` }}
              />
            </span>
            <span className="text-right font-mono text-sm tabular-nums text-txt-muted">{fmt(b.total_spend)}</span>
          </div>
        ))}
      </div>

      {/* model card expander */}
      {card && (
        <div className="inset overflow-hidden">
          <button
            onClick={() => setShowCard((v) => !v)}
            className="flex w-full items-center justify-between px-4 py-3 text-[13px] font-semibold text-txt transition-colors hover:bg-tint-2 cursor-pointer"
          >
            <span className="flex items-center gap-2"><Cpu className="h-4 w-4 text-txt-faint" /> Model card &amp; evaluation</span>
            <ChevronDown className={`h-4 w-4 text-txt-faint transition-transform ${showCard ? 'rotate-180' : ''}`} />
          </button>
          {showCard && (
            <div className="space-y-4 border-t border-line p-4">
              <p className="text-xs text-txt-muted">
                <span className="font-mono text-txt">{card.model}</span> · {card.n_samples} labeled samples · {card.n_classes} categories
              </p>
              <div className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-line bg-line md:grid-cols-4">
                {[
                  ['Accuracy', card.metrics.accuracy],
                  ['Precision', card.metrics.macro_precision],
                  ['Recall', card.metrics.macro_recall],
                  ['F1', card.metrics.macro_f1],
                ].map(([label, val]) => (
                  <div key={label as string} className="bg-panel p-3">
                    <div className="font-mono text-lg font-semibold text-accent-light">{((val as number) * 100).toFixed(1)}%</div>
                    <div className="font-mono text-[10px] uppercase tracking-wider text-txt-faint">{label}</div>
                  </div>
                ))}
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead>
                    <tr className="text-txt-faint">
                      <th scope="col" className="py-1.5 pr-4 text-left font-medium">Category</th>
                      <th scope="col" className="px-2 text-right font-medium">Prec.</th>
                      <th scope="col" className="px-2 text-right font-medium">Recall</th>
                      <th scope="col" className="px-2 text-right font-medium">F1</th>
                      <th scope="col" className="pl-2 text-right font-medium">Support</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(card.per_class).map(([cat, m]) => (
                      <tr key={cat} className="border-t border-line">
                        <td className="py-1.5 pr-4 capitalize text-txt-muted">{cat}</td>
                        <td className="px-2 text-right font-mono text-txt-muted">{(m.precision * 100).toFixed(0)}%</td>
                        <td className="px-2 text-right font-mono text-txt-muted">{(m.recall * 100).toFixed(0)}%</td>
                        <td className="px-2 text-right font-mono text-txt-muted">{(m.f1 * 100).toFixed(0)}%</td>
                        <td className="pl-2 text-right font-mono text-txt-faint">{m.support}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
