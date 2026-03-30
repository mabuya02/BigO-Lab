"use client";

import clsx from "clsx";
import {
  BrainCircuit,
  Database,
  FileText,
  FlaskConical,
  Gauge,
  Info,
  LayoutTemplate,
  LoaderCircle,
  Settings,
} from "lucide-react";
import { startTransition, useState } from "react";
import { Panel } from "react-resizable-panels";
import type { PresetRead } from "@/lib/types";
import { usePlaygroundStore } from "@/store/playground-store";
import { TabButton, buildSampleInput } from "./shared";

export function LeftPanel({ presetsQuery, groupedPresets }: { presetsQuery: any; groupedPresets: Record<string, PresetRead[]> }) {
  const [leftTab, setLeftTab] = useState<"library" | "settings" | "insights">("library");

  const {
    selectedPresetSlug,
    inputSizesText,
    inputKind,
    inputProfile,
    repetitions,
    backend,
    instrument,
    timeoutSeconds,
    memoryLimitMb,
    setField,
    applyPreset,
    experimentResponse,
  } = usePlaygroundStore();

  const lineMetrics = experimentResponse?.metrics_snapshot.line_metrics ?? [];
  const topFunctions = experimentResponse?.metrics_snapshot.function_metrics.slice(0, 4) ?? [];

  return (
    <Panel defaultSize={25} minSize={20} className="rounded-xl border border-white/10 bg-[#1e1e1e] flex flex-col overflow-hidden shadow-2xl">
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
                    onChange={(event) => setField("inputKind", event.target.value as any)}
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
                    onChange={(event) => setField("inputProfile", event.target.value as any)}
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
                    onChange={(event) => setField("backend", event.target.value as any)}
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
  );
}
