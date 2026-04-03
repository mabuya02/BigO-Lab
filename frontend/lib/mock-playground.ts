import type {
  AggregatedFunctionMetric,
  AggregatedLineMetric,
  CodeExecutionResult,
  ComparisonComplexityDelta,
  ComparisonHotspotComparison,
  ComparisonReport,
  ComparisonTrendDelta,
  ComplexityEstimate,
  ComplexityFit,
  ExperimentMetricsSnapshot,
  ExecutionBackend,
  ExecutionInstrumentationReport,
  ExplanationResponse,
  ExplanationSection,
  InputKind,
  InputProfile,
  MetricPoint,
  PlaygroundExperimentResponse,
  PlaygroundExperimentRun,
  PlaygroundRunResponse,
  PlaygroundStatusResponse,
  PresetCatalogRead,
  PresetCategory,
  PresetRead,
  SharePayloadRead,
} from "@/lib/types";

const PRESET_ALGORITHMS: PresetRead[] = [
  {
    slug: "bubble-sort",
    name: "Bubble Sort",
    category: "sorting",
    summary: "Nested passes that make quadratic work obvious in the chart.",
    description: "A classic nested-loop sort used to demonstrate why repeated full passes over an array become expensive.",
    language: "python",
    input_kind: "array",
    input_profile: "random",
    expected_complexity: "O(n^2)",
    starter_code: `def bubble_sort(values):\n    items = values[:]\n    for end in range(len(items) - 1, 0, -1):\n        for index in range(end):\n            if items[index] > items[index + 1]:\n                items[index], items[index + 1] = items[index + 1], items[index]\n    return items\n\nsample = [5, 3, 8, 1, 2]\nprint(bubble_sort(sample))\n`,
    tags: ["sorting", "quadratic", "nested-loops"],
    default_input_sizes: [10, 30, 60, 120],
    notes: ["Good for seeing a dominant inner loop.", "Use reversed arrays to exaggerate the work."],
  },
  {
    slug: "merge-sort",
    name: "Merge Sort",
    category: "sorting",
    summary: "Divide-and-conquer with a smoother n log n growth curve.",
    description: "Recursive splitting and merging usually maps to n log n growth for typical inputs.",
    language: "python",
    input_kind: "array",
    input_profile: "random",
    expected_complexity: "O(n log n)",
    starter_code: `def merge_sort(values):\n    if len(values) <= 1:\n        return values\n\n    middle = len(values) // 2\n    left = merge_sort(values[:middle])\n    right = merge_sort(values[middle:])\n\n    merged = []\n    left_index = 0\n    right_index = 0\n\n    while left_index < len(left) and right_index < len(right):\n        if left[left_index] <= right[right_index]:\n            merged.append(left[left_index])\n            left_index += 1\n        else:\n            merged.append(right[right_index])\n            right_index += 1\n\n    merged.extend(left[left_index:])\n    merged.extend(right[right_index:])\n    return merged\n\nprint(merge_sort([5, 3, 8, 1, 2]))\n`,
    tags: ["sorting", "divide-and-conquer", "recursive"],
    default_input_sizes: [32, 64, 128, 256],
    notes: ["Useful for comparing against bubble sort.", "The merge phase dominates the visible work."],
  },
  {
    slug: "linear-search",
    name: "Linear Search",
    category: "searching",
    summary: "A straight scan that usually tracks linearly with input size.",
    description: "Touches each element until the target is found or the collection ends.",
    language: "python",
    input_kind: "array",
    input_profile: "sorted",
    expected_complexity: "O(n)",
    starter_code: `def linear_search(values, target):\n    for index, value in enumerate(values):\n        if value == target:\n            return index\n    return -1\n\nnumbers = [1, 3, 5, 8, 13, 21]\nprint(linear_search(numbers, 13))\n`,
    tags: ["searching", "linear"],
    default_input_sizes: [10, 50, 100, 250],
    notes: ["Great baseline for comparison work.", "Best case is faster than the average case."],
  },
  {
    slug: "binary-search",
    name: "Binary Search",
    category: "searching",
    summary: "Shrinks the search space in half on each decision.",
    description: "A logarithmic algorithm that makes the gap between theory and observation easy to discuss.",
    language: "python",
    input_kind: "array",
    input_profile: "sorted",
    expected_complexity: "O(log n)",
    starter_code: `def binary_search(values, target):\n    low = 0\n    high = len(values) - 1\n\n    while low <= high:\n        middle = (low + high) // 2\n        if values[middle] == target:\n            return middle\n        if values[middle] < target:\n            low = middle + 1\n        else:\n            high = middle - 1\n\n    return -1\n\nnumbers = [1, 3, 5, 8, 13, 21, 34, 55]\nprint(binary_search(numbers, 21))\n`,
    tags: ["searching", "logarithmic", "branching"],
    default_input_sizes: [16, 64, 256, 1024],
    notes: ["Works best with sorted input.", "The chart should bend much more slowly than linear search."],
  },
  {
    slug: "recursive-fibonacci",
    name: "Recursive Fibonacci",
    category: "recursion",
    summary: "A branching recursion example with visibly explosive growth.",
    description: "Useful for showing how repeated overlapping calls can overwhelm runtime quickly.",
    language: "python",
    input_kind: "numbers",
    input_profile: "random",
    expected_complexity: "O(2^n)",
    starter_code: `def fib(n):\n    if n <= 1:\n        return n\n    return fib(n - 1) + fib(n - 2)\n\nprint(fib(8))\n`,
    tags: ["recursion", "exponential"],
    default_input_sizes: [5, 8, 10, 12],
    notes: ["Perfect for comparing against a memoized variant later.", "The recursion tree fans out quickly."],
  },
];

