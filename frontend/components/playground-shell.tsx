"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  Binary,
  BrainCircuit,
  Copy,
  Database,
  FlaskConical,
  Gauge,
  LoaderCircle,
  Play,
  Share2,
  Sparkles,
  Code2,
  Terminal,
  Settings,
  FileText,
  LayoutTemplate,
  Info
} from "lucide-react";
import { startTransition, useEffect, useMemo, useState } from "react";
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from "react-resizable-panels";

import { playgroundApi, ApiError } from "@/lib/api";
import type {
  ComparisonComplexityInput,
  PlaygroundExperimentResponse,
  PlaygroundRunResponse,
  PresetRead,
} from "@/lib/types";
import { MetricChart } from "@/components/metric-chart";
import { MonacoSurface } from "@/components/monaco-surface";
import { usePlaygroundStore } from "@/store/playground-store";

function buildSampleInput(preset: PresetRead) {
  if (preset.input_kind === "numbers") return "12";
  if (preset.input_kind === "string") return "abracadabra";
  return "[5, 3, 8, 1, 2]";
}

function parseInputSizes(inputSizesText: string) {
  return inputSizesText
    .split(",")
    .map((value) => Number.parseInt(value.trim(), 10))
    .filter((value) => Number.isFinite(value) && value > 0);
}

function toComparisonComplexity(input: PlaygroundExperimentResponse["complexity_estimate"]): ComparisonComplexityInput | undefined {
  if (!input) return undefined;
  return {
    estimated_class: input.estimated_class,
    confidence: input.confidence,
    sample_count: input.sample_count,
    explanation: input.explanation,
    evidence: input.evidence,
  };
}

function formatRuntime(runtimeMs: number) {
  return runtimeMs >= 1000 ? `${(runtimeMs / 1000).toFixed(2)} s` : `${runtimeMs.toFixed(0)} ms`;
}

