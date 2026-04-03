"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Activity,
  Binary,
  LoaderCircle,
  Play,
  Share2,
  FlaskConical,
  Code2,
} from "lucide-react";
import { startTransition, useEffect, useMemo, useState } from "react";
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from "react-resizable-panels";

import { playgroundApi, ApiError } from "@/lib/api";
import { MonacoSurface } from "@/components/monaco-surface";
import { usePlaygroundStore } from "@/store/playground-store";
import type { PresetRead } from "@/lib/types";

import { LeftPanel } from "./playground/left-panel";
import { BottomPanel } from "./playground/bottom-panel";
import { buildSampleInput, parseInputSizes, toComparisonComplexity, formatRuntime } from "./playground/shared";

export function PlaygroundShell() {
  const {
    code,
    stdin,
    selectedPresetSlug,
    inputSizesText,
    inputKind,
    inputProfile,
    repetitions,
    backend,
    instrument,
    timeoutSeconds,
    memoryLimitMb,
    runResponse,
    experimentResponse,
    explanation,
    comparison,
    setField,
    applyPreset,
    publishRun,
    publishExperiment,
    publishExplanation,
    publishComparison,
    publishShare,
  } = usePlaygroundStore();

  const [feedback, setFeedback] = useState<string | null>(null);

  const statusQuery = useQuery({ queryKey: ["playground-status"], queryFn: playgroundApi.getStatus, refetchInterval: 20_000 });
  const presetsQuery = useQuery({ queryKey: ["presets"], queryFn: playgroundApi.listPresets });

  const groupedPresets = useMemo(() => {
    const presets = presetsQuery.data?.presets ?? [];
    return presets.reduce<Record<string, PresetRead[]>>((acc, preset) => {
      acc[preset.category] = [...(acc[preset.category] ?? []), preset];
      return acc;
    }, {});
  }, [presetsQuery.data]);

  useEffect(() => {
    if (!selectedPresetSlug && presetsQuery.data?.presets.length) {
      const preset = presetsQuery.data.presets.find((item) => item.slug === "bubble-sort") ?? presetsQuery.data.presets[0];
      startTransition(() => { applyPreset(preset, buildSampleInput(preset)); });
    }
  }, [applyPreset, presetsQuery.data, selectedPresetSlug]);

  const runMutation = useMutation({
    mutationFn: playgroundApi.runCode,
    onSuccess: (payload) => {
      startTransition(() => { publishRun(payload); setField("activeTab", "console"); });
      setFeedback(`Run finished in ${formatRuntime(payload.execution.runtime_ms)}.`);
    },
    onError: (error) => { setFeedback(error instanceof ApiError ? error.message : "Run failed."); },
  });

  const explanationMutation = useMutation({
    mutationFn: playgroundApi.generateExplanation,
    onSuccess: (payload) => { startTransition(() => { publishExplanation(payload); }); },
    onError: () => { startTransition(() => { publishExplanation(null); }); },
  });

  const comparisonMutation = useMutation({
    mutationFn: playgroundApi.compareExperiments,
    onSuccess: (payload) => { startTransition(() => { publishComparison(payload); }); },
    onError: () => { startTransition(() => { publishComparison(null); }); },
  });

  const experimentMutation = useMutation({
    mutationFn: playgroundApi.runExperiment,
    onSuccess: async (payload) => {
      const previousExperiment = usePlaygroundStore.getState().experimentResponse;
      startTransition(() => { publishExperiment(payload); setField("activeTab", "runtime"); });

      const requests: Promise<unknown>[] = [];
      const bestComplexityEstimate = (() => {
        const rt = payload.complexity_estimate;
        const ops = payload.operations_complexity_estimate;
        if (ops && rt && ops.confidence > rt.confidence) return ops;
        return ops ?? rt ?? null;
      })();
      if (bestComplexityEstimate) {
        requests.push(
          explanationMutation.mutateAsync({
            metrics_snapshot: payload.metrics_snapshot,
            complexity_estimate: bestComplexityEstimate,
            max_sections: 5,
          })
        );
      } else {
        startTransition(() => { publishExplanation(null); });
      }

      if (previousExperiment) {
        const prevBestEstimate = (() => {
          const rt = previousExperiment.complexity_estimate;
          const ops = previousExperiment.operations_complexity_estimate;
          if (ops && rt && ops.confidence > rt.confidence) return ops;
          return ops ?? rt ?? null;
        })();
        requests.push(
          comparisonMutation.mutateAsync({
            left: {
              label: previousExperiment.code.slice(0, 18) || "previous",
              metrics: previousExperiment.metrics_snapshot,
              complexity_estimate: toComparisonComplexity(prevBestEstimate),
            },
            right: {
              label: payload.code.slice(0, 18) || "current",
              metrics: payload.metrics_snapshot,
              complexity_estimate: toComparisonComplexity(bestComplexityEstimate),
            },
          })
        );
      }

      await Promise.all(requests);
      setFeedback(`Experiment completed across ${payload.runs.length} runs.`);
    },
    onError: (error) => { setFeedback(error instanceof ApiError ? error.message : "Experiment failed."); },
  });

  const shareMutation = useMutation({
    mutationFn: playgroundApi.createShare,
    onSuccess: (payload) => {
      startTransition(() => { publishShare(payload); setField("activeTab", "share"); });
      setFeedback("Share token generated.");
    },
    onError: (error) => { setFeedback(error instanceof ApiError ? error.message : "Share generation failed."); },
  });

  const runExperiment = () => {
    experimentMutation.mutate({
      code,
      input_sizes: parseInputSizes(inputSizesText),
      input_kind: inputKind,
      input_profile: inputProfile,
      repetitions,
      backend,
      instrument,
      timeout_seconds: timeoutSeconds,
      memory_limit_mb: memoryLimitMb,
    });
  };

  const selectedPreset = presetsQuery.data?.presets.find((preset) => preset.slug === selectedPresetSlug) ?? null;
  const lineMetrics = experimentResponse?.metrics_snapshot.line_metrics ?? [];
  const latestExecution = runResponse?.execution ?? experimentResponse?.runs.at(-1)?.execution ?? null;

  return (
    <div className="flex h-screen w-full flex-col bg-[#0f0f0f] text-gray-300 font-sans selection:bg-green-500/30">
      <header className="flex h-[50px] shrink-0 items-center justify-between border-b border-white/10 bg-[#1a1a1a] px-4">
        <button 
          onClick={() => window.location.reload()} 
          className="flex text-left items-center gap-3 group hover:opacity-90 transition-opacity cursor-pointer focus:outline-none"
          title="Refresh Sandbox Environment"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-green-400 to-emerald-600 shadow-md shadow-green-500/20 group-hover:shadow-green-500/40 transition-shadow">
            <Binary size={16} className="text-black" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-wide text-white group-hover:text-green-400 transition-colors">Big O Playground</h1>
            <div className="flex items-center gap-2">
              <p className="text-[10px] uppercase tracking-wider text-gray-400">Interactive Runtime Lab</p>
            </div>
          </div>
        </button>

        <div className="flex items-center gap-2">
          <button
            type="button"
            className="flex items-center gap-2 rounded-md bg-[#262626] hover:bg-[#333333] px-4 py-1.5 text-xs font-medium text-gray-300 transition-colors"
            onClick={() =>
              runMutation.mutate({
                code,
                input: stdin,
                backend,
                instrument,
                timeout_seconds: timeoutSeconds,
                memory_limit_mb: memoryLimitMb,
              })
            }
            disabled={runMutation.isPending}
          >
            {runMutation.isPending ? <LoaderCircle className="animate-spin" size={14} /> : <Play size={14} className="text-gray-400 group-hover:text-white" />}
            Run
          </button>
          <button
            type="button"
            className="flex items-center gap-2 rounded-md bg-green-500 hover:bg-green-400 px-4 py-1.5 text-xs font-medium text-black transition-all"
            onClick={runExperiment}
            disabled={experimentMutation.isPending}
          >
            {experimentMutation.isPending ? <LoaderCircle className="animate-spin" size={14} /> : <FlaskConical size={14} className="text-black/80" />}
            Submit
          </button>
        </div>

        <div className="flex items-center gap-3 text-xs text-gray-400">
          <div className="hidden sm:flex items-center gap-1.5 rounded-full bg-white/5 px-2.5 py-1 text-xs border border-white/10">
            <Activity size={12} className={statusQuery.data?.mode === "maintenance" ? "text-yellow-500" : "text-green-500"} />
            <span className="capitalize">{statusQuery.data?.mode ?? "Connecting..."}</span>
          </div>
          <button
            onClick={() =>
              shareMutation.mutate({
                kind: "playground-session",
                label: selectedPreset?.name ?? "Custom session",
                expires_in_seconds: 60 * 60 * 24,
                data: {
                  workspace: { code, stdin, inputSizesText, inputKind, inputProfile, repetitions, backend, instrument, timeoutSeconds, memoryLimitMb },
                  latestRun: runResponse,
                  latestExperiment: experimentResponse,
                  explanation,
                  comparison,
                },
              })
            }
            disabled={shareMutation.isPending}
            className="flex items-center gap-1.5 rounded-md bg-[#262626] hover:bg-[#333333] px-3 py-1.5 text-xs font-medium text-gray-300 transition-colors"
          >
            {shareMutation.isPending ? <LoaderCircle className="animate-spin" size={14} /> : <Share2 size={14} className="text-gray-400" />}
            Share
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-hidden p-3 bg-[#0a0a0a]">
        <PanelGroup id="root" orientation="horizontal">
          <LeftPanel presetsQuery={presetsQuery} groupedPresets={groupedPresets} />

          <PanelResizeHandle className="w-1.5 flex items-center justify-center cursor-col-resize group z-10 transition-colors hover:bg-white/10">
            <div className="w-[2px] h-8 rounded-full bg-white/20 transition-colors" />
          </PanelResizeHandle>

          <Panel defaultSize={75} minSize={30}>
            <PanelGroup id="editor-console" orientation="vertical">
              <Panel defaultSize={65} minSize={20} className="rounded-xl border border-white/10 bg-[#1e1e1e] flex flex-col overflow-hidden shadow-2xl relative">
                <div className="flex h-11 shrink-0 items-center justify-between border-b border-white/10 bg-[#1e1e1e] px-4 text-xs">
                  <div className="flex items-center gap-2 text-gray-300 font-medium">
                    <Code2 size={16} className="text-green-500" />
                    <span>Code</span>
                  </div>
                  
                  <div className="flex items-center">
                    <div className="relative group">
                      <select
                        className="appearance-none bg-[#262626] border border-white/10 text-gray-300 rounded-md pl-4 pr-8 py-1.5 text-[11px] font-medium tracking-wider outline-none hover:bg-[#333333] hover:text-white transition-all cursor-pointer shadow-sm text-center min-w-[120px]"
                        defaultValue="python"
                      >
                        <option value="python">Python 3.11</option>
                      </select>
                      <svg className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 group-hover:text-white transition-colors pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </div>
                </div>
                <div className="flex-1 overflow-hidden bg-[#1e1e1e]">
                  <MonacoSurface code={code} onChange={(next) => setField("code", next)} lineMetrics={lineMetrics} complexityEstimate={
                  // Prefer operations estimate (immune to timer noise) if it exists and has higher confidence
                  (() => {
                    const rt = experimentResponse?.complexity_estimate ?? null;
                    const ops = experimentResponse?.operations_complexity_estimate ?? null;
                    if (ops && rt && ops.confidence > rt.confidence) return ops;
                    return ops ?? rt;
                  })()
                } />
                </div>
              </Panel>

              <PanelResizeHandle className="h-1.5 flex items-center justify-center cursor-row-resize group z-10 hover:bg-white/10 transition-colors">
                <div className="h-[2px] w-8 rounded-full bg-white/20 transition-colors" />
              </PanelResizeHandle>

              <BottomPanel
                feedback={feedback}
                latestExecution={latestExecution}
                selectedPreset={selectedPreset}
                isPending={runMutation.isPending}
                onRun={(stdinValue) =>
                  runMutation.mutate({
                    code,
                    input: stdinValue,
                    backend,
                    instrument,
                    timeout_seconds: timeoutSeconds,
                    memory_limit_mb: memoryLimitMb,
                  })
                }
              />
            </PanelGroup>
          </Panel>
        </PanelGroup>
      </main>
    </div>
  );
}
