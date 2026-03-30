"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type {
  ComparisonReport,
  ExplanationResponse,
  PlaygroundExperimentResponse,
  PlaygroundRunResponse,
  PresetRead,
  SharePayloadRead,
} from "@/lib/types";
import type { ExecutionBackend, InputKind, InputProfile } from "@/lib/types";

interface PlaygroundState {
  code: string;
  stdin: string;
  selectedPresetSlug: string | null;
  inputSizesText: string;
  inputKind: InputKind;
  inputProfile: InputProfile;
  repetitions: number;
  backend: ExecutionBackend;
  instrument: boolean;
  timeoutSeconds: number;
  memoryLimitMb: number;
  activeTab: "console" | "runtime" | "operations" | "explanation" | "comparison" | "share";
  runResponse: PlaygroundRunResponse | null;
  experimentResponse: PlaygroundExperimentResponse | null;
  previousExperimentResponse: PlaygroundExperimentResponse | null;
  explanation: ExplanationResponse | null;
  comparison: ComparisonReport | null;
  sharePayload: SharePayloadRead | null;
  setField: <K extends keyof PlaygroundState>(key: K, value: PlaygroundState[K]) => void;
  applyPreset: (preset: PresetRead, sampleInput: string) => void;
  publishRun: (payload: PlaygroundRunResponse) => void;
  publishExperiment: (payload: PlaygroundExperimentResponse) => void;
  publishExplanation: (payload: ExplanationResponse | null) => void;
  publishComparison: (payload: ComparisonReport | null) => void;
  publishShare: (payload: SharePayloadRead | null) => void;
}

export const usePlaygroundStore = create<PlaygroundState>()(
  persist(
    (set) => ({
      code: "print('Big O Playground ready')\n",
      stdin: "",
      selectedPresetSlug: null,
      inputSizesText: "10, 50, 100, 250",
      inputKind: "array",
      inputProfile: "random",
      repetitions: 1,
      backend: "auto",
      instrument: true,
      timeoutSeconds: 3,
      memoryLimitMb: 128,
      activeTab: "console",
      runResponse: null,
      experimentResponse: null,
      previousExperimentResponse: null,
      explanation: null,
      comparison: null,
      sharePayload: null,
      setField: (key, value) => set(() => ({ [key]: value })),
      applyPreset: (preset, sampleInput) =>
        set(() => ({
          selectedPresetSlug: preset.slug,
          code: preset.starter_code,
          stdin: sampleInput,
          inputSizesText: preset.default_input_sizes.join(", "),
          inputKind: preset.input_kind,
          inputProfile: preset.input_profile,
          sharePayload: null,
        })),
      publishRun: (payload) =>
        set(() => ({
          runResponse: payload,
          activeTab: "console",
          sharePayload: null,
        })),
      publishExperiment: (payload) =>
        set((state) => ({
          previousExperimentResponse: state.experimentResponse,
          experimentResponse: payload,
          activeTab: "runtime",
          sharePayload: null,
        })),
      publishExplanation: (payload) =>
        set(() => ({
          explanation: payload,
          activeTab: payload ? "explanation" : "runtime",
        })),
      publishComparison: (payload) =>
        set(() => ({
          comparison: payload,
        })),
      publishShare: (payload) =>
        set(() => ({
          sharePayload: payload,
          activeTab: payload ? "share" : "console",
        })),
    }),
    {
      name: "big-o-playground-workspace",
      partialize: (state) => ({
        code: state.code,
        stdin: state.stdin,
        selectedPresetSlug: state.selectedPresetSlug,
        inputSizesText: state.inputSizesText,
        inputKind: state.inputKind,
        inputProfile: state.inputProfile,
        repetitions: state.repetitions,
        backend: state.backend,
        instrument: state.instrument,
        timeoutSeconds: state.timeoutSeconds,
        memoryLimitMb: state.memoryLimitMb,
      }),
    },
  ),
);
