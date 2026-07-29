import { useState } from "react";
import { toggleCache, toggleRouting } from "../api/client";

interface ToggleControlsProps {
  useContextualRetrieval: boolean;
  onContextualRetrievalChange: (enabled: boolean) => void;
}

/**
 * Manual gateway toggles for the free-form chat view — cache/routing
 * (normally handled automatically by the Cost scenario) and contextual
 * retrieval (normally handled by the Context scenario).
 *
 * @param props - Component props.
 */
export function ToggleControls({
  useContextualRetrieval,
  onContextualRetrievalChange,
}: ToggleControlsProps) {
  const [cacheEnabled, setCacheEnabled] = useState(false);
  const [routingEnabled, setRoutingEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCacheToggle = async () => {
    const next = !cacheEnabled;
    try {
      await toggleCache(next);
      setCacheEnabled(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to toggle cache");
    }
  };

  const handleRoutingToggle = async () => {
    const next = !routingEnabled;
    try {
      await toggleRouting(next);
      setRoutingEnabled(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to toggle routing");
    }
  };

  return (
    <div>
      <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.85rem", color: "var(--text-secondary)" }}>
          <input type="checkbox" checked={cacheEnabled} onChange={handleCacheToggle} />
          Gateway caching
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.85rem", color: "var(--text-secondary)" }}>
          <input type="checkbox" checked={routingEnabled} onChange={handleRoutingToggle} />
          Model routing
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.85rem", color: "var(--text-secondary)" }}>
          <input
            type="checkbox"
            checked={useContextualRetrieval}
            onChange={(e) => onContextualRetrievalChange(e.target.checked)}
          />
          Contextual retrieval
        </label>
      </div>
      {error && <div className="error-block" style={{ marginTop: 12 }}>{error}</div>}
    </div>
  );
}
