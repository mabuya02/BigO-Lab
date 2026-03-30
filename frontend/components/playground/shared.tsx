import clsx from "clsx";
import type { PlaygroundExperimentResponse, PresetRead, ComparisonComplexityInput } from "@/lib/types";

export function buildSampleInput(preset: PresetRead) {
  if (preset.input_kind === "numbers") return "12";
  if (preset.input_kind === "string") return "abracadabra";
  return "[5, 3, 8, 1, 2]";
}

export function parseInputSizes(inputSizesText: string) {
  return inputSizesText
    .split(",")
    .map((value) => Number.parseInt(value.trim(), 10))
    .filter((value) => Number.isFinite(value) && value > 0);
}

export function toComparisonComplexity(input: PlaygroundExperimentResponse["complexity_estimate"]): ComparisonComplexityInput | undefined {
  if (!input) return undefined;
  return {
    estimated_class: input.estimated_class,
    confidence: input.confidence,
    sample_count: input.sample_count,
    explanation: input.explanation,
    evidence: input.evidence,
  };
}

export function formatRuntime(runtimeMs: number) {
  return runtimeMs >= 1000 ? `${(runtimeMs / 1000).toFixed(2)} s` : `${runtimeMs.toFixed(0)} ms`;
}

export function TabButton({ active, onClick, icon: Icon, label }: { active: boolean; onClick: () => void; icon: any; label: string }) {
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
