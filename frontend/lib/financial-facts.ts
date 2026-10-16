export type FinancialFactStatus =
  | "all"
  | "pending"
  | "validated"
  | "rejected"
  | "conflict";

export type FinancialFactSource = {
  source_ledger_id: string;
  document_id: string | null;
  chunk_id: string | null;
  source_title: string | null;
  page_number: number | null;
  source_snippet: string | null;
  retrieval_score: number | null;
};

export type FinancialFact = {
  fact_id: string;
  document_id: string;

  company: string | null;

  metric_key: string;
  canonical_metric_key: string | null;
  metric_label: string;

  value_type: string;

  numeric_value: string | null;
  normalized_numeric_value: string | null;

  text_value: string | null;
  raw_value: string | null;

  unit_key: string | null;
  unit_label: string | null;

  currency: string | null;
  scale: string | null;

  period_label: string | null;
  period_start: string | null;
  period_end: string | null;

  category: string | null;
  statement_type: string | null;

  validation_status: string;
  validation_score: number | null;
  validation_reason: string | null;

  validation_details: Record<
    string,
    unknown
  >;

  source: FinancialFactSource | null;
};

export type FinancialFactSummary = {
  total: number;
  pending: number;
  validated: number;
  rejected: number;
  conflict: number;
};

export type DocumentFinancialFactsResponse = {
  ok: boolean;

  document_id: string;

  status_filter: string;

  total: number;
  offset: number;
  limit: number;

  summary: FinancialFactSummary;

  facts: FinancialFact[];
};


export type FinancialFactChartSource = {
  source_ledger_id: string;

  document_id: string | null;
  chunk_id: string | null;

  source_title: string | null;
  page_number: number | null;

  source_snippet: string | null;
  retrieval_score: number | null;
};


export type FinancialFactChartPoint = {
  fact_id: string;

  period_label: string;

  period_start: string | null;
  period_end: string | null;

  value: number;

  numeric_value: string;

  normalized_numeric_value:
    string | null;

  raw_value: string | null;

  validation_score:
    number | null;

  source:
    FinancialFactChartSource
    | null;
};


export type FinancialFactChartResponse = {
  ok: boolean;

  document_id: string;

  metric_key: string;
  metric_label: string;

  value_type: string;

  company: string | null;

  category: string | null;

  statement_type: string | null;

  currency: string | null;

  unit_label: string | null;

  source_scales: string[];

  chart_type:
    | "line"
    | "bar";

  x_axis_label: string;

  y_axis_label: string;

  points:
    FinancialFactChartPoint[];

  warnings: string[];
};