function TabButton({ active, onClick, icon: Icon, label }: { active: boolean; onClick: () => void; icon: any; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        "flex min-w-fit items-center gap-2 rounded-md px-3 py-1.5 transition-colors text-xs hover:bg-white/5",
        active ? "bg-white/10 text-white font-medium" : "text-gray-400 hover:text-gray-200"
      )}
    >
      <Icon size={14} className={active ? "text-green-500" : ""} />
      {label}
    </button>
  );
}

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
    activeTab,
    runResponse,
    experimentResponse,
    explanation,
    comparison,
    sharePayload,
    setField,
    applyPreset,
    publishRun,
    publishExperiment,
    publishExplanation,
    publishComparison,
    publishShare,
  } = usePlaygroundStore();

  const [feedback, setFeedback] = useState<string | null>(null);
  const [leftTab, setLeftTab] = useState<"library" | "settings" | "insights">("library");

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
      startTransition(() => { publishExperiment(payload); setField("activeTab", "console"); });

      const requests: Promise<unknown>[] = [];
      if (payload.complexity_estimate) {
        requests.push(
          explanationMutation.mutateAsync({
            metrics_snapshot: payload.metrics_snapshot,
            complexity_estimate: payload.complexity_estimate,
            max_sections: 5,
          })
        );
      } else {
        startTransition(() => { publishExplanation(null); });
      }

      if (previousExperiment) {
        requests.push(
          comparisonMutation.mutateAsync({
            left: {
              label: previousExperiment.code.slice(0, 18) || "previous",
              metrics: previousExperiment.metrics_snapshot,
              complexity_estimate: toComparisonComplexity(previousExperiment.complexity_estimate),
            },
            right: {
              label: payload.code.slice(0, 18) || "current",
              metrics: payload.metrics_snapshot,
              complexity_estimate: toComparisonComplexity(payload.complexity_estimate),
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
  const topFunctions = experimentResponse?.metrics_snapshot.function_metrics.slice(0, 4) ?? [];
  const latestExecution = runResponse?.execution ?? experimentResponse?.runs.at(-1)?.execution ?? null;

  return (
    <div className="flex h-screen w-full flex-col bg-[#0f0f0f] text-gray-300 font-sans selection:bg-green-500/30">
      <header className="flex h-[50px] shrink-0 items-center justify-between border-b border-white/10 bg-[#1a1a1a] px-4">
        <div className="flex items-center gap-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-green-400 to-emerald-600 shadow-md shadow-green-500/20">
            <Binary size={16} className="text-black" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-wide text-white">Big O Playground</h1>
            <div className="flex items-center gap-2">
              <p className="text-[10px] uppercase tracking-wider text-gray-400">Interactive Runtime Lab</p>
            </div>
          </div>
        </div>

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
          <Panel defaultSize={35} minSize={20} className="rounded-xl border border-white/10 bg-[#1e1e1e] flex flex-col overflow-hidden shadow-2xl">
            <div className="flex h-11 shrink-0 items-center gap-1 border-b border-white/10 bg-[#1e1e1e] px-2">
              <TabButton active={leftTab === "library"} onClick={() => setLeftTab("library")} icon={FileText} label="DSA" />
              <TabButton active={leftTab === "settings"} onClick={() => setLeftTab("settings")} icon={Settings} label="Settings" />
              <TabButton active={leftTab === "insights"} onClick={() => setLeftTab("insights")} icon={BrainCircuit} label="Insights" />
            </div>
            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
              {leftTab === "library" && (
                <div className="space-y-6 animate-in fade-in duration-300">
                  {presetsQuery.isLoading && (
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <LoaderCircle className="animate-spin" size={16} /> Loading presets...
                    </div>
                  )}
                  {Object.entries(groupedPresets).map(([category, presets]) => (
                    <div key={category} className="space-y-3">
                      <h3 className="text-[11px] font-semibold uppercase tracking-widest text-gray-500">
                        {category.replaceAll("-", " ")}
                      </h3>
                      <div className="space-y-1">
                        {presets.map((preset) => (
                          <button
                            key={preset.slug}
                            type="button"
                            className={clsx(
                              "w-full rounded-lg px-3 py-2.5 text-left transition-all",
                              selectedPresetSlug === preset.slug
                                ? "bg-white/10 border border-white/10"
                                : "hover:bg-white/5 border border-transparent"
                            )}
                            onClick={() => startTransition(() => applyPreset(preset, buildSampleInput(preset)))}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <LayoutTemplate size={14} className={selectedPresetSlug === preset.slug ? "text-green-500" : "text-gray-500"} />
                                <span className={clsx("text-sm font-medium", selectedPresetSlug === preset.slug ? "text-white" : "text-gray-300")}>
                                  {preset.name}
                                </span>
                              </div>
                            </div>
                            <p className="mt-1.5 text-xs text-gray-400 leading-relaxed ml-6 line-clamp-3">
                              {preset.summary}
                            </p>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {leftTab === "settings" && (
                <div className="space-y-5 animate-in fade-in duration-300">
                  <div className="rounded-lg border border-white/10 bg-[#262626] p-4 space-y-4">
                    <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-400 flex items-center gap-2">
                      <FlaskConical size={14} className="text-gray-400"/> Test Environment
                    </h3>
                    <div className="space-y-1">
                      <label className="text-xs text-gray-400">Input Sizes (comma separated)</label>
                      <input
                        value={inputSizesText}
                        onChange={(event) => setField("inputSizesText", event.target.value)}
                        className="w-full rounded-md border border-white/10 bg-[#121212] px-3 py-2 text-sm text-gray-200 outline-none focus:border-white/30 transition-all"
                      />
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <label className="text-xs text-gray-400">Input Kind</label>
                        <select
                          value={inputKind}
                          onChange={(event) => setField("inputKind", event.target.value as typeof inputKind)}
                          className="w-full rounded-md border border-white/10 bg-[#121212] px-3 py-2 text-sm text-gray-200 outline-none focus:border-white/30 transition-all"
                        >
                          <option value="array">Array</option>
                          <option value="numbers">Numbers</option>
                          <option value="string">String</option>
                        </select>
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs text-gray-400">Profile</label>
                        <select
                          value={inputProfile}
                          onChange={(event) => setField("inputProfile", event.target.value as typeof inputProfile)}
                          className="w-full rounded-md border border-white/10 bg-[#121212] px-3 py-2 text-sm text-gray-200 outline-none focus:border-white/30 transition-all"
                        >
                          <option value="random">Random</option>
                          <option value="sorted">Sorted</option>
                          <option value="reversed">Reversed</option>
                          <option value="duplicate-heavy">Duplicate-heavy</option>
                          <option value="nearly-sorted">Nearly-sorted</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-lg border border-white/10 bg-[#262626] p-4 space-y-4">
                    <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-400 flex items-center gap-2">
                       <Settings size={14} className="text-gray-400"/> Execution Limits
                    </h3>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <label className="text-xs text-gray-400">Repetitions</label>
                        <input
                          type="number" min={1} max={10}
                          value={repetitions}
                          onChange={(event) => setField("repetitions", Number(event.target.value))}
                          className="w-full rounded-md border border-white/10 bg-[#121212] px-3 py-2 text-sm text-gray-200 outline-none focus:border-white/30 transition-all"
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs text-gray-400">Backend</label>
                        <select
                          value={backend}
                          onChange={(event) => setField("backend", event.target.value as typeof backend)}
                          className="w-full rounded-md border border-white/10 bg-[#121212] px-3 py-2 text-sm text-gray-200 outline-none focus:border-white/30 transition-all"
                        >
                          <option value="auto">Auto</option>
                          <option value="local">Local</option>
                          <option value="docker">Docker</option>
                        </select>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <label className="text-xs text-gray-400">Timeout (s)</label>
                        <input
                          type="number" min={1} max={30}
                          value={timeoutSeconds}
                          onChange={(event) => setField("timeoutSeconds", Number(event.target.value))}
                          className="w-full rounded-md border border-white/10 bg-[#121212] px-3 py-2 text-sm text-gray-200 outline-none focus:border-white/30 transition-all"
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs text-gray-400">Memory (MB)</label>
                        <input
                          type="number" min={64} max={1024} step={32}
                          value={memoryLimitMb}
                          onChange={(event) => setField("memoryLimitMb", Number(event.target.value))}
                          className="w-full rounded-md border border-white/10 bg-[#121212] px-3 py-2 text-sm text-gray-200 outline-none focus:border-white/30 transition-all"
                        />
                      </div>
                    </div>
                  </div>

                  <label className="flex items-center gap-3 rounded-lg border border-white/10 bg-[#262626] px-4 py-3 text-sm text-gray-300 cursor-pointer hover:bg-white/10 transition-colors">
                    <input
                      type="checkbox"
                      checked={instrument}
                      onChange={(event) => setField("instrument", event.target.checked)}
                      className="h-4 w-4 rounded border-gray-600 bg-[#121212] text-green-500 focus:ring-green-500/50"
                    />
                    Enable instrumentation (heatmaps & insights)
                  </label>
                </div>
              )}

              {leftTab === "insights" && (
                <div className="space-y-5 animate-in fade-in duration-300">
                  <div className="rounded-lg border border-white/10 bg-[#262626] p-5">
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-[#00b8a3] mb-4">
                      <Gauge size={16} /> Complexity Estimate
                    </div>
                    {experimentResponse?.complexity_estimate ? (
                      <div>
                        <p className="text-3xl font-bold tracking-tight text-white font-mono">
                          {experimentResponse.complexity_estimate.estimated_class}
                        </p>
                        <p className="mt-3 text-sm leading-relaxed text-gray-400">
                          {experimentResponse.complexity_estimate.explanation}
                        </p>
                        <div className="mt-4 inline-flex items-center rounded-full bg-white/5 px-2.5 py-1 text-xs font-medium text-gray-300 border border-white/10">
                          Confidence: {Math.round(experimentResponse.complexity_estimate.confidence * 100)}%
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center py-6 text-center text-gray-500">
                        <Info size={24} className="mb-2 opacity-50" />
                        <p className="text-sm">Submit an experiment to estimate scaling class.</p>
                      </div>
                    )}
                  </div>

                  <div className="rounded-lg border border-white/10 bg-[#262626] p-5">
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-[#ffc01e] mb-4">
                      <BrainCircuit size={16} /> Code Hotspots
                    </div>
                    <div className="space-y-3">
                      {lineMetrics.slice(0, 4).map((metric) => (
                        <div key={metric.line_number} className="rounded-lg border border-white/5 bg-[#121212] p-3">
                          <div className="flex items-center justify-between gap-3 text-sm mb-2">
                            <span className="text-gray-300">Line {metric.line_number}</span>
                            <span className="text-[#ffc01e] font-mono text-xs">{metric.total_execution_count.toLocaleString()} hits</span>
                          </div>
                          <div className="h-1.5 w-full rounded-full bg-black/50 overflow-hidden">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-[#ffc01e] to-[#ff2d55]"
                              style={{ width: `${Math.max(metric.percentage_of_total * 100, 6)}%` }}
                            />
                          </div>
                        </div>
                      ))}
                      {!lineMetrics.length && (
                        <div className="py-4 text-center text-sm text-gray-500">
                          Enable instrumentation and run to see hotspots.
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="rounded-lg border border-white/10 bg-[#262626] p-5">
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-[#007aff] mb-4">
                      <Database size={16} /> Function Focus
                    </div>
                    <div className="space-y-3">
                      {topFunctions.map((metric) => (
                        <div key={metric.function_name} className="rounded-lg border border-white/5 bg-[#121212] p-3">
                          <div className="flex items-center justify-between text-sm mb-1">
                            <span className="text-gray-200 font-medium font-mono text-xs">{metric.function_name}</span>
                            <span className="text-[#007aff] font-mono text-xs">{metric.total_call_count} calls</span>
                          </div>
                          <p className="text-xs text-gray-500">
                            Max depth {metric.max_depth} <span className="mx-1">•</span> Self time {metric.self_time_ms.toFixed(2)}ms
                          </p>
                        </div>
                      ))}
                      {!topFunctions.length && (
                        <div className="py-4 text-center text-sm text-gray-500">
                          No function metrics available yet.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </Panel>

          <PanelResizeHandle className="w-1.5 flex items-center justify-center cursor-col-resize group z-10 transition-colors hover:bg-white/10">
            <div className="w-[2px] h-8 rounded-full bg-white/20 transition-colors" />
          </PanelResizeHandle>

          <Panel defaultSize={65} minSize={30}>
            <PanelGroup id="editor-console" orientation="vertical">
              <Panel defaultSize={60} minSize={20} className="rounded-xl border border-white/10 bg-[#1e1e1e] flex flex-col overflow-hidden shadow-2xl relative">
                <div className="flex h-11 shrink-0 items-center justify-between border-b border-white/10 bg-[#1e1e1e] px-4 text-xs">
                  <div className="flex items-center gap-2 text-gray-300 font-medium">
                    <Code2 size={16} className="text-green-500" />
                    <span>Code</span>
                  </div>
                  <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5 text-gray-400 bg-white/5 px-2 py-0.5 rounded cursor-default border border-white/5 hover:bg-white/10 transition-colors">
                    Python 3.11
                  </div>
                  </div>
                </div>
                <div className="flex-1 overflow-hidden bg-[#1e1e1e]">
                  <MonacoSurface code={code} onChange={(next) => setField("code", next)} lineMetrics={lineMetrics} />
                </div>
              </Panel>

              <PanelResizeHandle className="h-1.5 flex items-center justify-center cursor-row-resize group z-10 hover:bg-white/10 transition-colors">
                <div className="h-[2px] w-8 rounded-full bg-white/20 transition-colors" />
              </PanelResizeHandle>

              <Panel defaultSize={40} minSize={20} className="rounded-xl border border-white/10 bg-[#1e1e1e] flex flex-col overflow-hidden shadow-2xl">
                <div className="flex h-11 shrink-0 items-center gap-1 overflow-x-auto border-b border-white/10 bg-[#1e1e1e] px-2 hide-scrollbar text-xs">
                  <TabButton active={activeTab === "console"} onClick={() => setField("activeTab", "console")} icon={Terminal} label="Testcase" />
                  <TabButton active={activeTab === "runtime"} onClick={() => setField("activeTab", "runtime")} icon={Activity} label="Runtime" />
                  <TabButton active={activeTab === "operations"} onClick={() => setField("activeTab", "operations")} icon={Gauge} label="Operations" />
                  <TabButton active={activeTab === "explanation"} onClick={() => setField("activeTab", "explanation")} icon={Sparkles} label="Explanation" />
                  <TabButton active={activeTab === "comparison"} onClick={() => setField("activeTab", "comparison")} icon={BarChart3} label="Compare" />
                  <TabButton active={activeTab === "share"} onClick={() => setField("activeTab", "share")} icon={Share2} label="Share" />
                </div>
                <div className="flex-1 overflow-y-auto p-4 custom-scrollbar bg-[#1e1e1e]">
                  {feedback && activeTab !== "console" && activeTab !== "share" && (
                    <div className="mb-4 rounded-md bg-white/5 px-3 py-2 text-xs text-gray-400 border border-white/10">
                      <span className="text-green-400 mr-2">➜</span> {feedback}
                    </div>
                  )}

                  {activeTab === "console" && (
                    <div className="flex flex-col h-full gap-4 lg:flex-row">
                      <div className="flex-1 flex flex-col space-y-3 min-w-[50%]">
                        <div className="flex items-center gap-3">
                          <label className="text-xs font-semibold text-gray-300">Input</label>
                          <button
                            type="button"
                            className="bg-white/5 hover:bg-white/10 border border-white/10 px-2 py-0.5 rounded text-[11px] text-gray-400 transition-colors"
                            onClick={() => { if (selectedPreset) setField("stdin", buildSampleInput(selectedPreset)); }}
                          >
                            Sample
                          </button>
                        </div>
                        <textarea
                          value={stdin}
                          onChange={(event) => setField("stdin", event.target.value)}
                          className="flex-1 min-h-[120px] w-full resize-none rounded-lg border border-white/10 bg-[#121212] px-4 py-3 text-sm text-gray-300 outline-none focus:border-white/20 transition-colors font-mono"
                          spellCheck={false}
                          placeholder="Standard input..."
                        />
                      </div>
                      <div className="flex-1 flex flex-col space-y-3 min-w-[50%]">
                        <div className="flex items-center justify-between">
                          <label className="text-xs font-semibold text-gray-300">Output</label>
                          {latestExecution && (
                            <span className={clsx("text-xs px-2 py-0.5 rounded bg-white/5 font-medium border border-white/10", latestExecution.status === "completed" ? "text-green-500" : "text-red-500")}>
                              {latestExecution.status === "completed" ? "Accepted" : "Runtime Error"}
                            </span>
                          )}
                        </div>
                        <div className="flex-1 min-h-[120px] rounded-lg border border-white/10 bg-[#121212] p-4 overflow-y-auto w-full">
                          {latestExecution ? (
                            <div className="space-y-4">
                              <div>
                                <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">{latestExecution.stdout || <span className="opacity-50">No stdout</span>}</pre>
                              </div>
                              {latestExecution.stderr && (
                                <div>
                                  <div className="rounded bg-red-500/10 px-3 py-2 text-sm text-red-500 font-mono whitespace-pre-wrap">
                                    {latestExecution.stderr}
                                  </div>
                                </div>
                              )}
                              <div className="pt-3 border-t border-white/10 flex gap-4 text-xs text-gray-500">
                                <div className="flex items-center gap-1.5"><Activity size={12}/> {formatRuntime(latestExecution.runtime_ms)}</div>
                                <div className="flex items-center gap-1.5"><Database size={12}/> {latestExecution.backend}</div>
                              </div>
                            </div>
                          ) : (
                            <div className="flex h-full items-center justify-center text-sm text-gray-500 italic px-4 text-center">
                              Run the code or submit an experiment to see the output.
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {activeTab === "runtime" && experimentResponse && (
                    <div className="h-full w-full max-h-[400px]">
                      <MetricChart
                        title="Runtime Curve"
                        subtitle="Measured wall-clock runtime across input sizes (lower is better)."
                        data={experimentResponse.metrics_snapshot.summary.runtime_series.points}
                        color="#00b8a3"
                      />
                    </div>
                  )}

                  {activeTab === "operations" && experimentResponse && (
                    <div className="h-full w-full max-h-[400px]">
                      <MetricChart
                        title="Operations Curve"
                        subtitle="Aggregated line execution counts as a proxy for algorithm steps."
                        data={experimentResponse.metrics_snapshot.summary.operations_series.points}
                        color="#007aff"
                      />
                    </div>
                  )}

                  {activeTab === "explanation" && (
                    <div className="max-w-4xl animate-in fade-in">
                      {explanation ? (
                        <div className="space-y-6">
                          <div className="rounded-xl border border-white/10 bg-[#262626] p-6">
                            <h3 className="text-xl font-bold tracking-tight text-white mb-2">{explanation.headline}</h3>
                            <p className="text-gray-400 leading-relaxed text-sm">{explanation.summary}</p>
                          </div>
                          <div className="grid gap-4 md:grid-cols-2">
                            {explanation.sections.map((section) => (
                              <div key={`${section.kind}-${section.title}`} className="rounded-xl border border-white/10 bg-[#262626] p-5">
                                <p className="text-[10px] font-semibold uppercase tracking-widest text-green-500 mb-2">{section.kind}</p>
                                <h4 className="text-base font-medium text-white mb-2">{section.title}</h4>
                                <p className="text-sm leading-relaxed text-gray-400 mb-4">{section.body}</p>
                                {section.evidence.length > 0 && (
                                  <ul className="space-y-1.5 text-xs text-gray-500 bg-[#121212] p-3 rounded-lg border border-white/5">
                                    {section.evidence.map((item) => (
                                      <li key={item} className="flex gap-2"><span className="text-green-500">•</span> <span>{item}</span></li>
                                    ))}
                                  </ul>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div className="flex flex-col items-center justify-center p-12 text-center text-gray-500">
                          <Sparkles size={32} className="mb-4 text-gray-600" />
                          <h3 className="text-lg font-medium text-gray-300 mb-2">No Explanation Generated</h3>
                          <p className="max-w-md text-sm">Run an experiment to let AI generate narrative insights for your algorithm.</p>
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === "comparison" && (
                    <div className="max-w-4xl animate-in fade-in">
                      {comparison ? (
                        <div className="grid gap-4 md:grid-cols-2">
                          <div className="rounded-xl border border-white/10 bg-[#262626] p-6">
                            <p className="text-[10px] font-semibold uppercase tracking-widest text-blue-400 mb-2">Verdict</p>
                            <h3 className="text-xl font-bold text-white mb-2">{comparison.summary.verdict}</h3>
                            <p className="text-sm text-gray-400 mb-4 bg-[#121212] p-2 rounded-lg border border-white/5 inline-flex items-center gap-2">
                              Winner: <span className="text-blue-400 font-medium">{comparison.summary.overall_winner}</span> |
                              Conf: <span>{Math.round(comparison.summary.confidence * 100)}%</span>
                            </p>
                            {comparison.summary.tradeoffs.length > 0 && (
                              <div className="space-y-2">
                                <p className="text-xs text-gray-500">Tradeoffs:</p>
                                <ul className="space-y-1 text-sm text-gray-400 list-inside list-disc pl-1">
                                  {comparison.summary.tradeoffs.map((t) => <li key={t}>{t}</li>)}
                                </ul>
                              </div>
                            )}
                          </div>
                          
                          <div className="space-y-3">
                            <div className="rounded-lg bg-[#262626] p-4 border border-white/5">
                              <div className="flex justify-between items-center mb-2">
                                <span className="text-xs font-semibold text-gray-300 tracking-wider">RUNTIME</span>
                                <span className="text-xs text-green-400 px-2 py-0.5 rounded bg-white/5 border border-white/10">{comparison.runtime.winner}</span>
                              </div>
                              <p className="text-sm text-gray-400">{comparison.runtime.interpretation}</p>
                            </div>
                            <div className="rounded-lg bg-[#262626] p-4 border border-white/5">
                              <div className="flex justify-between items-center mb-2">
                                <span className="text-xs font-semibold text-gray-300 tracking-wider">OPERATIONS</span>
                                <span className="text-xs text-[#007aff] px-2 py-0.5 rounded bg-white/5 border border-white/10">{comparison.operations.winner}</span>
                              </div>
                              <p className="text-sm text-gray-400">{comparison.operations.interpretation}</p>
                            </div>
                            <div className="rounded-lg bg-[#262626] p-4 border border-white/5">
                              <div className="flex justify-between items-center mb-2">
                                <span className="text-xs font-semibold text-gray-300 tracking-wider">COMPLEXITY</span>
                                <span className="text-xs text-purple-400 px-2 py-0.5 rounded bg-white/5 border border-white/10">{comparison.complexity.winner}</span>
                              </div>
                              <p className="text-sm text-gray-400">{comparison.complexity.interpretation}</p>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="flex flex-col items-center justify-center p-12 text-center text-gray-500">
                          <BarChart3 size={32} className="mb-4 text-gray-600" />
                          <h3 className="text-lg font-medium text-gray-300 mb-2">No Comparison Available</h3>
                          <p className="max-w-md text-sm">Run at least two experiments to compare the current session with a baseline.</p>
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === "share" && (
                     <div className="flex h-full items-center justify-center animate-in fade-in">
                       {sharePayload ? (
                         <div className="max-w-md w-full rounded-xl border border-white/10 bg-[#262626] p-6 text-center">
                           <Share2 size={32} className="mx-auto text-blue-400 mb-4" />
                           <h3 className="text-lg font-medium text-white mb-2">Share Link Generated</h3>
                           <p className="text-sm text-gray-400 mb-6">Anyone with the token can recreate your exact environment snapshot.</p>
                           <div className="rounded-lg bg-[#121212] p-3 mb-6 border border-white/10">
                              <code className="text-xs text-gray-300 break-all">{sharePayload.token}</code>
                           </div>
                           <div className="flex justify-center">
                             <button
                               onClick={() => navigator.clipboard.writeText(sharePayload.token)}
                               className="flex items-center gap-2 rounded-lg bg-white/5 border border-white/10 px-4 py-2 text-sm text-gray-300 hover:bg-white/10 transition-colors"
                             >
                               <Copy size={16} /> Copy Token
                             </button>
                           </div>
                         </div>
                       ) : (
                         <div className="flex flex-col items-center justify-center p-12 text-center text-gray-500">
                           <Share2 size={32} className="mb-4 text-gray-600" />
                           <h3 className="text-lg font-medium text-gray-300 mb-2">No Share Payload Generated</h3>
                           <p className="max-w-md text-sm">Click "Share" in the header to generate a snapshot of your workspace.</p>
                         </div>
                       )}
                     </div>
                  )}

                </div>
              </Panel>
            </PanelGroup>
          </Panel>
        </PanelGroup>
      </main>
    </div>
  );
}
