import { useState } from "react";
import { runQualityTrapScenario } from "../api/client";
import { Badge } from "../components/ui/Badge";
import { MetricGrid } from "../components/ui/MetricGrid";
import type { QualityTrapResponse } from "../types";

const DEFAULT_QUESTION =
  "If I delete my account, is a snapshot of my data kept anywhere, and for how long?";

/**
 * Moment 2 — Quality Trap: High Relevancy, Low Faithfulness.
 *
 * A failure mode that passes a shallow glance: the answer sounds
 * on-topic, but isn't actually grounded in the retrieved context.
 */
export function QualityTrapView() {
  const [question, setQuestion] = useState(DEFAULT_QUESTION);
  const [result, setResult] = useState<QualityTrapResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(await runQualityTrapScenario(question));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <header className="view-header">
        <p className="view-eyebrow">Moment 02</p>
        <h2>Quality Trap</h2>
        <p>Evals and drift detection — faithfulness, hallucination rate, answer relevance.</p>
      </header>

      <div className="panel">
        <p className="panel-title">Ask</p>
        <div className="field">
          <label htmlFor="trap-question">Question</label>
          <input
            id="trap-question"
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
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
          <MetricGrid
            metrics={[
              {
                label: "Relevancy",
                value: result.relevancy.toFixed(2),
                emphasis: result.relevancy >= 0.7 ? "accent" : undefined,
              },
              {
                label: "Faithfulness",
                value: result.faithfulness.toFixed(2),
                emphasis: result.faithfulness < 0.5 ? "error" : "success",
              },
            ]}
          />
          <p className="result-note">
            {result.is_quality_trap
              ? "This answer is on-topic (high relevancy) but not grounded in what was actually retrieved (low faithfulness) — the exact failure mode that passes a shallow check."
              : "This answer is both on-topic and grounded in the retrieved context."}
          </p>
          <div style={{ marginTop: 16 }}>
            <Badge variant={result.is_quality_trap ? "warning" : "success"}>
              {result.is_quality_trap ? "Quality trap detected" : "Grounded answer"}
            </Badge>
          </div>
        </div>
      )}
    </div>
  );
}