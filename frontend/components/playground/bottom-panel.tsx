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
import { MetricChart } from "@/components/metric-chart";
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
  );
}
