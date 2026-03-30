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
} from "lucide-react";
import { startTransition, useEffect, useMemo, useState } from "react";

import { backendApi, ApiError } from "@/lib/api";
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
  if (preset.input_kind === "numbers") {
    return "12";
  }
  if (preset.input_kind === "string") {
    return "abracadabra";
  }
  return "[5, 3, 8, 1, 2]";
}

function parseInputSizes(inputSizesText: string) {
  return inputSizesText
    .split(",")
    .map((value) => Number.parseInt(value.trim(), 10))
    .filter((value) => Number.isFinite(value) && value > 0);
}

function toComparisonComplexity(input: PlaygroundExperimentResponse["complexity_estimate"]): ComparisonComplexityInput | undefined {
  if (!input) {
    return undefined;
  }

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

function tabLabel(active: boolean) {
  return clsx(
    "rounded-full px-4 py-2 text-sm font-medium transition",
    active ? "bg-[#1a130c] text-[#f5e6cd] shadow-[0_10px_30px_rgba(26,19,12,0.35)]" : "text-[#6a6c63] hover:bg-white/70",
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

  const statusQuery = useQuery({
    queryKey: ["playground-status"],
    queryFn: backendApi.getStatus,
    refetchInterval: 20_000,
  });

  const presetsQuery = useQuery({
    queryKey: ["presets"],
    queryFn: backendApi.listPresets,
  });

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
      startTransition(() => {
        applyPreset(preset, buildSampleInput(preset));
      });
    }
  }, [applyPreset, presetsQuery.data, selectedPresetSlug]);

  const runMutation = useMutation({
    mutationFn: backendApi.runCode,
    onSuccess: (payload) => {
      startTransition(() => {
        publishRun(payload);
      });
      setFeedback(`Run finished in ${formatRuntime(payload.execution.runtime_ms)}.`);
    },
    onError: (error) => {
      setFeedback(error instanceof ApiError ? error.message : "Run failed.");
    },
  });

  const explanationMutation = useMutation({
    mutationFn: backendApi.generateExplanation,
    onSuccess: (payload) => {
      startTransition(() => {
        publishExplanation(payload);
      });
    },
    onError: () => {
      startTransition(() => {
        publishExplanation(null);
      });
    },
  });

  const comparisonMutation = useMutation({
    mutationFn: backendApi.compareExperiments,
    onSuccess: (payload) => {
      startTransition(() => {
        publishComparison(payload);
      });
    },
    onError: () => {
      startTransition(() => {
        publishComparison(null);
      });
    },
  });

  const experimentMutation = useMutation({
    mutationFn: backendApi.runExperiment,
    onSuccess: async (payload) => {
      const previousExperiment = usePlaygroundStore.getState().experimentResponse;
      startTransition(() => {
        publishExperiment(payload);
      });

      const requests: Promise<unknown>[] = [];
      if (payload.complexity_estimate) {
        requests.push(
          explanationMutation.mutateAsync({
            metrics_snapshot: payload.metrics_snapshot,
            complexity_estimate: payload.complexity_estimate,
            max_sections: 5,
          }),
        );
      } else {
        startTransition(() => {
          publishExplanation(null);
        });
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
          }),
        );
      }

      await Promise.all(requests);
      setFeedback(`Experiment completed across ${payload.runs.length} runs.`);
    },
    onError: (error) => {
      setFeedback(error instanceof ApiError ? error.message : "Experiment failed.");
    },
  });

  const shareMutation = useMutation({
    mutationFn: backendApi.createShare,
    onSuccess: (payload) => {
      startTransition(() => {
        publishShare(payload);
      });
      setFeedback("Share token generated.");
    },
    onError: (error) => {
      setFeedback(error instanceof ApiError ? error.message : "Share generation failed.");
    },
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

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(236,183,92,0.28),_transparent_28%),linear-gradient(180deg,_#f8f1df_0%,_#efe7d3_38%,_#f7f4ee_100%)] text-[#1d211d]">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(39,37,31,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(39,37,31,0.04)_1px,transparent_1px)] bg-[size:28px_28px] opacity-40 pointer-events-none" />
      <div className="relative mx-auto flex min-h-screen max-w-[1660px] flex-col px-4 py-4 sm:px-6 lg:px-8">
        <header className="panel-shell mb-4 grid gap-4 px-5 py-5 lg:grid-cols-[1.3fr_0.8fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[#8d5e31]">Big O Playground</p>
            <h1 className="mt-2 max-w-3xl text-3xl font-semibold tracking-[-0.04em] text-[#161815] sm:text-4xl">
              Interactive runtime lab for scaling behavior, hotspot analysis, and algorithm tradeoffs.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-[#4f5047]">
              Write Python, run controlled experiments, inspect hot lines, and compare growth curves without leaving the
              same workspace.
            </p>
          </div>
          <div className="grid gap-3 rounded-[24px] border border-white/55 bg-white/72 p-4 shadow-[0_16px_40px_rgba(45,35,20,0.08)]">
            <div className="flex items-center justify-between text-sm text-[#4f5047]">
              <span className="inline-flex items-center gap-2 font-medium text-[#1d211d]">
                <Activity size={16} className="text-[#b26e2f]" />
                {statusQuery.data?.mode ?? "loading"}
              </span>
              <span>{statusQuery.data?.backend_status.execution_backend ?? "..."}</span>
            </div>
            <div className="grid grid-cols-3 gap-3 text-xs text-[#4f5047]">
              <div>
                <p className="uppercase tracking-[0.18em] text-[#8d5e31]">Sandbox</p>
                <p className="mt-1 font-medium text-[#1d211d]">
                  {statusQuery.data?.backend_status.docker_image_available ? "Docker ready" : "Local fallback"}
                </p>
              </div>
              <div>
                <p className="uppercase tracking-[0.18em] text-[#8d5e31]">Queue</p>
                <p className="mt-1 font-medium text-[#1d211d]">{statusQuery.data?.backend_status.queue_backend ?? "..."}</p>
              </div>
              <div>
                <p className="uppercase tracking-[0.18em] text-[#8d5e31]">Memory cap</p>
                <p className="mt-1 font-medium text-[#1d211d]">{statusQuery.data?.backend_status.memory_limit_mb ?? 0} MB</p>
              </div>
            </div>
            {feedback ? <p className="text-xs text-[#6a6c63]">{feedback}</p> : null}
          </div>
        </header>

        <div className="grid flex-1 gap-4 lg:grid-cols-[260px_minmax(0,1fr)_320px]">
          <aside className="panel-shell flex min-h-[720px] flex-col overflow-hidden p-0">
            <div className="border-b border-black/8 px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8d5e31]">Preset Library</p>
              <p className="mt-2 text-sm text-[#4f5047]">Load a reference algorithm, then mutate it and rerun the lab.</p>
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-3">
              {presetsQuery.isLoading ? (
                <div className="flex items-center gap-2 px-2 py-6 text-sm text-[#6a6c63]">
                  <LoaderCircle className="animate-spin" size={16} />
                  Loading presets...
                </div>
              ) : null}
              {Object.entries(groupedPresets).map(([category, presets]) => (
                <section key={category} className="mb-5">
                  <h2 className="px-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8d5e31]">
                    {category.replaceAll("-", " ")}
                  </h2>
                  <div className="mt-2 space-y-1">
                    {presets.map((preset) => (
                      <button
                        key={preset.slug}
                        type="button"
                        className={clsx(
                          "w-full rounded-[18px] px-3 py-3 text-left transition",
                          selectedPresetSlug === preset.slug
                            ? "bg-[#1a130c] text-[#f7ead5] shadow-[0_15px_35px_rgba(26,19,12,0.28)]"
                            : "hover:bg-white/65",
                        )}
                        onClick={() =>
                          startTransition(() => {
                            applyPreset(preset, buildSampleInput(preset));
                          })
                        }
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-medium">{preset.name}</p>
                            <p
                              className={clsx(
                                "mt-1 text-xs leading-5",
                                selectedPresetSlug === preset.slug ? "text-[#dcc39c]" : "text-[#5b5d54]",
                              )}
                            >
                              {preset.summary}
                            </p>
                          </div>
                          <ArrowUpRight size={15} className={selectedPresetSlug === preset.slug ? "text-[#e6bc78]" : "text-[#8d5e31]"} />
                        </div>
                      </button>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </aside>

          <main className="flex min-h-[720px] flex-col gap-4">
            <section className="panel-shell p-4 sm:p-5">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8d5e31]">Workspace</p>
                  <h2 className="mt-1 text-xl font-semibold tracking-[-0.03em] text-[#161815]">
                    {selectedPreset?.name ?? "Custom analysis surface"}
                  </h2>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="inline-flex items-center gap-2 rounded-full bg-[#17120d] px-4 py-2 text-sm font-medium text-[#f7ead5] transition hover:bg-[#2a1e12]"
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
                    {runMutation.isPending ? <LoaderCircle className="animate-spin" size={16} /> : <Play size={16} />}
                    Run once
                  </button>
                  <button
                    type="button"
                    className="inline-flex items-center gap-2 rounded-full border border-[#18120c]/12 bg-white/76 px-4 py-2 text-sm font-medium text-[#18120c] transition hover:border-[#18120c]/20 hover:bg-white"
                    onClick={runExperiment}
                    disabled={experimentMutation.isPending}
                  >
                    {experimentMutation.isPending ? <LoaderCircle className="animate-spin" size={16} /> : <FlaskConical size={16} />}
                    Run experiment
                  </button>
                  <button
                    type="button"
                    className="inline-flex items-center gap-2 rounded-full border border-[#18120c]/12 bg-white/76 px-4 py-2 text-sm font-medium text-[#18120c] transition hover:border-[#18120c]/20 hover:bg-white"
                    onClick={() =>
                      shareMutation.mutate({
                        kind: "playground-session",
                        label: selectedPreset?.name ?? "Custom session",
                        expires_in_seconds: 60 * 60 * 24,
                        data: {
                          workspace: {
                            code,
                            stdin,
                            inputSizesText,
                            inputKind,
                            inputProfile,
                            repetitions,
                            backend,
                            instrument,
                            timeoutSeconds,
                            memoryLimitMb,
                          },
                          latestRun: runResponse,
                          latestExperiment: experimentResponse,
                          explanation,
                          comparison,
                        },
                      })
                    }
                    disabled={shareMutation.isPending}
                  >
                    {shareMutation.isPending ? <LoaderCircle className="animate-spin" size={16} /> : <Share2 size={16} />}
                    Share
                  </button>
                </div>
              </div>

              <MonacoSurface code={code} onChange={(next) => setField("code", next)} lineMetrics={lineMetrics} />

              <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
                <div className="rounded-[24px] border border-black/8 bg-white/70 p-4 shadow-[0_16px_40px_rgba(45,35,20,0.08)]">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-[#8d5e31]">Input console</h3>
                    <button
                      type="button"
                      className="text-xs font-medium text-[#8d5e31] transition hover:text-[#5e3c20]"
                      onClick={() => {
                        if (selectedPreset) {
                          setField("stdin", buildSampleInput(selectedPreset));
                        }
                      }}
                    >
                      Use sample input
                    </button>
                  </div>
                  <textarea
                    value={stdin}
                    onChange={(event) => setField("stdin", event.target.value)}
                    className="mt-3 h-32 w-full rounded-[18px] border border-black/8 bg-[#f5f1e8] px-4 py-3 text-sm text-[#1d211d] outline-none transition focus:border-[#be7c39] focus:bg-white"
                    spellCheck={false}
                  />
                </div>
                <div className="rounded-[24px] border border-black/8 bg-[#16110d] p-4 text-[#f1e7d1] shadow-[0_24px_60px_rgba(19,14,10,0.32)]">
                  <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-[#e6bc78]">Live output</h3>
                  <pre className="mt-3 max-h-32 overflow-auto whitespace-pre-wrap text-sm leading-6 text-[#e8ddc7]">
                    {runResponse?.execution.stdout || experimentResponse?.runs.at(-1)?.execution.stdout || "Run the code to inspect stdout."}
                  </pre>
                  {(runResponse?.execution.stderr || experimentResponse?.runs.at(-1)?.execution.stderr) && (
                    <div className="mt-3 rounded-[18px] bg-[#2e130f] px-3 py-3 text-xs text-[#ffb7a4]">
                      {runResponse?.execution.stderr || experimentResponse?.runs.at(-1)?.execution.stderr}
                    </div>
                  )}
                </div>
              </div>
            </section>

            <section className="panel-shell p-4 sm:p-5">
              <div className="mb-4 flex flex-wrap gap-2">
                {[
                  ["console", "Console"],
                  ["runtime", "Runtime"],
                  ["operations", "Operations"],
                  ["explanation", "Explanation"],
                  ["comparison", "Comparison"],
                  ["share", "Share"],
                ].map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    className={tabLabel(activeTab === value)}
                    onClick={() => setField("activeTab", value as typeof activeTab)}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {activeTab === "console" ? (
                <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
                  <ConsolePanel runResponse={runResponse} experimentResponse={experimentResponse} />
                  <ExecutionSnapshot runResponse={runResponse} experimentResponse={experimentResponse} />
                </div>
              ) : null}

              {activeTab === "runtime" && experimentResponse ? (
                <MetricChart
                  title="Runtime curve"
                  subtitle="Measured wall-clock runtime across configured input sizes."
                  data={experimentResponse.metrics_snapshot.summary.runtime_series.points}
                  color="#b56d2d"
                />
              ) : null}

              {activeTab === "operations" && experimentResponse ? (
                <MetricChart
                  title="Operation curve"
                  subtitle="Aggregated line execution counts as a proxy for work performed."
                  data={experimentResponse.metrics_snapshot.summary.operations_series.points}
                  color="#1f6c6d"
                />
              ) : null}

              {activeTab === "explanation" ? <ExplanationPanel explanation={explanation} /> : null}
              {activeTab === "comparison" ? <ComparisonPanel comparison={comparison} /> : null}
              {activeTab === "share" ? <SharePanel sharePayload={sharePayload} /> : null}
            </section>
          </main>

          <aside className="panel-shell flex min-h-[720px] flex-col gap-4 p-4">
            <section>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8d5e31]">Experiment controls</p>
              <div className="mt-3 grid gap-3">
                <Field label="Input sizes">
                  <input
                    value={inputSizesText}
                    onChange={(event) => setField("inputSizesText", event.target.value)}
                    className="field-shell"
                  />
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Input kind">
                    <select value={inputKind} onChange={(event) => setField("inputKind", event.target.value as typeof inputKind)} className="field-shell">
                      <option value="array">Array</option>
                      <option value="numbers">Numbers</option>
                      <option value="string">String</option>
                    </select>
                  </Field>
                  <Field label="Profile">
                    <select
                      value={inputProfile}
                      onChange={(event) => setField("inputProfile", event.target.value as typeof inputProfile)}
                      className="field-shell"
                    >
                      <option value="random">Random</option>
                      <option value="sorted">Sorted</option>
                      <option value="reversed">Reversed</option>
                      <option value="duplicate-heavy">Duplicate-heavy</option>
                      <option value="nearly-sorted">Nearly-sorted</option>
                    </select>
                  </Field>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Repetitions">
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={repetitions}
                      onChange={(event) => setField("repetitions", Number(event.target.value))}
                      className="field-shell"
                    />
                  </Field>
                  <Field label="Backend">
                    <select value={backend} onChange={(event) => setField("backend", event.target.value as typeof backend)} className="field-shell">
                      <option value="auto">Auto</option>
                      <option value="local">Local</option>
                      <option value="docker">Docker</option>
                    </select>
                  </Field>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Timeout (s)">
                    <input
                      type="number"
                      min={1}
                      max={30}
                      value={timeoutSeconds}
                      onChange={(event) => setField("timeoutSeconds", Number(event.target.value))}
                      className="field-shell"
                    />
                  </Field>
                  <Field label="Memory (MB)">
                    <input
                      type="number"
                      min={64}
                      max={1024}
                      step={32}
                      value={memoryLimitMb}
                      onChange={(event) => setField("memoryLimitMb", Number(event.target.value))}
                      className="field-shell"
                    />
                  </Field>
                </div>
                <label className="inline-flex items-center gap-3 rounded-[18px] border border-black/8 bg-white/72 px-3 py-3 text-sm text-[#2a2b25]">
                  <input
                    type="checkbox"
                    checked={instrument}
                    onChange={(event) => setField("instrument", event.target.checked)}
                    className="h-4 w-4 accent-[#b56d2d]"
                  />
                  Enable instrumentation and heatmaps
                </label>
              </div>
            </section>

            <section className="rounded-[24px] border border-black/8 bg-white/72 p-4 shadow-[0_16px_40px_rgba(45,35,20,0.08)]">
              <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.18em] text-[#8d5e31]">
                <Gauge size={16} />
                Complexity estimate
              </div>
              {experimentResponse?.complexity_estimate ? (
                <div className="mt-3">
                  <p className="text-3xl font-semibold tracking-[-0.05em] text-[#17120d]">
                    {experimentResponse.complexity_estimate.estimated_class}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-[#4f5047]">
                    {experimentResponse.complexity_estimate.explanation}
                  </p>
                  <p className="mt-3 text-xs uppercase tracking-[0.18em] text-[#8d5e31]">
                    Confidence {Math.round(experimentResponse.complexity_estimate.confidence * 100)}%
                  </p>
                </div>
              ) : (
                <p className="mt-3 text-sm text-[#5b5d54]">Run an experiment to estimate the scaling class.</p>
              )}
            </section>

            <section className="rounded-[24px] border border-black/8 bg-[#17120d] p-4 text-[#f5ead6] shadow-[0_24px_60px_rgba(19,14,10,0.32)]">
              <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.18em] text-[#e6bc78]">
                <BrainCircuit size={16} />
                Hotspots
              </div>
              <div className="mt-3 space-y-3">
                {lineMetrics.slice(0, 4).map((metric) => (
                  <div key={metric.line_number} className="rounded-[18px] bg-white/6 px-3 py-3">
                    <div className="flex items-center justify-between gap-3 text-sm">
                      <span>Line {metric.line_number}</span>
                      <span className="text-[#e6bc78]">{metric.total_execution_count.toLocaleString()} hits</span>
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-white/8">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-[#ffca7a] via-[#f08a37] to-[#dc5d2a]"
                        style={{ width: `${Math.max(metric.percentage_of_total * 100, 6)}%` }}
                      />
                    </div>
                  </div>
                ))}
                {!lineMetrics.length ? <p className="text-sm text-[#d5c2a4]">Instrumentation output will rank hot lines here.</p> : null}
              </div>
            </section>

            <section className="rounded-[24px] border border-black/8 bg-white/72 p-4 shadow-[0_16px_40px_rgba(45,35,20,0.08)]">
              <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.18em] text-[#8d5e31]">
                <Database size={16} />
                Function focus
              </div>
              <div className="mt-3 space-y-3">
                {topFunctions.map((metric) => (
                  <div key={metric.function_name} className="rounded-[18px] border border-black/6 bg-[#f7f4ee] px-3 py-3">
                    <div className="flex items-center justify-between gap-3 text-sm font-medium text-[#17120d]">
                      <span>{metric.function_name}</span>
                      <span>{metric.total_call_count} calls</span>
                    </div>
                    <p className="mt-2 text-xs text-[#5b5d54]">
                      Max depth {metric.max_depth} | self time {metric.self_time_ms.toFixed(2)} ms
                    </p>
                  </div>
                ))}
                {!topFunctions.length ? <p className="text-sm text-[#5b5d54]">Function hotspots will appear after an instrumented experiment.</p> : null}
              </div>
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-[#8d5e31]">{label}</span>
      {children}
    </label>
  );
}

function ConsolePanel({
  runResponse,
  experimentResponse,
}: {
  runResponse: PlaygroundRunResponse | null;
  experimentResponse: PlaygroundExperimentResponse | null;
}) {
  const latestExecution = runResponse?.execution ?? experimentResponse?.runs.at(-1)?.execution ?? null;
  return (
    <section className="rounded-[28px] border border-black/8 bg-[#17120d] p-5 text-[#f5ead6] shadow-[0_24px_60px_rgba(19,14,10,0.32)]">
      <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.18em] text-[#e6bc78]">
        <Binary size={16} />
        Console snapshot
      </div>
      <pre className="mt-4 min-h-[240px] whitespace-pre-wrap text-sm leading-6 text-[#f5ead6]">
        {latestExecution?.stdout || "Run once or execute an experiment to inspect stdout here."}
      </pre>
      {latestExecution?.stderr ? (
        <div className="mt-3 rounded-[20px] bg-[#381612] px-4 py-3 text-xs text-[#ffb7a4]">{latestExecution.stderr}</div>
      ) : null}
    </section>
  );
}

function ExecutionSnapshot({
  runResponse,
  experimentResponse,
}: {
  runResponse: PlaygroundRunResponse | null;
  experimentResponse: PlaygroundExperimentResponse | null;
}) {
  const latestExecution = runResponse?.execution ?? experimentResponse?.runs.at(-1)?.execution ?? null;
  return (
    <section className="rounded-[28px] border border-black/8 bg-white/80 p-5 shadow-[0_16px_40px_rgba(45,35,20,0.08)]">
      <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.18em] text-[#8d5e31]">
        <Sparkles size={16} />
        Run profile
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <Stat label="Status" value={latestExecution?.status ?? "idle"} />
        <Stat label="Runtime" value={latestExecution ? formatRuntime(latestExecution.runtime_ms) : "--"} />
        <Stat label="Backend" value={latestExecution?.backend ?? "--"} />
        <Stat
          label="Instrumented"
          value={latestExecution?.instrumentation ? `${latestExecution.instrumentation.line_numbers.length} lines tracked` : "No"}
        />
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[18px] border border-black/8 bg-[#f7f4ee] px-4 py-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8d5e31]">{label}</p>
      <p className="mt-2 text-lg font-semibold tracking-[-0.03em] text-[#17120d]">{value}</p>
    </div>
  );
}

function ExplanationPanel({ explanation }: { explanation: ReturnType<typeof usePlaygroundStore.getState>["explanation"] }) {
  if (!explanation) {
    return <EmptyState icon={BrainCircuit} title="No explanation yet" description="Run an experiment to generate narrative insights from the metrics." />;
  }

  return (
    <div className="grid gap-4">
      <section className="rounded-[28px] border border-black/8 bg-white/82 p-5 shadow-[0_16px_40px_rgba(45,35,20,0.08)]">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8d5e31]">Headline</p>
        <h3 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-[#161815]">{explanation.headline}</h3>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-[#4f5047]">{explanation.summary}</p>
      </section>
      <div className="grid gap-4 lg:grid-cols-2">
        {explanation.sections.map((section) => (
          <section key={`${section.kind}-${section.title}`} className="rounded-[24px] border border-black/8 bg-[#fdfbf7] p-5 shadow-[0_12px_30px_rgba(45,35,20,0.06)]">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#8d5e31]">{section.kind}</p>
            <h4 className="mt-2 text-lg font-semibold text-[#17120d]">{section.title}</h4>
            <p className="mt-3 text-sm leading-6 text-[#4f5047]">{section.body}</p>
            {section.evidence.length ? (
              <ul className="mt-4 space-y-2 text-xs text-[#6a6c63]">
                {section.evidence.map((item) => (
                  <li key={item}>- {item}</li>
                ))}
              </ul>
            ) : null}
          </section>
        ))}
      </div>
    </div>
  );
}

function ComparisonPanel({ comparison }: { comparison: ReturnType<typeof usePlaygroundStore.getState>["comparison"] }) {
  if (!comparison) {
    return <EmptyState icon={BarChart3} title="No comparison yet" description="Run at least two experiments to compare the latest result against the previous one." />;
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
      <section className="rounded-[28px] border border-black/8 bg-white/82 p-5 shadow-[0_16px_40px_rgba(45,35,20,0.08)]">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8d5e31]">Verdict</p>
        <h3 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-[#17120d]">{comparison.summary.verdict}</h3>
        <p className="mt-3 text-sm leading-6 text-[#4f5047]">
          Confidence {Math.round(comparison.summary.confidence * 100)}% | overall winner {comparison.summary.overall_winner}
        </p>
        {comparison.summary.tradeoffs.length ? (
          <ul className="mt-4 space-y-2 text-sm text-[#4f5047]">
            {comparison.summary.tradeoffs.map((tradeoff) => (
              <li key={tradeoff}>- {tradeoff}</li>
            ))}
          </ul>
        ) : null}
      </section>
      <section className="rounded-[28px] border border-black/8 bg-[#17120d] p-5 text-[#f5ead6] shadow-[0_24px_60px_rgba(19,14,10,0.32)]">
        <div className="space-y-4">
          <ComparisonMetric label="Runtime" value={comparison.runtime.interpretation} winner={comparison.runtime.winner} />
          <ComparisonMetric label="Operations" value={comparison.operations.interpretation} winner={comparison.operations.winner} />
          <ComparisonMetric label="Complexity" value={comparison.complexity.interpretation} winner={comparison.complexity.winner} />
        </div>
      </section>
    </div>
  );
}

function ComparisonMetric({ label, value, winner }: { label: string; value: string; winner: string }) {
  return (
    <div className="rounded-[20px] bg-white/6 px-4 py-4">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-[#e6bc78]">{winner}</span>
      </div>
      <p className="mt-2 text-sm leading-6 text-[#eadcc4]">{value}</p>
    </div>
  );
}

function SharePanel({ sharePayload }: { sharePayload: ReturnType<typeof usePlaygroundStore.getState>["sharePayload"] }) {
  if (!sharePayload) {
    return <EmptyState icon={Share2} title="No share payload yet" description="Generate a share token to capture the current workspace, latest run, and analysis." />;
  }

  return (
    <section className="rounded-[28px] border border-black/8 bg-white/82 p-5 shadow-[0_16px_40px_rgba(45,35,20,0.08)]">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8d5e31]">Share token</p>
      <div className="mt-4 rounded-[22px] border border-black/8 bg-[#f7f4ee] p-4">
        <p className="break-all font-mono text-xs text-[#3f403a]">{sharePayload.token}</p>
      </div>
      <div className="mt-4 flex flex-wrap gap-3">
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-full bg-[#17120d] px-4 py-2 text-sm font-medium text-[#f7ead5]"
          onClick={() => navigator.clipboard.writeText(sharePayload.token)}
        >
          <Copy size={16} />
          Copy token
        </button>
        <div className="inline-flex items-center rounded-full border border-black/10 bg-white px-4 py-2 text-sm text-[#4f5047]">
          {sharePayload.share_path}
        </div>
      </div>
    </section>
  );
}

function EmptyState({
  icon: Icon,
  title,
  description,
}: {
  icon: typeof Sparkles;
  title: string;
  description: string;
}) {
  return (
    <section className="rounded-[28px] border border-dashed border-black/12 bg-white/60 p-8 text-center shadow-[0_10px_24px_rgba(45,35,20,0.05)]">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#f3e4c8] text-[#8d5e31]">
        <Icon size={24} />
      </div>
      <h3 className="mt-4 text-xl font-semibold tracking-[-0.03em] text-[#17120d]">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-[#5b5d54]">{description}</p>
    </section>
  );
}
