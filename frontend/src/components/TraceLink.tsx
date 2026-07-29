interface TraceLinkProps {
  traceUrl: string | null;
  label?: string;
}

/**
 * Link out to the observability backend (Langfuse/Phoenix) for a given
 * request's trace. Renders nothing if no trace URL is available.
 *
 * @param props - Component props.
 */
export function TraceLink({ traceUrl, label = "View trace" }: TraceLinkProps) {
  if (!traceUrl) return null;

  return (
    <a className="trace-link" href={traceUrl} target="_blank" rel="noreferrer">
      {label} →
    </a>
  );
}
