import type {
  ComparisonComplexityInput,
  ComparisonReport,
  ExplanationResponse,
  PlaygroundExperimentResponse,
  PlaygroundRunResponse,
  PlaygroundStatusResponse,
  PresetCatalogRead,
  PresetRead,
  SharePayloadRead,
} from "@/lib/types";
import type { ExecutionBackend, ExperimentMetricsSnapshot, ComplexityEstimate, InputKind, InputProfile } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const errorPayload = (await response.json()) as { detail?: string };
      if (errorPayload.detail) {
        message = errorPayload.detail;
      }
    } catch {
      // Ignore JSON parse errors for non-JSON failures.
    }
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as T;
}

export const backendApi = {
  getStatus: () => apiRequest<PlaygroundStatusResponse>("/playground/status"),
  listPresets: () => apiRequest<PresetCatalogRead>("/presets"),
  getPreset: (slug: string) => apiRequest<PresetRead>(`/presets/${slug}`),
  runCode: (payload: {
    code: string;
    input: string;
    backend: ExecutionBackend;
    instrument: boolean;
    timeout_seconds?: number;
    memory_limit_mb?: number;
  }) =>
    apiRequest<PlaygroundRunResponse>("/playground/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  runExperiment: (payload: {
    code: string;
    input_sizes: number[];
    input_kind: InputKind;
    input_profile: InputProfile;
    repetitions: number;
    backend: ExecutionBackend;
    instrument: boolean;
    timeout_seconds?: number;
    memory_limit_mb?: number;
  }) =>
    apiRequest<PlaygroundExperimentResponse>("/playground/experiment", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  generateExplanation: (payload: {
    metrics_snapshot: ExperimentMetricsSnapshot;
    complexity_estimate: ComplexityEstimate | null;
    max_sections?: number;
  }) =>
    apiRequest<ExplanationResponse>("/explanations/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  compareExperiments: (payload: {
    left: {
      label: string;
      metrics: ExperimentMetricsSnapshot;
      complexity_estimate?: ComparisonComplexityInput;
    };
    right: {
      label: string;
      metrics: ExperimentMetricsSnapshot;
      complexity_estimate?: ComparisonComplexityInput;
    };
  }) =>
    apiRequest<ComparisonReport>("/comparisons/compare", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createShare: (payload: {
    kind: string;
    label: string;
    data: Record<string, unknown>;
    expires_in_seconds: number;
  }) =>
    apiRequest<SharePayloadRead>("/shares", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export { ApiError };
