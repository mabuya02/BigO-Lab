"use client";

import clsx from "clsx";
import type { UseQueryResult } from "@tanstack/react-query";
import {
  BrainCircuit,
  Database,
  FileText,
  FlaskConical,
  Gauge,
  LayoutTemplate,
  LoaderCircle,
  Settings,
  ChevronDown
} from "lucide-react";
import { startTransition, useState } from "react";
import { Panel } from "react-resizable-panels";
import type { ExecutionBackend, InputKind, InputProfile, PresetCatalogRead, PresetRead } from "@/lib/types";
import { usePlaygroundStore } from "@/store/playground-store";
import { TabButton, buildSampleInput } from "./shared";

export function LeftPanel({
  presetsQuery,
  groupedPresets,
}: {
  presetsQuery: UseQueryResult<PresetCatalogRead, Error>;
  groupedPresets: Record<string, PresetRead[]>;
}) {
  const [leftTab, setLeftTab] = useState<"library" | "experiment" | "analysis">("library");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const {
    code,
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
  const codeLines = code.split("\n");

  return (
    <Panel defaultSize={25} minSize={20} className="rounded-xl border border-white/10 bg-[#121212] flex flex-col overflow-hidden shadow-2xl sidebar-panel">
      <div className="flex h-11 shrink-0 items-center justify-start gap-1 border-b border-white/10 bg-[#1a1a1a] px-2 shadow-sm z-10">
        <TabButton active={leftTab === "library"} onClick={() => setLeftTab("library")} icon={FileText} label="Library" />
        <TabButton active={leftTab === "experiment"} onClick={() => setLeftTab("experiment")} icon={FlaskConical} label="Experiment" />
        <TabButton active={leftTab === "analysis"} onClick={() => setLeftTab("analysis")} icon={BrainCircuit} label="Analysis" />
      </div>
      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar bg-[#121212]">
        {leftTab === "library" && (
          <div className="space-y-6 animate-in fade-in duration-300">
            {presetsQuery.isLoading && (
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <LoaderCircle className="animate-spin" size={16} /> Loading library...
              </div>
            )}
            {Object.entries(groupedPresets).map(([category, presets]) => (
              <div key={category} className="space-y-3">
                <h3 className="text-[10px] font-semibold uppercase tracking-widest text-gray-500 mb-2">
                  {category.replaceAll("-", " ")}
                </h3>
                <div className="space-y-2">
                  {presets.map((preset) => (
                    <div key={preset.slug} className="group relative">
                      <button
                        type="button"
                        className={clsx(
                          "w-full rounded-lg px-3 py-3 text-left transition-all relative overflow-hidden",
                          selectedPresetSlug === preset.slug
                            ? "bg-[#262626] border border-white/20 shadow-md ring-1 ring-green-500/20"
                            : "bg-[#1a1a1a] border border-white/5 hover:bg-[#262626] hover:border-white/10"
                        )}
                        onClick={() => startTransition(() => applyPreset(preset, buildSampleInput(preset)))}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <LayoutTemplate size={14} className={selectedPresetSlug === preset.slug ? "text-green-500" : "text-gray-400"} />
                            <span className={clsx("text-sm font-semibold tracking-tight", selectedPresetSlug === preset.slug ? "text-white" : "text-gray-200")}>
                              {preset.name}
                            </span>
                          </div>
                          {preset.expected_complexity && (
                            <span className="shrink-0 ml-2 inline-flex items-center rounded bg-black/40 px-1.5 py-0.5 text-[10px] font-mono text-[#00b8a3] ring-1 ring-[#00b8a3]/20 font-bold tracking-wider">
                              {preset.expected_complexity}
                            </span>
                          )}
                        </div>
                        
                        <p className="text-xs text-gray-400 leading-relaxed mb-3 pr-2 line-clamp-2">
                          {preset.summary}
                        </p>

                        {preset.tags && preset.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1.5">
                            {preset.tags.map(tag => (
                              <span key={tag} className="text-[9px] uppercase tracking-wider font-medium text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/10">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </button>
                      
                      {selectedPresetSlug === preset.slug && (
                         <div className="mt-2 rounded-lg bg-green-500/5 p-3 text-xs text-green-100 border border-green-500/10 animate-in slide-in-from-top-2 fade-in">
                           <p className="mb-2 text-gray-300 leading-relaxed"><strong className="text-green-400 font-medium">Lab Notes:</strong> {preset.description}</p>
                           {preset.notes && preset.notes.length > 0 && (
                             <ul className="list-disc pl-4 space-y-1 mt-2 text-[11px] text-gray-400">
                               {preset.notes.map((note, i) => <li key={i}>{note}</li>)}
                             </ul>
                           )}
                         </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {leftTab === "experiment" && (
          <div className="space-y-4 animate-in fade-in duration-300 pb-8">
            <div className="rounded-lg border border-white/10 bg-[#1a1a1a] p-5 shadow-sm space-y-5">
              <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-300 flex items-center gap-2 border-b border-white/5 pb-3">
                <Database size={14} className="text-blue-400"/> Core Dataset Parameters
              </h3>
              
              <div className="space-y-2">
                <label className="text-xs font-medium text-gray-300">Input Growth Vector (N)</label>
                <input
                  value={inputSizesText}
                  onChange={(event) => setField("inputSizesText", event.target.value)}
                  className="w-full rounded-md border border-white/10 bg-[#121212] px-3 py-2 text-sm text-gray-200 outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all font-mono"
                  placeholder="e.g. 100, 200, 400, 800"
                />
                <p className="text-[10px] text-gray-500">Comma-separated input counts. Ensure exponential spacing for clear scaling curves.</p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs font-medium text-gray-300">Data Schema</label>
                  <select
                    value={inputKind}
                    onChange={(event) => setField("inputKind", event.target.value as InputKind)}
                    className="w-full rounded-md border border-white/10 bg-[#121212] px-3 py-2 text-sm text-gray-200 outline-none focus:border-white/30 transition-all cursor-pointer"
                  >
                    <option value="array">List/Array</option>
                    <option value="numbers">Numeric Scalar</option>
                    <option value="string">Text String</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-medium text-gray-300">Memory Profile</label>
                  <select
                    value={inputProfile}
                    onChange={(event) => setField("inputProfile", event.target.value as InputProfile)}
                    className="w-full rounded-md border border-white/10 bg-[#121212] px-3 py-2 text-sm text-gray-200 outline-none focus:border-white/30 transition-all cursor-pointer"
                  >
                    <option value="random">Random Entropy</option>
                    <option value="sorted">Perfectly Sorted</option>
                    <option value="reversed">Reverse Sorted</option>
                    <option value="duplicate-heavy">Many Duplicates</option>
                    <option value="nearly-sorted">90% Sorted</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-white/10 bg-[#1a1a1a] p-5 shadow-sm space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-300 flex items-center gap-2 border-b border-white/5 pb-3">
                 <Gauge size={14} className="text-orange-400"/> Sampling Configuration
              </h3>
              <div className="space-y-2 flex flex-col">
                <div className="flex justify-between items-center">
                   <label className="text-xs font-medium text-gray-300">Repetitions Per Data Point</label>
                   <span className="text-xs bg-black/40 px-2 py-0.5 rounded text-gray-400 font-mono ring-1 ring-white/10">{repetitions}x</span>
                </div>
                <input
                  type="range" min={1} max={10}
                  value={repetitions}
                  onChange={(event) => setField("repetitions", Number(event.target.value))}
                  className="w-full accent-orange-500 cursor-pointer"
                />
                <p className="text-[10px] text-gray-500 mt-1">Increasing repetitions mitigates OS noise but linearly bumps total scan duration.</p>
              </div>

               <label className="flex items-center gap-3 rounded-lg border border-white/5 bg-[#121212] px-4 py-3 text-sm text-gray-300 cursor-pointer hover:bg-white/5 transition-colors group mt-4">
                <input
                  type="checkbox"
                  checked={instrument}
                  onChange={(event) => setField("instrument", event.target.checked)}
                  className="h-4 w-4 rounded border-gray-600 bg-black text-green-500 focus:ring-green-500/50"
                />
                <div className="flex flex-col">
                   <span className="font-medium group-hover:text-white transition-colors">Instrument Execution Matrix</span>
                   <span className="text-[10px] text-gray-500 mt-0.5">Injects AST trackers to generate Editor Line Heatmaps and operation metrics.</span>
                </div>
              </label>
            </div>

            <div className="rounded-lg border border-white/10 bg-[#1a1a1a] overflow-hidden">
               <button 
                  onClick={() => setShowAdvanced(!showAdvanced)} 
                  className="w-full flex items-center justify-between p-4 bg-transparent hover:bg-white/5 transition-colors text-xs font-semibold uppercase tracking-widest text-gray-400"
               >
                 <div className="flex items-center gap-2"><Settings size={14} className="text-gray-500"/> Infrastructure</div>
                 <ChevronDown size={14} className={clsx("transition-transform duration-200 text-gray-500", showAdvanced && "rotate-180")} />
               </button>
               
               {showAdvanced && (
                 <div className="p-4 pt-0 space-y-4 border-t border-white/5 mt-2 bg-black/20 animate-in slide-in-from-top-2 fade-in">
                    <div className="grid grid-cols-2 gap-4 mt-4">
                      <div className="space-y-2">
                        <label className="text-xs font-medium text-gray-400">Compute Backend</label>
                        <select
                          value={backend}
                          onChange={(event) => setField("backend", event.target.value as ExecutionBackend)}
                          className="w-full rounded-md border border-white/10 bg-[#121212] px-3 py-2 text-sm text-gray-300 outline-none"
                        >
                          <option value="auto">Cluster Routing</option>
                          <option value="local">Local Native Pool</option>
                          <option value="docker">Strict Sandbox</option>
                        </select>
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs font-medium text-gray-400">Max Memory (MB)</label>
                        <input
                          type="number" min={64} max={1024} step={32}
                          value={memoryLimitMb}
                          onChange={(event) => setField("memoryLimitMb", Number(event.target.value))}
                          className="w-full rounded-md border border-white/10 bg-[#121212] px-3 py-2 text-sm text-gray-300 outline-none font-mono"
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-gray-400">Wall Clock Timeout (s)</label>
                      <input
                        type="number" min={1} max={60}
                        value={timeoutSeconds}
                        onChange={(event) => setField("timeoutSeconds", Number(event.target.value))}
                        className="w-full rounded-md border border-white/10 bg-[#121212] px-3 py-2 text-sm text-gray-300 outline-none font-mono"
                      />
                    </div>
                 </div>
               )}
            </div>
          </div>
        )}

        {leftTab === "analysis" && (
          <div className="space-y-5 animate-in fade-in duration-300 pb-8">
            <div className="rounded-xl border border-white/10 bg-[#1a1a1a] p-5 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-[#00b8a3]"></div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-[#00b8a3] mb-4">
                <Gauge size={14} /> Empirical Complexity
              </div>
              {experimentResponse?.complexity_estimate ? (
                <div>
                  <p className="text-4xl font-bold tracking-tight text-white font-mono drop-shadow-md">
                    {experimentResponse.complexity_estimate.estimated_class}
                  </p>
                  <p className="mt-3 text-sm leading-relaxed text-gray-300">
                    {experimentResponse.complexity_estimate.explanation}
                  </p>
                  <div className="mt-4 flex items-center gap-2">
                     <span className="inline-flex items-center rounded-sm bg-black/40 px-2 py-1 text-[11px] font-medium text-gray-400 ring-1 ring-white/10">
                       R² Fit Confidence: <strong className="text-white ml-1">{Math.round(experimentResponse.complexity_estimate.confidence * 100)}%</strong>
                     </span>
                     <span className="inline-flex items-center rounded-sm bg-black/40 px-2 py-1 text-[11px] font-medium text-gray-400 ring-1 ring-white/10">
                       Valid Models Checked: {experimentResponse.complexity_estimate.alternatives.length}
                     </span>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-center text-gray-500">
                  <BrainCircuit size={32} className="mb-3 opacity-30" />
                  <p className="text-sm font-medium text-gray-400 mb-1">Awaiting Telemetry</p>
                  <p className="text-xs max-w-[200px]">Submit an experiment mapping variables to synthesize growth bounds.</p>
                </div>
              )}
            </div>

            <div className="rounded-xl border border-white/10 bg-[#1a1a1a] p-5 shadow-sm">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-[#ffc01e] mb-4 border-b border-white/5 pb-3">
                <BrainCircuit size={14} /> Critical Hotspots
              </div>
              <div className="space-y-3">
                {lineMetrics.slice(0, 4).map((metric) => (
                  <div key={metric.line_number} className="rounded-lg border border-white/5 bg-[#121212] p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
                    <div className="flex items-center justify-between gap-3 mb-2">
                      <span className="text-xs font-medium text-white flex items-center gap-1.5">
                         <span className="bg-[#ffc01e]/20 text-[#ffc01e] px-1.5 py-0.5 rounded text-[10px] font-mono whitespace-nowrap">L: {metric.line_number}</span> 
                      </span>
                      <span className="text-[#ffc01e] font-mono text-[11px] opacity-90">{metric.total_execution_count.toLocaleString()} ops</span>
                    </div>
                    
                    <div className="my-2 rounded bg-black !bg-opacity-50 px-3 py-2 font-mono text-[10px] text-gray-300 overflow-hidden text-ellipsis whitespace-nowrap border border-white/5 shadow-inner leading-relaxed">
                       {codeLines[metric.line_number - 1]?.trim() || "..."}
                    </div>

                    <div className="flex items-center gap-2 mt-2">
                       <span className="text-[10px] text-gray-400 font-medium whitespace-nowrap">Impact Share:</span>
                       <div className="h-1 flex-1 rounded-full bg-black/50 overflow-hidden ring-1 ring-white/5">
                         <div
                           className="h-full rounded-full bg-gradient-to-r from-[#ffc01e] to-[#ff2d55]"
                           style={{ width: `${Math.max(metric.percentage_of_total * 100, 6)}%` }}
                         />
                       </div>
                       <span className="text-[10px] text-gray-300 font-mono w-7 text-right">{(metric.percentage_of_total * 100).toFixed(0)}%</span>
                    </div>
                    
                    <p className="mt-2 text-[10px] text-[#ffc01e]/70 leading-normal">
                      {metric.loop_iterations > 0
                        ? `Loop line executing ${metric.loop_iterations.toLocaleString()} iterations — accounts for ${(metric.percentage_of_total * 100).toFixed(0)}% of total work at nesting level ${metric.nesting_depth}.`
                        : metric.percentage_of_total > 0.3
                        ? `Hot path: ${metric.total_execution_count.toLocaleString()} executions (${(metric.percentage_of_total * 100).toFixed(0)}% of total). Consider optimizing this line.`
                        : `Contributes ${(metric.percentage_of_total * 100).toFixed(1)}% of total execution count (${metric.total_execution_count.toLocaleString()} hits).`}
                    </p>
                  </div>
                ))}
                {!lineMetrics.length && (
                  <div className="py-6 text-center text-sm text-gray-500 italic bg-[#121212] rounded-lg border border-dashed border-white/10">
                    No hotspot data yet. Enable instrumentation and submit an experiment.
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-[#1a1a1a] p-5 shadow-sm">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-[#007aff] mb-4 border-b border-white/5 pb-3">
                <Database size={14} /> Function Topology
              </div>
              <div className="space-y-3">
                {topFunctions.map((metric) => (
                  <div key={metric.function_name} className="rounded-lg border border-white/5 bg-[#121212] p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-white font-mono text-[11px] truncate tracking-tight">{metric.function_name}()</span>
                      <span className="text-[#007aff] font-mono text-[10px] bg-[#007aff]/10 border border-[#007aff]/20 px-1.5 py-0.5 rounded-sm whitespace-nowrap">{metric.total_call_count.toLocaleString()} invokes</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 mt-3">
                       <div className="bg-black/40 rounded p-2 text-center border border-white/5 shadow-inner">
                          <p className="text-[9px] uppercase tracking-wider text-gray-500 font-medium mb-1">Compute Time</p>
                          <p className="text-[#007aff] font-mono text-[11px]">{metric.self_time_ms.toFixed(2)}ms</p>
                       </div>
                       <div className="bg-black/40 rounded p-2 text-center border border-white/5 shadow-inner">
                          <p className="text-[9px] uppercase tracking-wider text-gray-500 font-medium mb-1">Stack Depth</p>
                          <p className="text-purple-400 font-mono text-[11px]">{metric.max_depth}</p>
                       </div>
                    </div>
                    <p className="mt-2 text-[10px] text-[#007aff]/70 leading-normal text-center w-full">
                       {metric.is_recursive 
                         ? `Recursive — ${metric.total_call_count.toLocaleString()} calls, max depth ${metric.max_depth}. Self time ${metric.self_time_ms.toFixed(2)}ms.`
                         : `Called ${metric.total_call_count.toLocaleString()} times. Self time ${metric.self_time_ms.toFixed(2)}ms (${metric.total_time_ms > 0 ? Math.round(metric.self_time_ms / metric.total_time_ms * 100) : 0}% of total).`}
                    </p>
                  </div>
                ))}
                {!topFunctions.length && (
                  <div className="py-6 text-center text-sm text-gray-500 italic bg-[#121212] rounded-lg border border-dashed border-white/10">
                    No structural call frames tracked yet.
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
