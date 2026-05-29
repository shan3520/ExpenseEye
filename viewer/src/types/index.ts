export interface UploadResponse {
  success: boolean;
  session_id: string;
  message: string;
  transactions_loaded: number;
  mapping_info: {
    date_column: string;
    description_column: string;
    amount_pattern: string;
    rows_skipped: number;
  };
}

export interface Subscription {
  description: string;
  amount: number;
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
