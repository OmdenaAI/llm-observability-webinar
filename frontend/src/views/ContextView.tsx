import { useState } from "react";
import { runContextSingleTurn, runStaleContextCase } from "../api/client";
import { Badge } from "../components/ui/Badge";
import { MetricGrid } from "../components/ui/MetricGrid";
import { TraceLink } from "../components/TraceLink";
import type { ContextSingleTurnResponse, StaleContextResponse } from "../types";

interface Turn {
  question: string;
  response: ContextSingleTurnResponse;
}

const DEFAULT_QUESTION = "What is the refund and support policy?";

/**
 * Moment 3 — Context as a Lever.
 *
 * Toggle contextual retrieval off, ask, see the faithfulness score.
 * Toggle it on, ask the same question again, watch the score change —
 * two real, separate turns rather than one button computing a diff.
 * The stale-context failure case runs as its own separate action below.
 */
export function ContextView() {
  const [question, setQuestion] = useState(DEFAULT_QUESTION);
  const [useContextual, setUseContextual] = useState(false);
  const [history, setHistory] = useState<Turn[]>([]);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [staleResult, setStaleResult] = useState<StaleContextResponse | null>(null);
  const [loadingStale, setLoadingStale] = useState(false);

  const handleAsk = async () => {
    if (!question.trim()) return;
    setAsking(true);
    setError(null);
    try {
      const response = await runContextSingleTurn(question, useContextual);
      setHistory((prev) => [...prev, { question, response }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setAsking(false);
    }
  };

  const handleRunStale = async () => {
    setLoadingStale(true);
    setError(null);
    try {
      setStaleResult(await runStaleContextCase(question));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoadingStale(false);
    }
  };

  return (
    <div>
      <header className="view-header">
        <p className="view-eyebrow">Moment 03</p>
        <h2>Context as a Lever</h2>
        <p>Context engineering and contextual retrieval — raising quality without a bigger model.</p>
      </header>

      <div className="panel">
        <p className="panel-title">Retrieval mode</p>
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.85rem", color: "var(--text-secondary)" }}>
          <input
            type="checkbox"
            checked={useContextual}
            onChange={(e) => setUseContextual(e.target.checked)}
          />
          Use contextual retrieval
        </label>
      </div>

      <div className="panel">
        <p className="panel-title">Ask</p>
        <div className="field">
          <label htmlFor="context-question">Question</label>
          <input
            id="context-question"
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
        </div>
        <div className="btn-row">
          <button className="btn btn-primary" onClick={handleAsk} disabled={asking}>
            {asking ? "Asking…" : "Ask"}
          </button>
        </div>
      </div>

      {error && <div className="error-block">{error}</div>}

      {history.length > 0 && (
        <div className="panel">
          <p className="panel-title">History ({history.length})</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {history.map((turn, index) => (
              <div
                key={index}
                style={{
                  paddingBottom: 20,
                  borderBottom:
                    index < history.length - 1 ? "1px solid var(--border)" : "none",
                }}
              >
                <p style={{ fontSize: "0.8rem", color: "var(--text-dim)", marginBottom: 8 }}>
                  &ldquo;{turn.question}&rdquo; · {turn.response.retrieval_mode} retrieval
                </p>
                <div className="answer-block">{turn.response.answer}</div>
                <MetricGrid
                  metrics={[
                    { label: "Relevancy", value: turn.response.relevancy.toFixed(2) },
                    {
                      label: "Faithfulness",
                      value: turn.response.faithfulness.toFixed(2),
                      emphasis:
                        turn.response.retrieval_mode === "contextual" ? "success" : undefined,
                    },
                  ]}
                />
                <div style={{ marginTop: 12 }}>
                  <TraceLink traceUrl={turn.response.trace_url} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="panel">
        <p className="panel-title">Stale-context failure case</p>
        <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: 12 }}>
          Uses the question above, but always retrieves from a
          deliberately outdated document — the eval score looks fine
          even though the answer is wrong.
        </p>
        <div className="btn-row">
          <button className="btn btn-secondary" onClick={handleRunStale} disabled={loadingStale}>
            {loadingStale ? "Running…" : "Run stale-context case"}
          </button>
        </div>
      </div>

      {staleResult && (
        <div className="panel">
          <p className="panel-title">Stale-context result</p>
          <div className="answer-block">{staleResult.answer}</div>
          <MetricGrid
            metrics={[{ label: "Faithfulness", value: staleResult.faithfulness.toFixed(2) }]}
          />
          <p className="result-note">
            {staleResult.passes_eval_but_wrong
              ? "The faithfulness score looks fine — but the answer is grounded in an outdated document, not the current policy."
              : "This case did not reproduce the stale-context pattern."}
          </p>
          <div style={{ marginTop: 16 }}>
            <Badge variant={staleResult.passes_eval_but_wrong ? "warning" : "neutral"}>
              {staleResult.passes_eval_but_wrong ? "Passes eval, likely wrong" : "No issue detected"}
            </Badge>
          </div>
        </div>
      )}
    </div>
  );
}
