import { mockPlaygroundApi } from "@/lib/mock-playground";
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
import type { ComplexityEstimate, ExecutionBackend, ExperimentMetricsSnapshot, InputKind, InputProfile } from "@/lib/types";

class ApiError extends Error {
  status: number;

  constructor(message: string, status = 400) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const RAW_API_MODE = process.env.NEXT_PUBLIC_PLAYGROUND_API_MODE?.trim().toLowerCase();
const API_MODE = RAW_API_MODE === "backend" ? "backend" : "mock";
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "/api/v1";

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
      // Ignore JSON parse failures for non-JSON errors.
    }
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as T;
}

const backendPlaygroundApi = {
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

const detachedPlaygroundApi = {
  async getStatus() {
    return mockPlaygroundApi.getStatus();
  },

  async listPresets() {
    return mockPlaygroundApi.listPresets();
  },

  async getPreset(slug: string) {
    return mockPlaygroundApi.getPreset(slug);
  },

  async runCode(payload: Parameters<typeof mockPlaygroundApi.runCode>[0]) {
    return mockPlaygroundApi.runCode(payload);
  },

  async runExperiment(payload: Parameters<typeof mockPlaygroundApi.runExperiment>[0]) {
    if (!payload.input_sizes.length) {
      throw new ApiError("Add at least one input size to run a preview experiment.", 422);
    }
    return mockPlaygroundApi.runExperiment(payload);
  },

  async generateExplanation(payload: Parameters<typeof mockPlaygroundApi.generateExplanation>[0]) {
    return mockPlaygroundApi.generateExplanation(payload);
  },

  async compareExperiments(payload: Parameters<typeof mockPlaygroundApi.compareExperiments>[0]) {
    return mockPlaygroundApi.compareExperiments(payload);
  },

  async createShare(payload: Parameters<typeof mockPlaygroundApi.createShare>[0]) {
    return mockPlaygroundApi.createShare(payload);
  },
};

export const playgroundApi = API_MODE === "backend" ? backendPlaygroundApi : detachedPlaygroundApi;
export const backendApi = playgroundApi;
export const playgroundApiMode = API_MODE;
export { ApiError };
