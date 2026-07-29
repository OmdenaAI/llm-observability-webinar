/**
 * Moment 6 — Unified Dashboard.
 *
 * No API call — pure observation. Opens Langfuse/Phoenix directly,
 * where cost, quality, reliability, and traceability signals from
 * Moments 1-5 all show up tied to their originating requests.
 */
export function DashboardView() {
  return (
    <div>
      <header className="view-header">
        <p className="view-eyebrow">Moment 06</p>
        <h2>Unified Dashboard</h2>
        <p>Cost, quality, reliability, and traceability — one dashboard per project.</p>
      </header>

      <div className="panel">
        <p className="panel-title">Observability backends</p>
        <div className="btn-row">
          <a
            className="btn btn-primary"
            href="https://cloud.langfuse.com"
            target="_blank"
            rel="noreferrer"
          >
            Open Langfuse ↗
          </a>
          <a
            className="btn btn-secondary"
            href="http://localhost:6006"
            target="_blank"
            rel="noreferrer"
          >
            Open Phoenix ↗
          </a>
        </div>
      </div>
    </div>
  );
}
