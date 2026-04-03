export type ExecutionBackend = "auto" | "docker" | "local";
export type InputKind = "array" | "numbers" | "string";
export type InputProfile = "random" | "sorted" | "reversed" | "duplicate-heavy" | "nearly-sorted";

export interface ExecutionInstrumentationReport {
  line_counts: Record<string, number>;
  function_call_counts: Record<string, number>;
  loop_iteration_counts: Record<string, number>;
  line_numbers: number[];
  function_names: string[];
  loop_line_numbers: number[];
}

export interface CodeExecutionResult {
  status: "completed" | "failed" | "timeout";
  stdout: string;
  stderr: string;
  exit_code: number | null;
  runtime_ms: number;
  backend: string;
  timed_out: boolean;
  truncated_stdout: boolean;
  truncated_stderr: boolean;
  instrumentation: ExecutionInstrumentationReport | null;
}

export interface PlaygroundRunResponse {
  code: string;
  input: string;
  backend_requested: ExecutionBackend;
  instrumented: boolean;
  execution: CodeExecutionResult;
}

export interface MetricPoint {
  input_size: number;
  value: number;
}

export interface MetricSeries {
  label: string;
  points: MetricPoint[];
}

export interface MetricSummary {
  total_runs: number;
  input_sizes: number[];
  average_runtime_ms: number;
  min_runtime_ms: number;
  max_runtime_ms: number;
  total_runtime_ms: number;
  total_line_executions: number;
  total_function_calls: number;
  dominant_line_number: number | null;
  dominant_function_name: string | null;
  runtime_series: MetricSeries;
  operations_series: MetricSeries;
}

export interface AggregatedLineMetric {
  line_number: number;
  total_execution_count: number;
  total_time_ms: number;
  average_time_ms: number;
  percentage_of_total: number;
  nesting_depth: number;
  loop_iterations: number;
  branch_visits: number;
}

export interface AggregatedFunctionMetric {
  function_name: string;
  qualified_name: string | null;
  total_call_count: number;
  total_time_ms: number;
  average_time_ms: number;
  self_time_ms: number;
  max_depth: number;
  is_recursive: boolean;
}

export interface ExperimentMetricsSnapshot {
  summary: MetricSummary;
  line_metrics: AggregatedLineMetric[];
  function_metrics: AggregatedFunctionMetric[];
}

export interface ComplexityFit {
  label: string;
  big_o: string;
  quality: number;
  rmse: number;
  normalized_rmse: number;
  slope: number;
  intercept: number;
  valid: boolean;
  notes: string;
}

export interface ComplexityEstimate {
  id: string;
  experiment_id: string | null;
  metric_name: string;
  estimated_class: string;
  confidence: number;
  sample_count: number;
  explanation: string;
  alternatives: ComplexityFit[];
  evidence: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface PlaygroundExperimentRun {
  input_size: number;
  repetition_index: number;
  input_kind: InputKind;
  input_profile: InputProfile;
  generated_input: {
    payload: unknown;
    stdin: string;
    metadata: Record<string, unknown>;
  };
  execution: CodeExecutionResult;
}

export interface PlaygroundExperimentResponse {
  code: string;
  backend_requested: ExecutionBackend;
  instrumented: boolean;
  input_kind: InputKind;
  input_profile: InputProfile;
  repetitions: number;
  runs: PlaygroundExperimentRun[];
  metrics_snapshot: ExperimentMetricsSnapshot;
  complexity_estimate: ComplexityEstimate | null;
  operations_complexity_estimate: ComplexityEstimate | null;
  orchestration_runtime_ms: number;
}

export interface ExplanationSection {
  title: string;
  body: string;
  evidence: string[];
  kind: "summary" | "dominance" | "loop" | "complexity" | "caveat";
}

export interface ExplanationResponse {
  headline: string;
  summary: string;
  complexity_class: string | null;
  confidence: number | null;
  dominant_line_number: number | null;
  dominant_function_name: string | null;
  sections: ExplanationSection[];
  caveats: string[];
}

export interface ComparisonComplexityInput {
  estimated_class: string;
  confidence: number;
  sample_count: number;
  explanation: string | null;
  evidence: Record<string, unknown>;
}

export interface ComparisonHotspotComparison {
  kind: "line" | "function";
  left_identifier: string | null;
  right_identifier: string | null;
  left_value: number;
  right_value: number;
  left_share_of_total: number;
  right_share_of_total: number;
  delta: number;
  winner: "left" | "right" | "tie";
  interpretation: string;
}

export interface ComparisonTrendDelta {
  metric_name: string;
  left_start: number;
  left_end: number;
  right_start: number;
  right_end: number;
  left_growth_rate: number;
  right_growth_rate: number;
  delta: number;
  percent_change: number;
  winner: "left" | "right" | "tie";
  interpretation: string;
}

export interface ComparisonComplexityDelta {
  left_class: string | null;
  right_class: string | null;
  left_rank: number | null;
  right_rank: number | null;
  delta: number | null;
  confidence_delta: number | null;
  winner: "left" | "right" | "tie";
  interpretation: string;
}

export interface ComparisonReport {
  runtime: ComparisonTrendDelta;
  operations: ComparisonTrendDelta;
  complexity: ComparisonComplexityDelta;
  hotspots: ComparisonHotspotComparison[];
  summary: {
    overall_winner: "left" | "right" | "tie";
    confidence: number;
    verdict: string;
    tradeoffs: string[];
  };
}

export interface ExecutionBackendStatus {
  execution_backend: string;
  queue_backend: string;
  local_fallback_enabled: boolean;
  docker_cli_available: boolean;
  docker_image_available: boolean;
  dramatiq_available: boolean;
  redis_configured: boolean;
  sandbox_image: string;
  default_timeout_seconds: number;
  max_timeout_seconds: number;
  memory_limit_mb: number;
}

export interface PlaygroundStatusResponse {
  mode: string;
  description: string;
  backend_status: ExecutionBackendStatus;
}

export interface PresetCategory {
  slug: string;
  name: string;
  description: string;
  preset_count: number;
}

export interface PresetRead {
  slug: string;
  name: string;
  category: string;
  summary: string;
  description: string;
  language: string;
  input_kind: InputKind;
  input_profile: InputProfile;
  expected_complexity: string;
  starter_code: string;
  tags: string[];
  default_input_sizes: number[];
  notes: string[];
}

export interface PresetCatalogRead {
  categories: PresetCategory[];
  presets: PresetRead[];
}

export interface SharePayloadRead {
  token: string;
  share_path: string;
  kind: string;
  label: string | null;
  data: Record<string, unknown>;
  created_at: string;
  expires_at: string | null;
  payload_size_bytes: number;
  signature_version: string;
}
