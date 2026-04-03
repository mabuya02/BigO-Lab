"use client";

import { useEffect, useRef, useState, KeyboardEvent } from "react";
import { Terminal, ChevronRight, AlertCircle, CheckCircle2 } from "lucide-react";
import clsx from "clsx";
import type { CodeExecutionResult, PresetRead } from "@/lib/types";
import type { ExecutionBackend } from "@/lib/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type LineKind = "command" | "stdout" | "stderr" | "info" | "error" | "success" | "divider";

interface HistoryLine {
  id: number;
  kind: LineKind;
  text: string;
  runtimeMs?: number;
}

interface TerminalConsoleProps {
  code: string;
  backend: ExecutionBackend;
  instrument: boolean;
  timeoutSeconds: number;
  memoryLimitMb: number;
  latestExecution: CodeExecutionResult | null;
  selectedPreset: PresetRead | null;
  isPending: boolean;
  onRun: (stdin: string) => void;
  onStdinChange: (value: string) => void;
  currentStdin: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

let lineId = 0;
const mkLine = (kind: LineKind, text: string, runtimeMs?: number): HistoryLine => ({
  id: ++lineId,
  kind,
  text,
  runtimeMs,
});

const PROMPT = ">>> ";

const HELP_TEXT = `Big O Playground — Interactive Python Shell
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Commands:
  <input>        Pass input to your code and run it
  run            Run current code with no stdin
  clear          Clear terminal history
  help           Show this help

Keyboard shortcuts:
  Enter          Execute command
  ↑ / ↓         Navigate command history
  Ctrl+L         Clear terminal

The code in the editor is always used. Type your stdin value and press Enter.`;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function TerminalConsole({
  code,
  backend,
  instrument,
  timeoutSeconds,
  memoryLimitMb,
  latestExecution,
  selectedPreset,
  isPending,
  onRun,
  onStdinChange,
  currentStdin,
}: TerminalConsoleProps) {
  const [history, setHistory] = useState<HistoryLine[]>([
    mkLine("info", `Big O Playground — Python 3.11 runtime`),
    mkLine("info", `Type your stdin value and press Enter, or type 'help' for commands.`),
    mkLine("divider", ""),
  ]);
  const [input, setInput] = useState("");
  const [cmdHistory, setCmdHistory] = useState<string[]>([]);
  const [cmdHistoryIdx, setCmdHistoryIdx] = useState(-1);
  const [savedInput, setSavedInput] = useState("");

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const prevExecutionRef = useRef<CodeExecutionResult | null>(null);

  // Auto-scroll on new lines
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [history]);

  // Append execution result when it changes
  useEffect(() => {
    if (!latestExecution || latestExecution === prevExecutionRef.current) return;
    prevExecutionRef.current = latestExecution;

    const lines: HistoryLine[] = [];

    if (latestExecution.stdout) {
      for (const line of latestExecution.stdout.split("\n")) {
        lines.push(mkLine("stdout", line));
      }
    } else {
      lines.push(mkLine("info", "(no output)"));
    }

    if (latestExecution.stderr) {
      lines.push(mkLine("divider", ""));
      for (const line of latestExecution.stderr.split("\n")) {
        if (line.trim()) lines.push(mkLine("stderr", line));
      }
    }

    const status =
      latestExecution.timed_out
        ? mkLine("error", `Execution timed out after ${timeoutSeconds}s`)
        : latestExecution.status === "completed"
        ? mkLine("success", `Exited 0  ·  ${latestExecution.runtime_ms}ms wall-clock`, latestExecution.runtime_ms)
        : mkLine("error", `Exited ${latestExecution.exit_code ?? 1}  ·  process failed`);

    lines.push(status);
    lines.push(mkLine("divider", ""));

    setHistory((prev) => [...prev, ...lines]);
  }, [latestExecution, timeoutSeconds]);

  const pushCommand = (cmd: string) => {
    setHistory((prev) => [...prev, mkLine("command", PROMPT + cmd)]);
  };

  const execute = (raw: string) => {
    const cmd = raw.trim();
    if (!cmd) {
      // empty enter — just run with no stdin
      pushCommand("");
      onStdinChange("");
      onRun("");
      return;
    }

    pushCommand(cmd);
    setCmdHistory((prev) => [cmd, ...prev.filter((c) => c !== cmd)]);
    setCmdHistoryIdx(-1);
    setSavedInput("");

    if (cmd === "clear" || cmd === "cls") {
      setHistory([mkLine("info", "Terminal cleared."), mkLine("divider", "")]);
      return;
    }

    if (cmd === "help") {
      const helpLines = HELP_TEXT.split("\n").map((l) => mkLine("info", l));
      setHistory((prev) => [...prev, ...helpLines, mkLine("divider", "")]);
      return;
    }

    if (cmd === "run") {
      onStdinChange("");
      onRun("");
      return;
    }

    // Anything else is treated as stdin passed to the current code
    onStdinChange(cmd);
    onRun(cmd);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      execute(input);
      setInput("");
      return;
    }

