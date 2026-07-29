import { useState } from "react";
import { runTraceabilityScenario } from "../api/client";
import { Badge } from "../components/ui/Badge";
import { TraceLink } from "../components/TraceLink";
import type { TraceabilityScenarioResponse } from "../types";

/**
 * Moment 5 — Traceability: an MCP Tool Call, End to End.
 *
 * A single fixed question chains four read-only MCP calls to Umaku.
 * Each call's real status and latency is shown individually — not a
 * placeholder visualization — using the actual per-call data the
 * backend now returns.
 */
export function TraceabilityView() {
  const [result, setResult] = useState<TraceabilityScenarioResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(await runTraceabilityScenario());
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
        <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: 12 }}>
          &ldquo;How is the current sprint going, and how&apos;s the team doing?&rdquo;
        </p>
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