const COMPLEXITY_RANKS: Record<string, number> = {
  "O(1)": 0,
  "O(log n)": 1,
  "O(n)": 2,
  "O(n log n)": 3,
  "O(n^2)": 4,
  "O(2^n)": 5,
};

type ComplexitySignal = {
  estimatedClass: string;
  confidence: number;
  rationale: string;
  signals: string[];
  alternatives: string[];
};

function delay(ms: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function nowIso() {
  return new Date().toISOString();
}

function randomId(prefix: string) {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Math.random().toString(36).slice(2, 12)}`;
}

function round(value: number, precision = 2) {
  const factor = 10 ** precision;
  return Math.round(value * factor) / factor;
}

function hashText(input: string) {
  let hash = 0;
  for (let index = 0; index < input.length; index += 1) {
    hash = (hash * 31 + input.charCodeAt(index)) >>> 0;
  }
  return hash;
}

function titleCase(slug: string) {
  return slug
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function listPresetCategories(): PresetCategory[] {
  const counts = PRESET_ALGORITHMS.reduce<Record<string, number>>((accumulator, preset) => {
    accumulator[preset.category] = (accumulator[preset.category] ?? 0) + 1;
    return accumulator;
  }, {});

  return Object.entries(counts).map(([slug, presetCount]) => ({
    slug,
    name: titleCase(slug),
    description: `${titleCase(slug)} examples for detached preview mode.`,
    preset_count: presetCount,
  }));
}

function getExecutableLines(code: string) {
  return code
    .split("\n")
    .map((text, index) => ({ lineNumber: index + 1, text, trimmed: text.trim() }))
    .filter((line) => line.trimmed && !line.trimmed.startsWith("#"));
}

function getFunctionNames(code: string) {
  return Array.from(code.matchAll(/^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)/gm)).map((match) => match[1]);
}

function getLoopLines(code: string) {
  return Array.from(code.matchAll(/^\s*(for|while)\b/gm)).map((match) => {
    const beforeMatch = code.slice(0, match.index ?? 0);
    return beforeMatch.split("\n").length;
  });
}

function detectComplexity(code: string): ComplexitySignal {
  const lowered = code.toLowerCase();
  const functionNames = getFunctionNames(code);
  const loopLines = getLoopLines(code);
  const hasNestedLoop = /\n[ \t]+for\b|\n[ \t]+while\b/.test(code) && loopLines.length >= 2;
  const recursiveNames = functionNames.filter((name) => new RegExp(`\\b${name}\\s*\\(`, "g").test(code.replace(new RegExp(`def\\s+${name}\\s*\\(`), "")));
  const hasMemoSignal = /\bmemo\b|\bcache\b|lru_cache|@cache|@lru_cache/.test(lowered);
  const hasMergeSignal = /\bmerge\b|\bmiddle\b|\bmid\b/.test(lowered);
  const hasBinarySignal = /\blow\b|\bhigh\b|\bmiddle\b|\bmid\b/.test(lowered) && /\bwhile\b/.test(lowered);
  const hasSortSignal = /\.sort\(|sorted\(/.test(lowered);

  if (recursiveNames.length > 0 && !hasMemoSignal && /return .*fib\(.*\)\s*\+\s*fib\(/.test(lowered)) {
    return {
      estimatedClass: "O(2^n)",
      confidence: 0.9,
      rationale: "Branching recursive calls suggest repeated overlapping work that grows exponentially.",
      signals: ["branching recursion", "same function called twice per frame"],
      alternatives: ["O(n^2)", "O(n log n)"],
    };
  }

  if ((recursiveNames.length > 0 && hasMergeSignal) || hasSortSignal) {
    return {
      estimatedClass: "O(n log n)",
      confidence: 0.83,
      rationale: "The code combines recursive splitting with merge-like work or built-in sort behavior.",
      signals: ["divide and conquer", "merge or sort signal"],
      alternatives: ["O(n)", "O(n^2)"],
    };
  }

  if (hasBinarySignal) {
    return {
      estimatedClass: "O(log n)",
      confidence: 0.8,
      rationale: "The search window narrows each iteration, which is a logarithmic pattern.",
      signals: ["moving low/high bounds", "midpoint branching"],
      alternatives: ["O(1)", "O(n)"],
    };
  }

  if (hasNestedLoop || loopLines.length >= 2) {
    return {
      estimatedClass: "O(n^2)",
      confidence: 0.84,
      rationale: "Multiple loop layers imply repeated work over the same growing input.",
      signals: ["nested loops", "repeated full-pass work"],
      alternatives: ["O(n log n)", "O(n)"],
    };
  }

  if (loopLines.length === 1 || recursiveNames.length > 0) {
    return {
      estimatedClass: "O(n)",
      confidence: 0.76,
      rationale: "The main work scales with a single pass or a memoized recursive walk.",
      signals: ["single dominant loop or pass"],
      alternatives: ["O(log n)", "O(n log n)"],
    };
  }

  return {
    estimatedClass: "O(1)",
    confidence: 0.61,
    rationale: "The preview could not find an obvious scaling structure, so it treats the code as near constant time.",
    signals: ["no dominant loop detected"],
    alternatives: ["O(log n)", "O(n)"],
  };
}

function growthForComplexity(bigO: string, n: number) {
  const safeN = Math.max(n, 2);
  switch (bigO) {
    case "O(log n)":
      return Math.log2(safeN);
    case "O(n)":
      return safeN;
    case "O(n log n)":
      return safeN * Math.log2(safeN);
    case "O(n^2)":
      return safeN * safeN;
    case "O(2^n)":
      return Math.pow(1.22, Math.min(safeN, 28));
    case "O(1)":
    default:
      return 1;
  }
}

function buildAlternatives(bestClass: string, alternatives: string[], growth: number): ComplexityFit[] {
  const entries = [bestClass, ...alternatives].slice(0, 3);
  return entries.map((bigO, index) => ({
    label: index === 0 ? "best-fit" : `alternative-${index}`,
    big_o: bigO,
    quality: round(Math.max(0.42, 0.92 - index * 0.18), 3),
    rmse: round(growth * (0.06 + index * 0.04), 3),
    normalized_rmse: round(0.08 + index * 0.07, 3),
    slope: round(0.8 + index * 0.11, 3),
    intercept: round(1.4 + index * 0.23, 3),
    valid: true,
    notes: index === 0 ? "Best visual fit in mock preview mode." : "Secondary candidate retained for contrast.",
  }));
}

function buildComplexityEstimate(signal: ComplexitySignal, inputSizes: number[], dominantLineNumber: number | null): ComplexityEstimate {
  const largestInput = inputSizes.at(-1) ?? 1;
  return {
    id: randomId("complexity"),
    experiment_id: null,
    metric_name: "runtime_ms",
    estimated_class: signal.estimatedClass,
    confidence: signal.confidence,
    sample_count: inputSizes.length,
    explanation: signal.rationale,
    alternatives: buildAlternatives(signal.estimatedClass, signal.alternatives, growthForComplexity(signal.estimatedClass, largestInput)),
    evidence: {
      signals: signal.signals,
      dominant_line_number: dominantLineNumber,
      max_input_size: largestInput,
      mode: "detached-preview",
    },
    created_at: nowIso(),
    updated_at: nowIso(),
  };
}

function buildGeneratedInput(inputKind: InputKind, inputProfile: InputProfile, inputSize: number) {
  if (inputKind === "numbers") {
    return {
      payload: inputSize,
      stdin: String(inputSize),
      metadata: { profile: inputProfile, preview: true },
    };
  }

  if (inputKind === "string") {
    const alphabet = inputProfile === "duplicate-heavy" ? "aaaaabbbbb" : "algorithms";
    const value = Array.from({ length: inputSize }, (_, index) => alphabet[index % alphabet.length]).join("");
    return {
      payload: value,
      stdin: value,
      metadata: { profile: inputProfile, preview: true, length: value.length },
    };
  }

  let values = Array.from({ length: inputSize }, (_, index) => index + 1);
  if (inputProfile === "random") {
    values = values.map((value, index) => (index * 17 + 11) % (inputSize + 7));
  } else if (inputProfile === "reversed") {
    values = [...values].reverse();
  } else if (inputProfile === "duplicate-heavy") {
    values = values.map((value) => value % 5);
  } else if (inputProfile === "nearly-sorted") {
    values = [...values];
    if (values.length > 4) {
      const penultimateIndex = values.length - 2;
      const lastIndex = values.length - 1;
      [values[1], values[2]] = [values[2], values[1]];
      [values[penultimateIndex], values[lastIndex]] = [values[lastIndex], values[penultimateIndex]];
    }
  }

  return {
    payload: values,
    stdin: JSON.stringify(values),
    metadata: { profile: inputProfile, preview: true, length: values.length },
  };
}

function buildLineMetrics(
  code: string,
  runtimePoints: MetricPoint[],
  operationsPoints: MetricPoint[],
  instrumented: boolean,
): AggregatedLineMetric[] {
  if (!instrumented) {
    return [];
  }

  const executableLines = getExecutableLines(code);
  if (!executableLines.length) {
    return [];
  }

  const totalOperations = operationsPoints.reduce((sum, point) => sum + point.value, 0);
  const totalRuntime = runtimePoints.reduce((sum, point) => sum + point.value, 0);
  const loopLineSet = new Set(getLoopLines(code));

  const weightedLines = executableLines.map((line, index) => {
    const isLoop = loopLineSet.has(line.lineNumber);
    const isFunction = line.trimmed.startsWith("def ");
    const weight = isLoop ? 1.8 : isFunction ? 1.2 : index === 0 ? 0.95 : 0.75;
    return { ...line, weight };
  });
  const totalWeight = weightedLines.reduce((sum, line) => sum + line.weight, 0);

  return weightedLines
    .map((line) => {
      const share = line.weight / totalWeight;
      const totalExecutionCount = Math.max(1, Math.round(totalOperations * share));
      return {
        line_number: line.lineNumber,
        total_execution_count: totalExecutionCount,
        total_time_ms: round(totalRuntime * share, 3),
        average_time_ms: round((totalRuntime * share) / Math.max(runtimePoints.length, 1), 3),
        percentage_of_total: share,
        nesting_depth: loopLineSet.has(line.lineNumber) ? (getLoopLines(code).length > 1 ? 2 : 1) : 0,
        loop_iterations: loopLineSet.has(line.lineNumber) ? totalExecutionCount : 0,
        branch_visits: line.trimmed.startsWith("if ") ? Math.round(totalExecutionCount * 0.35) : 0,
      };
    })
    .sort((left, right) => right.total_execution_count - left.total_execution_count);
}

function buildFunctionMetrics(
  code: string,
  runtimePoints: MetricPoint[],
  lineMetrics: AggregatedLineMetric[],
  instrumented: boolean,
): AggregatedFunctionMetric[] {
  if (!instrumented) {
    return [];
  }

  const names = getFunctionNames(code);
  if (!names.length) {
    return [];
  }

  const totalRuntime = runtimePoints.reduce((sum, point) => sum + point.value, 0);
  const recursiveNames = names.filter((name) => new RegExp(`\\b${name}\\s*\\(`, "g").test(code.replace(new RegExp(`def\\s+${name}\\s*\\(`), "")));

  return names.map((name, index) => {
    const runtimeShare = 1 / names.length;
    const loopDensity = lineMetrics.filter((metric) => metric.nesting_depth > 0).length;
    const totalCallCount = Math.max(1, Math.round((lineMetrics[index]?.total_execution_count ?? 24) / Math.max(loopDensity, 1)));
    const totalTimeMs = round(totalRuntime * runtimeShare, 3);
    return {
      function_name: name,
      qualified_name: null,
      total_call_count: totalCallCount,
      total_time_ms: totalTimeMs,
      average_time_ms: round(totalTimeMs / totalCallCount, 4),
      self_time_ms: round(totalTimeMs * 0.42, 3),
      max_depth: recursiveNames.includes(name) ? 6 : 2,
      is_recursive: recursiveNames.includes(name),
    };
  });
}

function buildInstrumentationReport(
  code: string,
  lineMetrics: AggregatedLineMetric[],
  functionMetrics: AggregatedFunctionMetric[],
): ExecutionInstrumentationReport | null {
  if (!lineMetrics.length) {
    return null;
  }

  return {
    line_counts: Object.fromEntries(lineMetrics.map((metric) => [String(metric.line_number), metric.total_execution_count])),
    function_call_counts: Object.fromEntries(functionMetrics.map((metric) => [metric.function_name, metric.total_call_count])),
    loop_iteration_counts: Object.fromEntries(
      lineMetrics.filter((metric) => metric.loop_iterations > 0).map((metric) => [String(metric.line_number), metric.loop_iterations]),
    ),
    line_numbers: getExecutableLines(code).map((line) => line.lineNumber),
    function_names: functionMetrics.map((metric) => metric.function_name),
    loop_line_numbers: getLoopLines(code),
  };
}

function buildMetricSnapshot(
  code: string,
  inputSizes: number[],
  runtimePoints: MetricPoint[],
  operationsPoints: MetricPoint[],
  instrumented: boolean,
): ExperimentMetricsSnapshot {
  const lineMetrics = buildLineMetrics(code, runtimePoints, operationsPoints, instrumented);
  const functionMetrics = buildFunctionMetrics(code, runtimePoints, lineMetrics, instrumented);
  const totalRuntime = runtimePoints.reduce((sum, point) => sum + point.value, 0);
  const runtimeValues = runtimePoints.map((point) => point.value);
  const totalOperations = lineMetrics.reduce((sum, metric) => sum + metric.total_execution_count, 0);

  return {
    summary: {
      total_runs: inputSizes.length,
      input_sizes: inputSizes,
      average_runtime_ms: round(totalRuntime / Math.max(runtimePoints.length, 1), 3),
      min_runtime_ms: runtimeValues.length ? Math.min(...runtimeValues) : 0,
      max_runtime_ms: runtimeValues.length ? Math.max(...runtimeValues) : 0,
      total_runtime_ms: round(totalRuntime, 3),
      total_line_executions: totalOperations,
      total_function_calls: functionMetrics.reduce((sum, metric) => sum + metric.total_call_count, 0),
      dominant_line_number: lineMetrics[0]?.line_number ?? null,
      dominant_function_name: functionMetrics[0]?.function_name ?? null,
      runtime_series: {
        label: "runtime_ms",
        points: runtimePoints,
      },
      operations_series: {
        label: "line_executions",
        points: operationsPoints,
      },
    },
    line_metrics: lineMetrics,
    function_metrics: functionMetrics,
  };
}

function buildRunStdout(code: string, input: string, runtimeMs: number, complexityClass: string) {
  const previewLines = [
    "Big O Playground detached preview",
    `Code lines: ${code.split("\n").filter(Boolean).length}`,
    `Input snapshot: ${input || "(empty)"}`,
    `Predicted scaling: ${complexityClass}`,
    `Synthetic runtime: ${round(runtimeMs, 2)} ms`,
  ];
  return previewLines.join("\n");
}

function buildExecutionResult(
  code: string,
  input: string,
  backend: ExecutionBackend,
  instrument: boolean,
  runtimeMs: number,
  operations: number,
  complexityClass: string,
  lineMetrics: AggregatedLineMetric[],
  functionMetrics: AggregatedFunctionMetric[],
): CodeExecutionResult {
  return {
    status: "completed",
    stdout: buildRunStdout(code, input, runtimeMs, complexityClass),
    stderr: "",
    exit_code: 0,
    runtime_ms: round(runtimeMs, 3),
    backend: backend === "auto" ? "mock-local" : `mock-${backend}`,
    timed_out: false,
    truncated_stdout: false,
    truncated_stderr: false,
    instrumentation: instrument
      ? buildInstrumentationReport(
          code,
          lineMetrics.map((metric) => ({
            ...metric,
            total_execution_count: Math.max(1, Math.round(metric.total_execution_count * (operations / Math.max(1, lineMetrics.reduce((sum, item) => sum + item.total_execution_count, 0))))),
          })),
          functionMetrics,
        )
      : null,
  };
}

function buildExplanationResponse(metricsSnapshot: ExperimentMetricsSnapshot, complexityEstimate: ComplexityEstimate | null, maxSections = 5): ExplanationResponse {
  const sections: ExplanationSection[] = [];
  const dominantLine = metricsSnapshot.summary.dominant_line_number;
  const dominantFunction = metricsSnapshot.summary.dominant_function_name;
  const runtimePoints = metricsSnapshot.summary.runtime_series.points;
  const startRuntime = runtimePoints[0]?.value ?? 0;
  const endRuntime = runtimePoints.at(-1)?.value ?? 0;

  sections.push({
    kind: "summary",
    title: "Observed curve",
    body: `The detached preview grows from ${round(startRuntime)} ms to ${round(endRuntime)} ms across ${runtimePoints.length} configured input sizes.`,
    evidence: [
      `input sizes: ${metricsSnapshot.summary.input_sizes.join(", ")}`,
      `total synthetic runtime: ${round(metricsSnapshot.summary.total_runtime_ms)} ms`,
    ],
  });

  if (dominantLine !== null) {
    sections.push({
      kind: "dominance",
      title: "Dominant line",
      body: `Line ${dominantLine} receives the largest execution share in this preview, so the editor heatmap emphasizes it.`,
      evidence: [`dominant line: ${dominantLine}`],
    });
  }

  if (complexityEstimate) {
    sections.push({
      kind: "complexity",
      title: "Complexity signal",
      body: complexityEstimate.explanation,
      evidence: (complexityEstimate.evidence.signals as string[] | undefined) ?? [],
    });
  }

  if (dominantFunction) {
    sections.push({
      kind: "loop",
      title: "Function focus",
      body: `${dominantFunction} absorbs the largest share of synthetic function time in the detached preview.`,
      evidence: [`dominant function: ${dominantFunction}`],
    });
  }

  sections.push({
    kind: "caveat",
    title: "Preview caveat",
    body: "This frontend is using dummy data only. The shapes are realistic enough for UI work, but no Python is executing here.",
    evidence: ["frontend and backend are detached", "all metrics are synthetic"],
  });

  return {
    headline: complexityEstimate ? `Preview trend points toward ${complexityEstimate.estimated_class}` : "Preview trend is still ambiguous",
    summary: "Use this detached mode to build and review the interface without needing a live execution engine.",
    complexity_class: complexityEstimate?.estimated_class ?? null,
    confidence: complexityEstimate?.confidence ?? null,
    dominant_line_number: dominantLine,
    dominant_function_name: dominantFunction,
    sections: sections.slice(0, maxSections),
    caveats: ["Synthetic preview data only.", "No backend request was made."],
  };
}

function buildTrendDelta(label: string, leftPoints: MetricPoint[], rightPoints: MetricPoint[]): ComparisonTrendDelta {
  const leftStart = leftPoints[0]?.value ?? 0;
  const leftEnd = leftPoints.at(-1)?.value ?? 0;
  const rightStart = rightPoints[0]?.value ?? 0;
  const rightEnd = rightPoints.at(-1)?.value ?? 0;
  const leftGrowthRate = leftEnd / Math.max(leftStart, 1);
  const rightGrowthRate = rightEnd / Math.max(rightStart, 1);
  const winner = leftEnd === rightEnd ? "tie" : leftEnd < rightEnd ? "left" : "right";
  const delta = round(rightEnd - leftEnd, 3);
  const percentChange = round((Math.abs(delta) / Math.max(Math.max(leftEnd, rightEnd), 1)) * 100, 3);

  return {
    metric_name: label,
    left_start: round(leftStart, 3),
    left_end: round(leftEnd, 3),
    right_start: round(rightStart, 3),
    right_end: round(rightEnd, 3),
    left_growth_rate: round(leftGrowthRate, 3),
    right_growth_rate: round(rightGrowthRate, 3),
    delta,
    percent_change: percentChange,
    winner,
    interpretation:
      winner === "tie"
        ? `${label} tracks almost identically in this preview.`
        : `${winner} shows the lower ${label.toLowerCase()} curve at the largest input size.`,
  };
}

function buildComplexityDelta(
  left: { estimated_class?: string; confidence?: number } | undefined,
  right: { estimated_class?: string; confidence?: number } | undefined,
): ComparisonComplexityDelta {
  const leftClass = left?.estimated_class ?? null;
  const rightClass = right?.estimated_class ?? null;
  const leftRank = leftClass ? COMPLEXITY_RANKS[leftClass] ?? null : null;
  const rightRank = rightClass ? COMPLEXITY_RANKS[rightClass] ?? null : null;
  const winner = leftRank === rightRank ? "tie" : (leftRank ?? 0) < (rightRank ?? 0) ? "left" : "right";

  return {
    left_class: leftClass,
    right_class: rightClass,
    left_rank: leftRank,
    right_rank: rightRank,
    delta: leftRank !== null && rightRank !== null ? rightRank - leftRank : null,
    confidence_delta:
      left?.confidence !== undefined && right?.confidence !== undefined ? round((right.confidence - left.confidence) * 100, 3) : null,
    winner,
    interpretation:
      winner === "tie"
        ? "Both preview runs map to the same complexity class."
        : `${winner} has the lower asymptotic class in detached preview mode.`,
  };
}

function buildHotspotComparison(
  kind: "line" | "function",
  leftMetric: AggregatedLineMetric | AggregatedFunctionMetric | undefined,
  rightMetric: AggregatedLineMetric | AggregatedFunctionMetric | undefined,
): ComparisonHotspotComparison {
  const leftValue = leftMetric && "total_execution_count" in leftMetric ? leftMetric.total_execution_count : leftMetric?.total_call_count ?? 0;
  const rightValue = rightMetric && "total_execution_count" in rightMetric ? rightMetric.total_execution_count : rightMetric?.total_call_count ?? 0;
  const winner = leftValue === rightValue ? "tie" : leftValue < rightValue ? "left" : "right";

  return {
    kind,
    left_identifier:
      kind === "line"
        ? leftMetric && "line_number" in leftMetric
          ? `line-${leftMetric.line_number}`
          : null
        : leftMetric && "function_name" in leftMetric
          ? leftMetric.function_name
          : null,
    right_identifier:
      kind === "line"
        ? rightMetric && "line_number" in rightMetric
          ? `line-${rightMetric.line_number}`
          : null
        : rightMetric && "function_name" in rightMetric
          ? rightMetric.function_name
          : null,
    left_value: leftValue,
    right_value: rightValue,
    left_share_of_total:
      leftMetric && "percentage_of_total" in leftMetric
        ? leftMetric.percentage_of_total
        : leftValue / Math.max(leftValue + rightValue, 1),
    right_share_of_total:
      rightMetric && "percentage_of_total" in rightMetric
        ? rightMetric.percentage_of_total
        : rightValue / Math.max(leftValue + rightValue, 1),
    delta: round(rightValue - leftValue, 3),
    winner,
    interpretation:
      winner === "tie"
        ? `The top ${kind} hotspot lands at roughly the same load in both previews.`
        : `${winner} has the lighter dominant ${kind} hotspot in the detached preview.`,
  };
}

function buildComparisonReport(payload: {
  left: {
    label: string;
    metrics: ExperimentMetricsSnapshot;
    complexity_estimate?: { estimated_class: string; confidence: number };
  };
  right: {
    label: string;
    metrics: ExperimentMetricsSnapshot;
    complexity_estimate?: { estimated_class: string; confidence: number };
  };
}): ComparisonReport {
  const runtime = buildTrendDelta(payload.left.label, payload.left.metrics.summary.runtime_series.points, payload.right.metrics.summary.runtime_series.points);
  const operations = buildTrendDelta(payload.right.label, payload.left.metrics.summary.operations_series.points, payload.right.metrics.summary.operations_series.points);
  const complexity = buildComplexityDelta(payload.left.complexity_estimate, payload.right.complexity_estimate);
  const hotspots = [
    buildHotspotComparison("line", payload.left.metrics.line_metrics[0], payload.right.metrics.line_metrics[0]),
    buildHotspotComparison("function", payload.left.metrics.function_metrics[0], payload.right.metrics.function_metrics[0]),
  ];

  const winners = [runtime.winner, operations.winner, complexity.winner].filter((winner) => winner !== "tie");
  const leftVotes = winners.filter((winner) => winner === "left").length;
  const rightVotes = winners.filter((winner) => winner === "right").length;
  const overallWinner = leftVotes === rightVotes ? "tie" : leftVotes > rightVotes ? "left" : "right";

  return {
    runtime,
    operations,
    complexity,
    hotspots,
    summary: {
      overall_winner: overallWinner,
      confidence: round(0.56 + Math.abs(leftVotes - rightVotes) * 0.12, 3),
      verdict:
        overallWinner === "tie"
          ? "Both versions land in the same performance band in detached preview mode."
          : `${overallWinner} looks stronger across the current synthetic metrics.`,
      tradeoffs: [
        "Detached preview comparison favors shape and relative trends, not exact runtime.",
        "Run the real backend later if you want actual measured execution.",
      ],
    },
  };
}

function buildRuntimePoints(code: string, inputSizes: number[], complexityClass: string): MetricPoint[] {
  const codeWeight = Math.max(1, getExecutableLines(code).length * 0.45);
  const codeHash = hashText(code);
  return inputSizes.map((inputSize, index) => {
    const growth = growthForComplexity(complexityClass, inputSize);
    const noise = ((codeHash + index * 13) % 7) * 0.35;
    const multiplier = complexityClass === "O(n^2)" ? 0.0042 : complexityClass === "O(n log n)" ? 0.008 : complexityClass === "O(log n)" ? 1.3 : complexityClass === "O(2^n)" ? 2.1 : complexityClass === "O(n)" ? 0.024 : 5.8;
    return {
      input_size: inputSize,
      value: round(codeWeight * multiplier * growth + 6 + noise, 3),
    };
  });
}

function buildOperationPoints(inputSizes: number[], complexityClass: string, code: string): MetricPoint[] {
  const lineWeight = Math.max(3, getExecutableLines(code).length);
  return inputSizes.map((inputSize) => ({
    input_size: inputSize,
    value: Math.max(1, Math.round(growthForComplexity(complexityClass, inputSize) * lineWeight)),
  }));
}

function buildPreviewRunResponse(payload: {
  code: string;
  input: string;
  backend: ExecutionBackend;
  instrument: boolean;
  timeout_seconds?: number;
}): PlaygroundRunResponse {
  const signal = detectComplexity(payload.code);
  const runtimePoints = buildRuntimePoints(payload.code, [Math.max(payload.input.length, 8)], signal.estimatedClass);
  const operationsPoints = buildOperationPoints([Math.max(payload.input.length, 8)], signal.estimatedClass, payload.code);
  const metricsSnapshot = buildMetricSnapshot(payload.code, [Math.max(payload.input.length, 8)], runtimePoints, operationsPoints, payload.instrument);
  const execution = buildExecutionResult(
    payload.code,
    payload.input,
    payload.backend,
    payload.instrument,
    runtimePoints[0]?.value ?? 0,
    operationsPoints[0]?.value ?? 1,
    signal.estimatedClass,
    metricsSnapshot.line_metrics,
    metricsSnapshot.function_metrics,
  );

  return {
    code: payload.code,
    input: payload.input,
    backend_requested: payload.backend,
    instrumented: payload.instrument,
    execution,
  };
}

function buildPreviewExperimentResponse(payload: {
  code: string;
  input_sizes: number[];
  input_kind: InputKind;
  input_profile: InputProfile;
  repetitions: number;
  backend: ExecutionBackend;
  instrument: boolean;
}): PlaygroundExperimentResponse {
  const inputSizes = payload.input_sizes.length ? payload.input_sizes : [10, 50, 100];
  const signal = detectComplexity(payload.code);
  const runtimePoints = buildRuntimePoints(payload.code, inputSizes, signal.estimatedClass);
  const operationsPoints = buildOperationPoints(inputSizes, signal.estimatedClass, payload.code);
  const metricsSnapshot = buildMetricSnapshot(payload.code, inputSizes, runtimePoints, operationsPoints, payload.instrument);
  const complexityEstimate = buildComplexityEstimate(signal, inputSizes, metricsSnapshot.summary.dominant_line_number);

  const runs: PlaygroundExperimentRun[] = inputSizes.flatMap((inputSize, sizeIndex) =>
    Array.from({ length: Math.max(payload.repetitions, 1) }, (_, repetitionIndex) => {
      const generatedInput = buildGeneratedInput(payload.input_kind, payload.input_profile, inputSize);
      const runtimeMs = round((runtimePoints[sizeIndex]?.value ?? 0) * (1 + repetitionIndex * 0.04), 3);
      const operations = Math.round((operationsPoints[sizeIndex]?.value ?? 1) * (1 + repetitionIndex * 0.02));
      return {
        input_size: inputSize,
        repetition_index: repetitionIndex,
        input_kind: payload.input_kind,
        input_profile: payload.input_profile,
        generated_input: generatedInput,
        execution: buildExecutionResult(
          payload.code,
          generatedInput.stdin,
          payload.backend,
          payload.instrument,
          runtimeMs,
          operations,
          signal.estimatedClass,
          metricsSnapshot.line_metrics,
          metricsSnapshot.function_metrics,
        ),
      };
    }),
  );

  return {
    code: payload.code,
    backend_requested: payload.backend,
    instrumented: payload.instrument,
    input_kind: payload.input_kind,
    input_profile: payload.input_profile,
    repetitions: payload.repetitions,
    runs,
    metrics_snapshot: metricsSnapshot,
    complexity_estimate: complexityEstimate,
    operations_complexity_estimate: null,
    orchestration_runtime_ms: round(metricsSnapshot.summary.total_runtime_ms * 0.18 + 11, 3),
  };
}

export const mockPlaygroundApi = {
  async getStatus(): Promise<PlaygroundStatusResponse> {
    await delay(110);
    return {
      mode: "detached-preview",
      description: "Frontend preview mode with local dummy data. No backend calls are active.",
      backend_status: {
        execution_backend: "mock-engine",
        queue_backend: "none",
        local_fallback_enabled: true,
        docker_cli_available: false,
        docker_image_available: false,
        dramatiq_available: false,
        redis_configured: false,
        sandbox_image: "unused",
        default_timeout_seconds: 3,
        max_timeout_seconds: 10,
        memory_limit_mb: 256,
      },
    };
  },

  async listPresets(): Promise<PresetCatalogRead> {
    await delay(120);
    return {
      categories: listPresetCategories(),
      presets: PRESET_ALGORITHMS,
    };
  },

  async getPreset(slug: string): Promise<PresetRead> {
    await delay(80);
    const preset = PRESET_ALGORITHMS.find((entry) => entry.slug === slug);
    if (!preset) {
      throw new Error(`Preset not found: ${slug}`);
    }
    return preset;
  },

  async runCode(payload: {
    code: string;
    input: string;
    backend: ExecutionBackend;
    instrument: boolean;
    timeout_seconds?: number;
    memory_limit_mb?: number;
  }): Promise<PlaygroundRunResponse> {
    await delay(160);
    return buildPreviewRunResponse(payload);
  },

  async runExperiment(payload: {
    code: string;
    input_sizes: number[];
    input_kind: InputKind;
    input_profile: InputProfile;
    repetitions: number;
    backend: ExecutionBackend;
    instrument: boolean;
    timeout_seconds?: number;
    memory_limit_mb?: number;
  }): Promise<PlaygroundExperimentResponse> {
    await delay(240);
    return buildPreviewExperimentResponse(payload);
  },

  async generateExplanation(payload: {
    metrics_snapshot: ExperimentMetricsSnapshot;
    complexity_estimate: ComplexityEstimate | null;
    max_sections?: number;
  }): Promise<ExplanationResponse> {
    await delay(120);
    return buildExplanationResponse(payload.metrics_snapshot, payload.complexity_estimate, payload.max_sections);
  },

  async compareExperiments(payload: {
    left: {
      label: string;
      metrics: ExperimentMetricsSnapshot;
      complexity_estimate?: { estimated_class: string; confidence: number };
    };
    right: {
      label: string;
      metrics: ExperimentMetricsSnapshot;
      complexity_estimate?: { estimated_class: string; confidence: number };
    };
  }): Promise<ComparisonReport> {
    await delay(140);
    return buildComparisonReport(payload);
  },

  async createShare(payload: {
    kind: string;
    label: string;
    data: Record<string, unknown>;
    expires_in_seconds: number;
  }): Promise<SharePayloadRead> {
    await delay(90);
    const token = randomId("preview");
    const createdAt = new Date();
    const expiresAt = new Date(createdAt.getTime() + payload.expires_in_seconds * 1000);

    return {
      token,
      share_path: `/preview/share/${token.slice(-12)}`,
      kind: payload.kind,
      label: payload.label,
      data: payload.data,
      created_at: createdAt.toISOString(),
      expires_at: expiresAt.toISOString(),
      payload_size_bytes: JSON.stringify(payload.data).length,
      signature_version: "preview-v1",
    };
  },
};
