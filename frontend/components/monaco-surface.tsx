"use client";

import type { Monaco, OnMount } from "@monaco-editor/react";
import dynamic from "next/dynamic";
import { useDeferredValue, useEffect, useRef } from "react";

import type { AggregatedLineMetric } from "@/lib/types";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

function heatClassName(intensity: number) {
  if (intensity >= 0.8) return "line-heat-4";
  if (intensity >= 0.55) return "line-heat-3";
  if (intensity >= 0.3) return "line-heat-2";
  return "line-heat-1";
}

interface MonacoSurfaceProps {
  code: string;
  onChange: (next: string) => void;
  lineMetrics: AggregatedLineMetric[];
}

function syncDecorations(
  editor: Parameters<OnMount>[0] | null,
  monaco: Monaco | null,
  metrics: AggregatedLineMetric[],
  currentDecorationIds: string[],
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
    .map((metric) => ({
      range: new monaco.Range(metric.line_number, 1, metric.line_number, 1),
      options: {
        isWholeLine: true,
        className: heatClassName(metric.total_execution_count / maxExecutionCount),
        glyphMarginClassName: "line-glyph-hot",
        glyphMarginHoverMessage: {
          value: `Executions: ${metric.total_execution_count}\nLoop iterations: ${metric.loop_iterations}`,
        },
      },
    }));

  return editor.deltaDecorations(currentDecorationIds, nextDecorations);
}

export function MonacoSurface({ code, onChange, lineMetrics }: MonacoSurfaceProps) {
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null);
  const monacoRef = useRef<Monaco | null>(null);
  const decorationIdsRef = useRef<string[]>([]);
  const deferredLineMetrics = useDeferredValue(lineMetrics);

  useEffect(() => {
    decorationIdsRef.current = syncDecorations(
      editorRef.current,
      monacoRef.current,
      deferredLineMetrics,
      decorationIdsRef.current,
    );
  }, [deferredLineMetrics]);

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
    decorationIdsRef.current = syncDecorations(editor, monaco, deferredLineMetrics, decorationIdsRef.current);
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
