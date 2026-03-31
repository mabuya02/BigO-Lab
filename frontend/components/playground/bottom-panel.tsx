"use client";

import clsx from "clsx";
import {
  Activity,
  BarChart3,
  Copy,
  Database,
  Gauge,
  Share2,
  Sparkles,
  Terminal,
} from "lucide-react";
import { Panel } from "react-resizable-panels";
import type { CodeExecutionResult, PresetRead } from "@/lib/types";
import { usePlaygroundStore } from "@/store/playground-store";
import { TabButton, buildSampleInput, formatRuntime } from "./shared";

export function BottomPanel({
  feedback,
  latestExecution,
  selectedPreset,
}: {
  feedback: string | null;
  latestExecution: CodeExecutionResult | null;
  selectedPreset: PresetRead | null;
}) {
  const {
    stdin,
    setField,
    activeTab,
    experimentResponse,
    explanation,
    comparison,
    sharePayload,
  } = usePlaygroundStore();

  return (
    <Panel defaultSize={35} minSize={20} className="rounded-xl border border-white/10 bg-[#1e1e1e] flex flex-col overflow-hidden shadow-2xl">
      <div className="flex h-11 shrink-0 items-center gap-1 overflow-x-auto border-b border-white/10 bg-[#1e1e1e] px-2 hide-scrollbar text-xs">
        <TabButton active={activeTab === "console"} onClick={() => setField("activeTab", "console")} icon={Terminal} label="Input / Output" />
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
          <div className="flex flex-col h-full bg-[#0f0f0f] rounded-xl border border-white/10 overflow-hidden shadow-2xl relative ring-1 ring-white/5">
            {/* Terminal Chrome Header */}
            <div className="flex h-10 shrink-0 items-center justify-between px-4 border-b border-white/5 bg-[#1a1a1a]">
              <div className="flex items-center gap-2">
                <div className="flex gap-1.5 mr-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500/80 shadow-sm" />
                  <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/80 shadow-sm" />
                  <div className="w-2.5 h-2.5 rounded-full bg-green-500/80 shadow-sm" />
                </div>
                <div className="text-[10px] font-mono font-semibold tracking-wider text-gray-500 flex items-center gap-2 uppercase">
                   <Terminal size={12} className="text-green-500"/>
                   sandbox-session-v2
                </div>
              </div>
              <div className="flex items-center gap-3">
                 <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-white/5 border border-white/10 text-[9px] font-mono text-gray-600 uppercase">
                    UTC-0:00
                 </div>
                 {latestExecution && (
                   <span className={clsx("text-[9px] uppercase tracking-widest px-2 py-0.5 rounded font-bold border shadow-sm", latestExecution.status === "completed" ? "text-green-500 bg-green-500/10 border-green-500/20" : "text-red-500 bg-red-500/10 border-red-500/20")}>
                     {latestExecution.status === "completed" ? "PROCESS SUCCESS" : "PROCESS FAILED"}
                   </span>
                 )}
              </div>
            </div>

            {/* Scrollable Console Buffer */}
            <div className="flex-1 overflow-y-auto p-5 font-mono custom-scrollbar selection:bg-[#00f2fe]/20 scroll-smooth">
              <div className="max-w-4xl mx-auto space-y-6">
                 {/* Greeting / Context */}
                 <div className="space-y-1 opacity-50">
                    <div className="text-[10px] text-gray-500 flex items-center gap-2">
                       <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
                       Big O Laboratory Runtime Environment v2.4.1 (linux/amd64)
                    </div>
                    <div className="text-[10px] text-gray-500">Connected to stateless node clusters (local-thread). Running isolated execution.</div>
                 </div>

                 {/* Terminal Session Content */}
                 <div className="space-y-4">
                    {/* User Command / Stdin Section */}
                    <div className="group border-l-2 border-white/5 pl-4 py-1 hover:border-green-500/30 transition-colors">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-[10px] font-bold text-gray-600 tracking-tighter uppercase">Standard Input</span>
                        <div className="h-px flex-1 bg-white/[0.03]"></div>
                        <button
                          type="button"
                          className="px-2 py-0.5 rounded text-[8px] bg-white/5 border border-white/10 text-gray-500 hover:text-white hover:bg-white/10 transition-all uppercase opacity-0 group-hover:opacity-100"
                          onClick={() => { if (selectedPreset) setField("stdin", buildSampleInput(selectedPreset)); }}
                        >
                          [Import Sample]
                        </button>
                      </div>
                      <div className="flex gap-4">
                        <span className="text-[#34d399] select-none font-bold text-sm leading-none mt-1">$</span>
                        <textarea
                          value={stdin}
                          onChange={(event) => setField("stdin", event.target.value)}
                          className="flex-1 min-h-[40px] max-h-[160px] bg-transparent text-sm text-gray-300 outline-none border-none resize-none p-0 leading-relaxed font-mono placeholder:text-gray-800"
                          spellCheck={false}
                          placeholder="Type input here..."
                        />
                      </div>
                    </div>

                    {/* Process Output Section */}
                    <div className="group border-l-2 border-white/5 pl-4 py-1 hover:border-blue-500/30 transition-colors">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-[10px] font-bold text-gray-600 tracking-tighter uppercase font-mono">Process Output</span>
                        <div className="h-px flex-1 bg-white/[0.03]"></div>
                        {latestExecution && <span className="text-[9px] font-mono text-gray-500 italic lowercase">{latestExecution.runtime_ms}ms wall-clock</span>}
                      </div>

                      <div className="flex gap-4">
                        <span className="text-gray-600 select-none font-bold text-sm leading-none mt-1 opacity-40">➜</span>
                        <div className="flex-1 w-full overflow-hidden">
                           {!latestExecution ? (
                             <div className="text-xs text-gray-700 italic space-y-1">
                                <p className="animate-pulse">_ system is idle. submit code for processing...</p>
                             </div>
                           ) : (
                             <div className="space-y-4 font-mono">
                                {latestExecution.stdout ? (
                                   <pre className="text-sm text-blue-50/90 whitespace-pre-wrap leading-relaxed overflow-x-auto selection:bg-[#007aff]/30 drop-shadow-sm">
                                      {latestExecution.stdout}
                                   </pre>
                                ) : (
                                   <div className="text-xs text-gray-700 italic">null sequence (no stdout)</div>
                                )}

                                {latestExecution.stderr && (
                                   <div className="mt-4 rounded-lg bg-red-500/[0.04] border border-red-500/10 p-4 shadow-sm">
                                      <div className="flex items-center gap-2 mb-2 opacity-60">
                                         <div className="w-1.5 h-1.5 rounded-full bg-red-500"></div>
                                         <span className="text-[10px] font-bold text-red-500/80 uppercase tracking-widest">Runtime Buffer (stderr)</span>
                                      </div>
                                      <pre className="text-sm text-red-400/90 whitespace-pre-wrap font-mono leading-relaxed selection:bg-red-500/20">
                                         {latestExecution.stderr}
                                      </pre>
                                   </div>
                                )}
                             </div>
                           )}
                        </div>
                      </div>
                    </div>
                 </div>
                 <div ref={(el) => { if (el) el.scrollIntoView({ behavior: 'smooth', block: 'end' }); }} />
              </div>
            </div>

            {/* Terminal Footer Console Bar */}
            <div className="h-8 shrink-0 border-t border-white/5 bg-[#1a1a1a]/40 px-4 flex items-center justify-between pointer-events-none select-none">
               <div className="flex items-center gap-4 text-[9px] font-mono text-gray-600 uppercase tracking-tighter font-semibold">
                  <span className="flex items-center gap-1.5"><Activity size={10} className="text-gray-700"/> {latestExecution?.backend ?? "stateless-mode"}</span>
                  <span className="opacity-20">|</span>
                  <span className="hidden sm:inline">buffer-encoding: utf-8</span>
               </div>
               <div className="flex items-center gap-3">
                  <div className="h-2 w-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]"></div>
                  <span className="text-[9px] font-mono text-gray-700 font-bold uppercase tracking-widest">Ready</span>
               </div>
            </div>
          </div>
        )}

        {activeTab === "runtime" && experimentResponse && (() => {
          const summary = experimentResponse.metrics_snapshot.summary;
          const points = summary.runtime_series.points;
          const fastest = Math.min(...points.map(p => p.value));
          const slowest = Math.max(...points.map(p => p.value));

          return (
            <div className="w-full flex flex-col gap-5 animate-in fade-in pb-6 pt-2">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="rounded-lg border border-white/5 bg-[#1a1a1a] p-4 shadow-sm">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-[#00b8a3] mb-1">Average Response</p>
                  <p className="text-xl font-mono text-white">{summary.average_runtime_ms.toFixed(2)}ms</p>
                </div>
                <div className="rounded-lg border border-white/5 bg-[#1a1a1a] p-4 shadow-sm">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-500 mb-1">Scale Min</p>
                  <p className="text-xl font-mono text-gray-300">{summary.min_runtime_ms.toFixed(2)}ms</p>
                </div>
                <div className="rounded-lg border border-white/5 bg-[#1a1a1a] p-4 shadow-sm">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-500 mb-1">Scale Max</p>
                  <p className="text-xl font-mono text-gray-300">{summary.max_runtime_ms.toFixed(2)}ms</p>
                </div>
                <div className="rounded-lg border border-white/5 bg-[#1a1a1a] p-4 shadow-sm">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-[#007aff] mb-1">Total Dataset Scans</p>
                  <p className="text-xl font-mono text-white">{summary.total_runs}</p>
                </div>
              </div>

              <div className="rounded-xl border border-white/5 bg-[#121212] overflow-x-auto shadow-sm">
                <table className="w-full text-left text-sm text-gray-300 whitespace-nowrap">
                  <thead className="bg-[#1a1a1a]">
                    <tr>
                      <th className="px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-gray-500 border-b border-white/5">Input Size (N)</th>
                      <th className="px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-gray-500 border-b border-white/5 text-right w-40">Wall-Clock (ms)</th>
                      <th className="px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-gray-500 border-b border-white/5 text-right w-36">Step Delta</th>
                      <th className="px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-gray-500 border-b border-white/5 text-center w-36">Growth Factor</th>
                      <th className="px-5 py-3 text-[10px] font-semibold uppercase tracking-widest text-gray-500 border-b border-white/5">Signal Trace</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 font-mono">
                    {points.map((p, i) => {
                      const prev = i > 0 ? points[i - 1] : null;
                      const ratio = prev && prev.value > 0 ? p.value / prev.value : 0;
                      const delta = prev ? p.value - prev.value : 0;
                      const isFastest = p.value === fastest;
                      const isSlowest = p.value === slowest;
                      
                      let signal = "Baseline Matrix";
                      let signalColor = "text-gray-500 bg-white/5 border-white/10";
                      if (i > 0) {
                         if (ratio > 2.5) { signal = "Sharp Spike"; signalColor = "text-red-400 bg-red-500/10 border-red-500/20"; }
                         else if (ratio > 1.3) { signal = "Linear Growth Jump"; signalColor = "text-orange-400 bg-orange-500/10 border-orange-500/20"; }
                         else { signal = "Stable Vector / Noise"; signalColor = "text-[#00b8a3] bg-[#00b8a3]/10 border-[#00b8a3]/20"; }
                      }

                      return (
                        <tr key={p.input_size} className="hover:bg-white/[0.03] transition-colors">
                          <td className="px-5 py-3 font-medium text-white">{p.input_size.toLocaleString()}</td>
                          <td className="px-5 py-3 text-right flex items-center justify-end gap-2 text-white">
                            {isFastest && <span className="text-[9px] uppercase tracking-widest text-[#00b8a3] bg-[#00b8a3]/10 border border-[#00b8a3]/20 px-1 py-0.5 rounded font-sans">Fastest</span>}
                            {isSlowest && <span className="text-[9px] uppercase tracking-widest text-red-400 bg-red-500/10 border border-red-500/20 px-1 py-0.5 rounded font-sans">Slowest</span>}
                            <span>{p.value.toFixed(2)}</span>
                          </td>
                          <td className={clsx("px-5 py-3 text-right", delta > 0 ? "text-orange-400" : delta < 0 ? "text-[#00b8a3]" : "text-gray-500")}>
                            {i === 0 ? "-" : `${delta > 0 ? "+" : ""}${delta.toFixed(2)} ms`}
                          </td>
                          <td className="px-5 py-3 text-center text-blue-400">
                            {i === 0 ? "-" : `${ratio.toFixed(2)}x`}
                          </td>
                          <td className="px-5 py-3 font-sans">
                             <span className={clsx("px-2.5 py-1 rounded-md text-[9px] uppercase tracking-widest border font-semibold", signalColor)}>
                               {signal}
                             </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })()}

        {activeTab === "operations" && experimentResponse && (() => {
          const summary = experimentResponse.metrics_snapshot.summary;
          const points = summary.operations_series.points;
          
          return (
            <div className="w-full grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6 animate-in fade-in pb-6 pt-2">
              <div className="rounded-xl border border-white/5 bg-[#121212] overflow-x-auto shadow-sm">
                <table className="w-full text-left text-sm text-gray-300 whitespace-nowrap">
                  <thead className="bg-[#1a1a1a]">
                    <tr>
                      <th className="px-5 py-4 text-[10px] font-semibold uppercase tracking-widest text-gray-500 border-b border-white/5 w-40">Input Step (N)</th>
                      <th className="px-5 py-4 text-[10px] font-semibold uppercase tracking-widest text-gray-500 border-b border-white/5 text-right w-48">Raw Work (AST Hits)</th>
                      <th className="px-5 py-4 text-[10px] font-semibold uppercase tracking-widest text-gray-500 border-b border-white/5 text-right">Algorithmic Burden Delta</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 font-mono">
                    {points.map((p, i) => {
                      const prev = i > 0 ? points[i - 1] : null;
                      const ratio = prev && prev.value > 0 ? p.value / prev.value : 0;
                      return (
                        <tr key={p.input_size} className="hover:bg-white/[0.03] transition-colors relative group">
                          <td className="px-5 py-4 font-medium text-white flex items-center gap-3">
                            <div className="w-6 h-6 flex items-center justify-center font-sans text-gray-500 text-[10px] bg-white/5 rounded-full ring-1 ring-white/10">{i+1}</div>
                            {p.input_size.toLocaleString()}
                          </td>
                          <td className="px-5 py-4 text-right text-purple-400">{Math.round(p.value).toLocaleString()} <span className="text-xs text-gray-600 font-sans ml-1">ops</span></td>
                          <td className="px-5 py-4 text-right">
                            {i === 0 ? (
                               <span className="text-gray-500 text-xs">-</span>
                            ) : (
                               <div className="flex items-center justify-end gap-2">
                                  <span className="text-[10px] text-gray-400 border border-white/10 bg-[#1a1a1a] px-1.5 py-1 rounded tracking-widest mr-2 font-sans font-medium">{prev?.input_size} → {p.input_size}:</span>
                                  <span className={clsx("px-2.5 py-1 rounded-md text-[11px] border font-medium font-sans shadow-sm", ratio > 1.8 ? "text-orange-400 bg-orange-500/10 border-orange-500/20" : "text-[#00b8a3] bg-[#00b8a3]/10 border-[#00b8a3]/20")}>
                                     +{ratio.toFixed(1)}x effort
                                  </span>
                               </div>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              
              <div className="space-y-4">
                 <div className="rounded-xl border border-white/5 bg-[#1a1a1a] p-5 shadow-sm relative overflow-hidden">
                   <div className="absolute top-0 right-0 w-24 h-24 bg-[#007aff]/5 rounded-bl-full blur-[10px]"></div>
                   <p className="text-[10px] font-semibold uppercase tracking-widest text-[#007aff] mb-3 flex items-center gap-2 border-b border-white/5 pb-3">
                     <Gauge size={14}/> Dominant Work Focus
                   </p>
                   {summary.dominant_line_number ? (
                     <div className="mt-4 relative z-10">
                       <p className="text-sm text-gray-300 leading-relaxed">
                         Most execution work is concentrated at <strong className="text-white bg-white/10 px-1.5 py-0.5 rounded ml-1 cursor-help hover:ring-1 hover:ring-white/20 transition-all font-mono text-[11px]" title={`Hotspot: Line ${summary.dominant_line_number}`}>Line {summary.dominant_line_number}</strong> — it accounts for the largest share of total line executions.  
                       </p>
                       <div className="mt-4 bg-[#121212] rounded-lg border border-white/5 p-4 flex flex-col gap-1.5 shadow-inner">
                          <span className="text-[10px] text-gray-500 uppercase tracking-widest font-semibold">Total Line Executions</span>
                          <span className="text-[#007aff] font-mono text-xl tracking-tight leading-none">{summary.total_line_executions.toLocaleString()} <span className="text-xs text-gray-500 font-sans tracking-normal uppercase ml-1">hits</span></span>
                       </div>
                       <div className="mt-3 bg-[#121212] rounded-lg border border-white/5 p-4 flex flex-col gap-1.5 shadow-inner">
                          <span className="text-[10px] text-gray-500 uppercase tracking-widest font-semibold">Total Function Calls</span>
                          <span className="text-purple-400 font-mono text-xl tracking-tight leading-none">{summary.total_function_calls.toLocaleString()} <span className="text-xs text-gray-500 font-sans tracking-normal uppercase ml-1">calls</span></span>
                       </div>
                     </div>
                   ) : (
                     <p className="text-sm text-gray-500 italic mt-4 py-3 border border-dashed border-white/10 rounded-lg text-center bg-[#121212]">No instrumentation data. Enable &quot;Instrument Execution&quot; in Experiment settings and re-run.</p>
                   )}
                 </div>

                 <div className="rounded-xl border border-white/5 bg-[#1a1a1a] p-5 shadow-sm">
                   <p className="text-[10px] font-semibold uppercase tracking-widest text-[#ffc01e] mb-2 border-b border-white/5 pb-3">Growth Interpretation</p>
                   <ul className="space-y-4 mt-4 text-xs leading-relaxed text-gray-400">
                     {(() => {
                       const ratios = points.slice(1).map((p, i) => ({
                         from: points[i].input_size,
                         to: p.input_size,
                         ratio: points[i].value > 0 ? p.value / points[i].value : 0,
                       }));
                       const avgRatio = ratios.length > 0 ? ratios.reduce((s, r) => s + r.ratio, 0) / ratios.length : 0;
                       const complexityClass = experimentResponse.complexity_estimate?.estimated_class ?? "unknown";
                       const confidence = experimentResponse.complexity_estimate?.confidence ?? 0;
                       
                       const insights: string[] = [];
                       
                       if (avgRatio < 1.3) {
                         insights.push(`Operations grow slowly (avg ${avgRatio.toFixed(2)}x per step), consistent with sub-linear or constant behavior.`);
                       } else if (avgRatio < 2.2) {
                         insights.push(`Operations grow at ~${avgRatio.toFixed(2)}x per step, suggesting roughly linear scaling.`);
                       } else if (avgRatio < 5) {
                         insights.push(`Operations grow at ~${avgRatio.toFixed(2)}x per step, suggesting super-linear (possibly n·log n) scaling.`);
                       } else {
                         insights.push(`Operations grow at ~${avgRatio.toFixed(1)}x per step, indicating quadratic or worse scaling.`);
                       }
                       
                       if (complexityClass !== "unknown") {
                         insights.push(`The complexity estimator fitted ${complexityClass} with ${Math.round(confidence * 100)}% confidence based on ${points.length} data points.`);
                       }
                       
                       if (ratios.length >= 2) {
                         const first = ratios[0];
                         const last = ratios[ratios.length - 1];
                         if (last.ratio > first.ratio * 1.5) {
                           insights.push(`Growth is accelerating — the effort multiplier climbed from ${first.ratio.toFixed(2)}x to ${last.ratio.toFixed(2)}x as N increased.`);
                         } else if (last.ratio < first.ratio * 0.7) {
                           insights.push(`Growth rate is decelerating — overhead amortizes at larger N (${first.ratio.toFixed(2)}x → ${last.ratio.toFixed(2)}x).`);
                         } else {
                           insights.push(`Growth rate is stable across steps (${first.ratio.toFixed(2)}x → ${last.ratio.toFixed(2)}x), consistent with uniform scaling.`);
                         }
                       }
                       
                       return insights.map((text, idx) => (
                         <li key={idx} className="flex gap-2.5 relative">
                           <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 opacity-80 ${idx === 0 ? "bg-[#ffc01e]" : "bg-[#00b8a3]"}`}></span>
                           <span>{text}</span>
                         </li>
                       ));
                     })()}
                   </ul>
                 </div>
              </div>
            </div>
          );
        })()}

        {activeTab === "explanation" && (
          <div className="w-full animate-in fade-in">
            {explanation ? (
              <div className="space-y-6">
                <div className="rounded-xl border border-white/10 bg-[#262626] p-6">
                  <h3 className="text-xl font-bold tracking-tight text-white mb-2">{explanation.headline}</h3>
                  <p className="text-gray-400 leading-relaxed text-sm">{explanation.summary}</p>
                </div>
                <div className="grid gap-4 grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
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
          <div className="w-full animate-in fade-in">
            {comparison ? (
              <div className="grid gap-6 grid-cols-1 lg:grid-cols-[1fr_1.5fr]">
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
                 <p className="max-w-md text-sm">Click the Share action in the header to generate a snapshot of your workspace.</p>
               </div>
             )}
           </div>
        )}

      </div>
    </Panel>
  );
}
