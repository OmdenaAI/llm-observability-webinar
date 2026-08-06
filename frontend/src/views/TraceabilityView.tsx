import { useState } from "react";
import { runTraceabilityScenario } from "../api/client";
import { Badge } from "../components/ui/Badge";
import { TraceLink } from "../components/TraceLink";
import type { TraceabilityScenarioResponse } from "../types";

const DEFAULT_QUESTION = "How is the current sprint going, and how's the team doing?";

/**
 * Moment 5 — Traceability: an MCP Tool Call, End to End.
 *
 * A fixed-by-default question chains four read-only MCP calls to
 * Umaku. Each call's real status and latency is shown individually —
 * not a placeholder visualization — using the actual per-call data the
 * backend now returns. The question is editable, but tool routing here
 * is a simple keyword match (any of "sprint", "team", "kanban",
 * "board", "performance") rather than an LLM deciding tool use — see
 * tool_router.py — so editing out all of those keywords means no MCP
 * calls fire at all.
 */
export function TraceabilityView() {
  const [question, setQuestion] = useState(DEFAULT_QUESTION);
  const [result, setResult] = useState<TraceabilityScenarioResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(await runTraceabilityScenario(question));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const maxLatency = result
    ? Math.max(...result.tool_calls.map((c) => c.latency_ms), 1)
    : 1;

  return (
    <div>
      <header className="view-header">
        <p className="view-eyebrow">Moment 05</p>
        <h2>Traceability</h2>
        <p>MCP as an observability layer — traceability of context and tool use.</p>
      </header>

      <div className="panel">
        <p className="panel-title">Ask</p>
        <div className="field">
          <label htmlFor="traceability-question">Question</label>
          <input
            id="traceability-question"
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <p style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: 4 }}>
            Include at least one of: sprint, team, kanban, board, performance — otherwise
            no MCP tool calls will be triggered.
          </p>
        </div>
        <div className="btn-row">
          <button className="btn btn-primary" onClick={handleRun} disabled={loading}>
            {loading ? "Asking…" : "Ask"}
          </button>
        </div>
      </div>

      {error && <div className="error-block">{error}</div>}

      {result && (
        <div className="panel">
          <p className="panel-title">Result</p>
          <div className="answer-block">{result.answer}</div>

          <div className="waterfall" style={{ marginBottom: 20 }}>
            {result.tool_calls.map((call) => {
              const isSuccess = call.status === "success";
              return (
                <div className="waterfall-row" key={call.tool_name}>
                  <span className="waterfall-label" title={call.tool_name}>
                    mcp:{call.tool_name}
                  </span>
                  <div className="waterfall-track">
                    <div
                      className={`waterfall-bar ${isSuccess ? "" : "error"}`}
                      style={{ width: `${Math.max((call.latency_ms / maxLatency) * 100, 4)}%` }}
                    />
                  </div>
                  <span className={`waterfall-status ${isSuccess ? "success" : "error"}`}>
                    {isSuccess ? `${call.latency_ms.toFixed(0)}ms` : "failed"}
                  </span>
                </div>
              );
            })}
          </div>

          {result.tool_calls.some((c) => c.status !== "success") && (
            <div className="error-block">
              {result.tool_calls
                .filter((c) => c.status !== "success")
                .map((c) => `${c.tool_name}: ${c.error_message}`)
                .join(" · ")}
            </div>
          )}

          <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 16 }}>
            <Badge variant={result.all_calls_succeeded ? "success" : "error"}>
              {result.tool_call_count} tool calls ·{" "}
              {result.all_calls_succeeded ? "all succeeded" : "some failed"}
            </Badge>
            <TraceLink traceUrl={result.trace_url} />
          </div>
        </div>
      )}
    </div>
  );
}