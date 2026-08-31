export interface SkippedRow {
  row: number | null;
  reason: string;
  values: string[];
}

export interface UploadResponse {
  success: boolean;
  session_id: string;
  message: string;
  transactions_loaded: number;
  mapping_info: {
    date_column: string;
    date_format: string;
    description_column: string;
    amount_pattern: string;
    rows_skipped: number;
    skipped_rows?: SkippedRow[];
  };
}

export interface Subscription {
  description: string;
  amount: number;
  amount_min?: number;
  amount_max?: number;
  frequency: string;
  avg_gap: number;
  occurrences: number;
}

export interface SubscriptionsResponse {
  success: boolean;
  count: number;
  subscriptions: Subscription[];
}

export interface OverspendingMonth {
  month: string;
  spending: number;
  avg_spending: number;
  pct_deviation: number;
  status: string;
  excess: number;
}

export interface OverspendingResponse {
  success: boolean;
  summary: {
    total_analyzed: number;
    overspending_count: number;
    normal_count: number;
  };
  months: OverspendingMonth[];
}

// ----- Cash-Flow Forecast (Task 1) ----------------------------------------- //
export interface ForecastAccuracy {
  mae: number;
  rmse: number;
  mape: number | null;
  holdout_months?: number;
  holdout_days?: number;
  basis: string;
}

export interface MonthlyPoint {
  month: string;
  spend: number;
}

export interface DailyPoint {
  date: string;
  spend: number;
}

export interface ForecastResponse {
  success: boolean;
  method: string;
  history_days: number;
  history_months: number;
  daily: { history: DailyPoint[]; forecast: DailyPoint[] };
  monthly: { history: MonthlyPoint[]; forecast: MonthlyPoint[] };
  next_30_day_total: number;
  next_month_total: number;
  accuracy: ForecastAccuracy | null;
  daily_accuracy: ForecastAccuracy | null;
  message: string;
  error?: string;
}

// ----- ML Categorizer (Task 2) --------------------------------------------- //
export interface CategorizedTxn {
  description: string;
  amount: number;
  category: string;
  confidence: number | null;
  source: 'model' | 'rule_fallback';
}

export interface CategorizeResponse {
  success: boolean;
  model_available: boolean;
  confidence_threshold: number;
  counts: { total: number; model: number; rule_fallback: number };
  breakdown: { category: string; total_spend: number }[];
  transactions: CategorizedTxn[];
  error?: string;
}

export interface ModelCardResponse {
  success: boolean;
  model_available: boolean;
  model: string;
  n_samples: number;
  n_classes: number;
  classes: string[];
  metrics: {
    accuracy: number;
    macro_precision: number;
    macro_recall: number;
    macro_f1: number;
  };
  per_class: Record<string, { precision: number; recall: number; f1: number; support: number }>;
  error?: string;
}

// ----- Anomaly Detection (Task 3) ------------------------------------------ //
export interface Anomaly {
  txn_date: string;
  description: string;
  amount: number;
  spend: number;
  category: string;
  z_score: number;
  category_median: number;
  explanation: string;
}

export interface AnomaliesResponse {
  success: boolean;
  method: string;
  z_threshold: number;
  total_transactions: number;
  anomaly_count: number;
  anomalies: Anomaly[];
  error?: string;
}
