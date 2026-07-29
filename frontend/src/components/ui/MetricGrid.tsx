interface Metric {
  /** Short label shown above the value (e.g. "Cost", "Latency"). */
  label: string;
  /** The value to display — pre-formatted as a string by the caller. */
  value: string;
  /** Optional color emphasis for the value. */
  emphasis?: "accent" | "success" | "error";
}

interface MetricGridProps {
  /** The metrics to display, in order. */
  metrics: Metric[];
}

/**
 * A responsive grid of labeled metric values — cost, latency, scores,
 * counts, etc. Used across every moment view for consistent, scannable
 * data display.
 *
 * @param props - Component props.
 */
export function MetricGrid({ metrics }: MetricGridProps) {
  return (
    <div className="metric-grid">
      {metrics.map((metric) => (
        <div className="metric" key={metric.label}>
          <span className="metric-label">{metric.label}</span>
          <span className={`metric-value ${metric.emphasis ?? ""}`}>
            {metric.value}
          </span>
        </div>
      ))}
    </div>
  );
}
