import { useState } from "react";
import { sendChatMessage } from "../api/client";
import { MetricGrid } from "./ui/MetricGrid";
import { TraceLink } from "./TraceLink";
import type { ChatResponse } from "../types";

interface ChatWindowProps {
  /** Whether to request contextual retrieval instead of plain retrieval (Moment 3). */
  useContextualRetrieval: boolean;
}

/**
 * Free-form question/answer panel. Submits to the backend's /chat/
 * endpoint and displays the answer along with cost, latency, cache-hit
 * status, and any MCP tool calls made while answering.
 *
 * @param props - Component props.
 */
export function ChatWindow({ useContextualRetrieval }: ChatWindowProps) {
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const result = await sendChatMessage({
        question,
        use_contextual_retrieval: useContextualRetrieval,
      });
      setResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit} style={{ display: "flex", gap: 8 }}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question…"
          style={{
            flex: 1,
            padding: "10px 12px",
            background: "var(--bg)",
            border: "1px solid var(--border-bright)",
            borderRadius: 8,
            color: "var(--text-primary)",
            fontFamily: "var(--font-body)",
            fontSize: "0.875rem",
          }}
        />
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Thinking…" : "Ask"}
        </button>
      </form>

      {error && <div className="error-block" style={{ marginTop: 16 }}>{error}</div>}

      {response && (
        <div style={{ marginTop: 20 }}>
          <div className="answer-block">{response.answer}</div>
          <MetricGrid
            metrics={[
              { label: "Model", value: response.model_used },
              { label: "Cost", value: `$${response.cost_usd.toFixed(5)}` },
              { label: "Latency", value: `${response.latency_ms.toFixed(0)}ms` },
              { label: "Cache hit", value: response.cache_hit ? "Yes" : "No" },
            ]}
          />
          {response.tool_calls.length > 0 && (
            <p className="result-note">
              Tool calls: {response.tool_calls.join(" → ")}
            </p>
          )}
          <div style={{ marginTop: 12 }}>
            <TraceLink traceUrl={response.trace_url} />
          </div>
        </div>
      )}
    </div>
  );
}
