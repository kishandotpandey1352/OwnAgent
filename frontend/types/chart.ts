export type ChartType =
  | "line"
  | "bar"
  | "scatter"
  | "area"
  | "table";


export type ChartValue =
  | string
  | number
  | boolean
  | null;


export type ChartDataRow =
  Record<string, ChartValue>;


export interface ChartRequest {
  dataset_id: string;

  chart_type: ChartType;

  x?: string | null;

  series?: string[];

  title?: string | null;

  max_rows?: number;
}


export interface ChartSpec {
  ok: boolean;

  dataset_id: string;
  file_name: string;

  chart_type: ChartType;

  title: string;

  x?: string | null;

  series: string[];

  data: ChartDataRow[];

  source_row_count: number;
  chart_row_count: number;

  sampled: boolean;

  explanation: string;

  source_coverage: number;

  warnings: string[];
}


export interface ChartApiResponse
  extends ChartSpec {
  requestId?: string;

  error?: string;
  detail?: string;
}