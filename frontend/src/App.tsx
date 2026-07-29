import { useState } from "react";
import { Sidebar, type ViewId } from "./components/Sidebar";
import { CostView } from "./views/CostView";
import { QualityTrapView } from "./views/QualityTrapView";
import { ContextView } from "./views/ContextView";
import { ReliabilityView } from "./views/ReliabilityView";
import { TraceabilityView } from "./views/TraceabilityView";
import { DashboardView } from "./views/DashboardView";
import { ChatView } from "./views/ChatView";
import "./App.css";

const VIEWS: Record<ViewId, React.ComponentType> = {
  cost: CostView,
  quality: QualityTrapView,
  context: ContextView,
  reliability: ReliabilityView,
  traceability: TraceabilityView,
  dashboard: DashboardView,
  chat: ChatView,
};

/**
 * Operator console — sidebar navigation with one dedicated view per
 * demo moment, plus a free-form chat view for ad-hoc testing.
 *
 * Each moment view is self-contained: it explains how to run itself,
 * calls the corresponding backend scenario endpoint directly, and
 * displays the result with the specific things to check for. Built
 * this way (rather than one long scrollable page) so the screen only
 * ever shows what's relevant to the moment currently being presented.
 */
function App() {
  const [activeView, setActiveView] = useState<ViewId>("cost");

  const ActiveViewComponent = VIEWS[activeView];

  return (
    <div className="app-shell">
      <Sidebar activeView={activeView} onSelectView={setActiveView} />
      <main className="main-content">
        <ActiveViewComponent />
      </main>
    </div>
  );
}

export default App;
