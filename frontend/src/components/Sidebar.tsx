export type ViewId =
  | "cost"
  | "quality"
  | "context"
  | "reliability"
  | "traceability"
  | "dashboard"
  | "chat";

interface NavItem {
  id: ViewId;
  number: string;
  label: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: "cost", number: "01", label: "Cost" },
  { id: "quality", number: "02", label: "Quality Trap" },
  { id: "context", number: "03", label: "Context" },
  { id: "reliability", number: "04", label: "Reliability" },
  { id: "traceability", number: "05", label: "Traceability" },
  { id: "dashboard", number: "06", label: "Dashboard" },
];

interface SidebarProps {
  /** Which view is currently active. */
  activeView: ViewId;
  /** Called with the clicked view's id. */
  onSelectView: (view: ViewId) => void;
}

/**
 * Persistent left navigation — one entry per demo moment, in the order
 * they're presented, plus a free-form chat entry for ad-hoc testing
 * outside the scripted moments.
 *
 * The numbering here is genuinely informative, not decorative — it
 * mirrors the moment order in the demo runbook, so "Moment 3" in the
 * script and "03 Context" in the sidebar are the same thing.
 *
 * @param props - Component props.
 */
export function Sidebar({ activeView, onSelectView }: SidebarProps) {
  return (
    <nav className="sidebar">
      <div className="sidebar-brand">
        <h1>LLM Observability</h1>
        <p>Demo Console</p>
      </div>

      <div className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            className={`sidebar-nav-item ${activeView === item.id ? "active" : ""}`}
            onClick={() => onSelectView(item.id)}
          >
            <span className="sidebar-nav-number">{item.number}</span>
            {item.label}
          </button>
        ))}
      </div>

      <div className="sidebar-nav" style={{ marginTop: 16 }}>
        <button
          className={`sidebar-nav-item ${activeView === "chat" ? "active" : ""}`}
          onClick={() => onSelectView("chat")}
        >
          <span className="sidebar-nav-number">·</span>
          Free-form Chat
        </button>
      </div>

      <div className="sidebar-footer">
        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-dim)" }}>
          docs/testing_sequence.md
        </span>
      </div>
    </nav>
  );
}
