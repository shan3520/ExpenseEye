import { useState, useEffect } from 'react';
import { Tags, AlertCircle, ChevronDown, Cpu, BookOpen } from 'lucide-react';
import axios from 'axios';
import api from '@/lib/api';
import type { CategorizeResponse, ModelCardResponse } from '@/types';

interface Props {
  sessionId: string;
}

const fmt = (n: number) => '₹' + n.toLocaleString(undefined, { maximumFractionDigits: 0 });

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

  if (loading) return (
    <div className="flex justify-center p-8" role="status" aria-live="polite">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      <span className="sr-only">Categorizing transactions</span>
    </div>
  );
  if (error) return (
    <div className="bg-red-50 text-red-800 p-4 rounded-lg flex items-start gap-3">
      <AlertCircle className="w-5 h-5 text-red-500 mt-0.5" /><p>{error}</p>
    </div>
  );
  if (!data?.success) return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center text-gray-500">
      <Tags className="w-12 h-12 mx-auto text-gray-400 mb-3" />
      <p className="text-lg font-medium text-gray-900">No transactions to categorize</p>
    </div>
  );

  const modelPct = data.counts.total ? Math.round((data.counts.model / data.counts.total) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* coverage summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center gap-2 text-gray-500 mb-2"><Cpu className="w-4 h-4" /><span className="text-sm font-medium">Classified by ML model</span></div>
          <span className="text-3xl font-bold text-gray-900">{modelPct}%</span>
          <span className="text-xs text-gray-500 ml-2">({data.counts.model}/{data.counts.total})</span>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center gap-2 text-gray-500 mb-2"><BookOpen className="w-4 h-4" /><span className="text-sm font-medium">Rule fallback (low confidence)</span></div>
          <span className="text-3xl font-bold text-gray-900">{data.counts.rule_fallback}</span>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center gap-2 text-gray-500 mb-2"><Tags className="w-4 h-4" /><span className="text-sm font-medium">Categories detected</span></div>
          <span className="text-3xl font-bold text-gray-900">{data.breakdown.length}</span>
        </div>
      </div>

      {/* spend breakdown */}
      <div className="rounded-lg border border-gray-200 shadow-sm overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Total Spend</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {data.breakdown.map((b, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-6 py-3 text-sm font-medium text-gray-900 capitalize">{b.category}</td>
                <td className="px-6 py-3 text-sm text-gray-700 text-right">{fmt(b.total_spend)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* model card expander */}
      {card && (
        <div className="rounded-xl border border-gray-200 overflow-hidden">
          <button
            onClick={() => setShowCard((v) => !v)}
            className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-sm font-semibold text-gray-700"
          >
            <span className="flex items-center gap-2"><Cpu className="w-4 h-4" /> Model card &amp; evaluation metrics</span>
            <ChevronDown className={`w-4 h-4 transition-transform ${showCard ? 'rotate-180' : ''}`} />
          </button>
          {showCard && (
            <div className="p-4 space-y-4">
              <p className="text-xs text-gray-500">{card.model} · trained on {card.n_samples} labeled samples across {card.n_classes} categories</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  ['Accuracy', card.metrics.accuracy],
                  ['Macro Precision', card.metrics.macro_precision],
                  ['Macro Recall', card.metrics.macro_recall],
                  ['Macro F1', card.metrics.macro_f1],
                ].map(([label, val]) => (
                  <div key={label as string} className="text-center bg-blue-50 rounded-lg py-3 border border-blue-100">
                    <div className="text-xl font-bold text-blue-700">{((val as number) * 100).toFixed(1)}%</div>
                    <div className="text-[11px] text-gray-500 uppercase tracking-wide">{label}</div>
                  </div>
                ))}
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead><tr className="text-gray-400">
                    <th className="text-left py-1 pr-4">Category</th><th className="text-right px-2">Precision</th>
                    <th className="text-right px-2">Recall</th><th className="text-right px-2">F1</th><th className="text-right pl-2">Support</th>
                  </tr></thead>
                  <tbody>
                    {Object.entries(card.per_class).map(([cat, m]) => (
                      <tr key={cat} className="border-t border-gray-100">
                        <td className="py-1 pr-4 capitalize text-gray-700">{cat}</td>
                        <td className="text-right px-2">{(m.precision * 100).toFixed(0)}%</td>
                        <td className="text-right px-2">{(m.recall * 100).toFixed(0)}%</td>
                        <td className="text-right px-2">{(m.f1 * 100).toFixed(0)}%</td>
                        <td className="text-right pl-2 text-gray-400">{m.support}</td>
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
