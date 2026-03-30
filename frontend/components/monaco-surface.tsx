"use client";

import type { Monaco, OnMount } from "@monaco-editor/react";
import dynamic from "next/dynamic";
import { useDeferredValue, useEffect, useRef } from "react";

import type { AggregatedLineMetric, ComplexityEstimate } from "@/lib/types";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

function heatClassName(intensity: number) {
  if (intensity >= 0.8) return "line-heat-4";
  if (intensity >= 0.55) return "line-heat-3";
  if (intensity >= 0.3) return "line-heat-2";
  return "line-heat-1";
}

/**
 * Derive per-line complexity from actual execution counts across input sizes.
 * The `metric.loop_iterations` and `metric.total_execution_count` give us a
 * data-driven signal about how much work each line is doing:
 *  - Lines with zero loop iterations are constant-time accesses → O(1)
 *  - Lines inside loops scale with the execution count relative to total work
 *  - The overall experiment complexity estimate gives the dominant class
 */
function deriveLineComplexity(
  metric: AggregatedLineMetric,
  maxExecCount: number,
  overallComplexity: string | null,
): { label: string; cssClass: string } {
  // If line was never executed, no label
  if (metric.total_execution_count === 0) {
    return { label: "", cssClass: "" };
  }

  const ratio = metric.total_execution_count / maxExecCount;

  // Lines with loop iterations that dominate execution → show the overall complexity
  if (metric.loop_iterations > 0 && ratio >= 0.5 && overallComplexity) {
    const normalized = overallComplexity.replace(/\s+/g, "").toUpperCase();
    if (normalized.includes("N^2") || normalized.includes("N²")) {
      return { label: "O(N²)", cssClass: "complexity-label complexity-o-n2" };
    }
    if (normalized.includes("N^3") || normalized.includes("N³")) {
      return { label: "O(N³)", cssClass: "complexity-label complexity-o-n3" };
    }
    if (normalized.includes("NLOGN") || normalized.includes("N LOG N")) {
      return { label: "O(N·log N)", cssClass: "complexity-label complexity-o-n" };
    }
    if (normalized.includes("LOGN") || normalized.includes("LOG N")) {
      return { label: "O(log N)", cssClass: "complexity-label complexity-o-1" };
    }
    if (normalized.includes("2^N")) {
      return { label: "O(2ᴺ)", cssClass: "complexity-label complexity-o-n4" };
    }
    if (normalized === "O(N)" || normalized === "O(N)") {
      return { label: "O(N)", cssClass: "complexity-label complexity-o-n" };
    }
    // Fallback: show the raw estimated class
    return { label: overallComplexity, cssClass: "complexity-label complexity-o-n" };
  }

  // Lines with loop iterations but lower share → they're linear contributors
  if (metric.loop_iterations > 0) {
    return { label: "O(N)", cssClass: "complexity-label complexity-o-n" };
  }

  // Non-loop lines
  return { label: "O(1)", cssClass: "complexity-label complexity-o-1" };
}

interface MonacoSurfaceProps {
  code: string;
  onChange: (next: string) => void;
  lineMetrics: AggregatedLineMetric[];
  complexityEstimate?: ComplexityEstimate | null;
}

function syncDecorations(
  editor: Parameters<OnMount>[0] | null,
  monaco: Monaco | null,
  metrics: AggregatedLineMetric[],
  currentDecorationIds: string[],
  overallComplexity: string | null,
) {
  if (!editor || !monaco) {
    return currentDecorationIds;
  }

  const model = editor.getModel();
  if (!model) {
    return currentDecorationIds;
  }

  const maxExecutionCount = Math.max(...metrics.map((metric) => metric.total_execution_count), 1);
  const nextDecorations = metrics
    .filter((metric) => metric.line_number <= model.getLineCount())
    .map((metric) => {
      const { label: complexityEq, cssClass: complexityClass } = deriveLineComplexity(
        metric,
        maxExecutionCount,
        overallComplexity,
      );
      
      const combinedClassName = [
        heatClassName(metric.total_execution_count / maxExecutionCount),
        complexityClass
      ].filter(Boolean).join(" ");

      return {
        range: new monaco.Range(metric.line_number, 1, metric.line_number, 1),
        options: {
          isWholeLine: true,
          className: combinedClassName,
          glyphMarginClassName: "line-glyph-hot",
          glyphMarginHoverMessage: {
            value: `Executions: ${metric.total_execution_count.toLocaleString()}\nLoop iterations: ${metric.loop_iterations.toLocaleString()}\nLine complexity: ${complexityEq || "N/A"}${overallComplexity ? `\nOverall: ${overallComplexity}` : ""}`,
          },
        },
      };
    });

  return editor.deltaDecorations(currentDecorationIds, nextDecorations);
}

export function MonacoSurface({ code, onChange, lineMetrics, complexityEstimate }: MonacoSurfaceProps) {
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null);
  const monacoRef = useRef<Monaco | null>(null);
  const decorationIdsRef = useRef<string[]>([]);
  const deferredLineMetrics = useDeferredValue(lineMetrics);
  const estimatedClass = complexityEstimate?.estimated_class ?? null;

  useEffect(() => {
    decorationIdsRef.current = syncDecorations(
      editorRef.current,
      monacoRef.current,
      deferredLineMetrics,
      decorationIdsRef.current,
      estimatedClass,
    );
  }, [deferredLineMetrics, estimatedClass]);

  const handleMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
    editor.updateOptions({
      fontSize: 14,
      minimap: { enabled: false },
      smoothScrolling: true,
      fontLigatures: true,
      lineHeight: 22,
      wordWrap: "on",
      padding: { top: 18, bottom: 18 },
      glyphMargin: true,
      renderLineHighlight: "gutter",
      scrollBeyondLastLine: false,
    });
    decorationIdsRef.current = syncDecorations(editor, monaco, deferredLineMetrics, decorationIdsRef.current, estimatedClass);
  };

  return (
    <div className="h-full w-full overflow-hidden bg-[#1e1e1e]">
      <MonacoEditor
        height="100%"
        defaultLanguage="python"
        language="python"
        theme="vs-dark"
        value={code}
        onChange={(value) => onChange(value ?? "")}
        onMount={handleMount}
        options={{
          automaticLayout: true,
          bracketPairColorization: { enabled: true },
          suggest: { showWords: false },
        }}
      />
    </div>
  );
}
