import { mockPlaygroundApi } from "@/lib/mock-playground";

class ApiError extends Error {
  status: number;

  constructor(message: string, status = 400) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export const playgroundApi = {
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

export const backendApi = playgroundApi;
export { ApiError };
