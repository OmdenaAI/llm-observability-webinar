import { useState } from "react";
import { runReliabilityScenario } from "../api/client";
import { Badge } from "../components/ui/Badge";
import type { ReliabilityScenarioResponse } from "../types";

const DEFAULT_QUESTION = "What happens during a provider outage?";

/**
 * Moment 4 — Reliability: Live Provider Outage.
 *
 * The provider kill itself is a terminal command (`make kill-provider`)
 * run outside this app — this view only runs the question afterward
 * and reports whether the gateway's fallback chain caught the failure.
 */
export function ReliabilityView() {
  const [question, setQuestion] = useState(DEFAULT_QUESTION);
  const [result, setResult] = useState<ReliabilityScenarioResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(await runReliabilityScenario(question));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <header className="view-header">
        <p className="view-eyebrow">Moment 04</p>
        <h2>Reliability</h2>
        <p>Fallbacks, rate limits, and error handling — graceful degradation under a live outage.</p>
      </header>

      <div className="panel">
        <p className="panel-title">Ask</p>
        <div className="field">
          <label htmlFor="reliability-question">Question</label>
          <input
            id="reliability-question"
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
        </div>
        <div className="btn-row">
          <button className="btn btn-danger" onClick={handleRun} disabled={loading}>
            {loading ? "Asking…" : "Ask"}
          </button>
        </div>
      </div>

      {error && <div className="error-block">{error}</div>}

      {result && (
        <div className="panel">
          <p className="panel-title">Result</p>
          <div className="answer-block">{result.answer}</div>
          <p className="result-note">
            {result.failed_over
              ? "The primary provider was unreachable — the gateway's configured fallback chain caught it automatically, and the user never saw a disruption."
              : "No failover was detected on this request."}
          </p>
          <div style={{ marginTop: 16 }}>
            <Badge variant={result.failed_over ? "success" : "error"}>
              {result.failed_over ? "Failover confirmed" : "No failover detected"}
            </Badge>
          </div>
        </div>
      )}
    </div>
  );
}