    if (e.key === "l" && e.ctrlKey) {
      e.preventDefault();
      setHistory([mkLine("info", "Terminal cleared."), mkLine("divider", "")]);
      return;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (cmdHistory.length === 0) return;
      const nextIdx = cmdHistoryIdx + 1;
      if (nextIdx === 0) setSavedInput(input);
      if (nextIdx < cmdHistory.length) {
        setCmdHistoryIdx(nextIdx);
        setInput(cmdHistory[nextIdx]);
      }
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (cmdHistoryIdx <= 0) {
        setCmdHistoryIdx(-1);
        setInput(savedInput);
        return;
      }
      const nextIdx = cmdHistoryIdx - 1;
      setCmdHistoryIdx(nextIdx);
      setInput(cmdHistory[nextIdx]);
      return;
    }
  };

  // Click anywhere in the terminal buffer to focus the input
  const focusInput = () => inputRef.current?.focus();

  return (
    <div
      className="flex flex-col h-full bg-[#0c0c0c] rounded-xl border border-white/10 overflow-hidden shadow-2xl ring-1 ring-white/5"
      onClick={focusInput}
    >
      {/* Title bar */}
      <div className="flex h-10 shrink-0 items-center justify-between px-4 border-b border-white/5 bg-[#161616]">
        <div className="flex items-center gap-2.5">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/70" />
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/70" />
            <div className="w-2.5 h-2.5 rounded-full bg-green-500/70" />
          </div>
          <Terminal size={12} className="text-green-500 ml-1" />
          <span className="text-[10px] font-mono font-semibold tracking-widest text-gray-500 uppercase">
            python3 — big-o-sandbox
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isPending && (
            <span className="flex items-center gap-1.5 text-[9px] font-mono text-yellow-400 uppercase tracking-widest animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-yellow-400" />
              running
            </span>
          )}
          {!isPending && latestExecution && (
            latestExecution.status === "completed" && !latestExecution.timed_out ? (
              <CheckCircle2 size={12} className="text-green-500" />
            ) : (
              <AlertCircle size={12} className="text-red-500" />
            )
          )}
          <span className="text-[9px] font-mono text-gray-600 border border-white/5 px-1.5 py-0.5 rounded bg-white/[0.02]">
            {backend === "auto" ? "local" : backend}
          </span>
        </div>
      </div>

      {/* Scrollback buffer */}
      <div className="flex-1 overflow-y-auto px-4 py-3 font-mono text-sm custom-scrollbar selection:bg-green-500/20">
        {history.map((line) => (
          <div key={line.id} className={clsx("leading-relaxed", line.kind === "divider" && "my-1")}>
            {line.kind === "divider" ? (
              <div className="border-t border-white/[0.04]" />
            ) : line.kind === "command" ? (
              <span className="text-green-400">{line.text}</span>
            ) : line.kind === "stdout" ? (
              <span className="text-gray-200">{line.text || "\u00A0"}</span>
            ) : line.kind === "stderr" ? (
              <span className="text-red-400/90">{line.text}</span>
            ) : line.kind === "success" ? (
              <span className="text-emerald-500/80 text-xs">{line.text}</span>
            ) : line.kind === "error" ? (
              <span className="text-red-500/90 text-xs">{line.text}</span>
            ) : (
              // info
              <span className="text-gray-600 text-xs">{line.text}</span>
            )}
          </div>
        ))}
        <div ref={scrollRef} />
      </div>

      {/* Input line */}
      <div className="shrink-0 border-t border-white/5 bg-[#111111] px-4 py-2.5 flex items-center gap-2">
        <ChevronRight size={13} className={clsx("shrink-0 transition-colors", isPending ? "text-yellow-400 animate-pulse" : "text-green-500")} />
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isPending}
          autoFocus
          spellCheck={false}
          autoComplete="off"
          className="flex-1 bg-transparent text-sm text-gray-200 outline-none border-none font-mono placeholder:text-gray-700 disabled:opacity-40"
          placeholder={isPending ? "running…" : "enter stdin or command (help, clear, run)"}
        />
      </div>
    </div>
  );
}
