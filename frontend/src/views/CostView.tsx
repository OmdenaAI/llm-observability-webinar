import { useState } from "react";
import { sendChatMessage, toggleCache, toggleRouting } from "../api/client";
import { Badge } from "../components/ui/Badge";
import { MetricGrid } from "../components/ui/MetricGrid";
import { TraceLink } from "../components/TraceLink";
import type { ChatResponse } from "../types";

interface Turn {
  question: string;
  response: ChatResponse;
}

const DEFAULT_QUESTION = "What is your refund policy?";

/**
 * Moment 1 — Cost Optimization.
 *
 * A live, interactive flow rather than a single button that runs a
 * before/after diff internally: ask a question with caching off, see
 * a real cost; flip caching on; ask the SAME question again; see the
 * cost drop to $0 and the cache-hit flag flip to true. Both turns stay
 * visible in a running history so the change is something the audience
 * watches happen, not something they're told happened.
 */
export function CostView() {
  const [question, setQuestion] = useState(DEFAULT_QUESTION);
  const [cacheEnabled, setCacheEnabled] = useState(false);
  const [routingEnabled, setRoutingEnabled] = useState(false);
  const [history, setHistory] = useState<Turn[]>([]);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleToggleCache = async () => {
    const next = !cacheEnabled;
    try {
      await toggleCache(next);
      setCacheEnabled(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to toggle cache");
    }
  };

  const handleToggleRouting = async () => {
    const next = !routingEnabled;
    try {
      await toggleRouting(next);
      setRoutingEnabled(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to toggle routing");
    }
  };

  const handleAsk = async () => {
    if (!question.trim()) return;
    setAsking(true);
    setError(null);
    try {
      const response = await sendChatMessage({
        question,
        use_contextual_retrieval: false,
      });
      setHistory((prev) => [...prev, { question, response }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setAsking(false);
    }
  };

  return (
    <div>
      <header className="view-header">
        <p className="view-eyebrow">Moment 01</p>
        <h2>Cost Optimization</h2>
        <p>Token monitoring, caching, and model routing at the gateway level.</p>
      </header>

      <div className="panel">
        <p className="panel-title">Gateway controls</p>
        <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            <input type="checkbox" checked={cacheEnabled} onChange={handleToggleCache} />
            Caching
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            <input type="checkbox" checked={routingEnabled} onChange={handleToggleRouting} />
            Model routing
          </label>
        </div>
      </div>

      <div className="panel">
        <p className="panel-title">Ask</p>
        <div className="field">
          <label htmlFor="cost-question">Question</label>
          <input
            id="cost-question"
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
                  &ldquo;{turn.question}&rdquo;
                </p>
                <div className="answer-block">{turn.response.answer}</div>
                <MetricGrid
                  metrics={[
                    { label: "Model", value: turn.response.model_used },
                    {
                      label: "Cost",
                      value: `$${turn.response.cost_usd.toFixed(5)}`,
                      emphasis: turn.response.cost_usd === 0 ? "success" : undefined,
                    },
                    { label: "Latency", value: `${turn.response.latency_ms.toFixed(0)}ms` },
                  ]}
                />
                <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 16 }}>
                  <Badge variant={turn.response.cache_hit ? "success" : "neutral"}>
                    {turn.response.cache_hit ? "Cache hit" : "Cache miss"}
                  </Badge>
                  <TraceLink traceUrl={turn.response.trace_url} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
