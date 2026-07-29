import { useState } from "react";
import { ChatWindow } from "../components/ChatWindow";
import { ToggleControls } from "../components/ToggleControls";

/**
 * Free-form chat — not one of the six scripted moments, but useful for
 * ad-hoc testing outside the fixed scenario questions (e.g. probing the
 * corpus with your own questions, or manually toggling gateway state).
 */
export function ChatView() {
  const [useContextualRetrieval, setUseContextualRetrieval] = useState(false);

  return (
    <div>
      <header className="view-header">
        <p className="view-eyebrow">Free-form</p>
        <h2>Chat</h2>
        <p>
          Ask anything directly — useful for probing the corpus or MCP
          tools outside the six fixed demo scenarios.
        </p>
      </header>

      <div className="panel">
        <p className="panel-title">Gateway controls</p>
        <ToggleControls
          useContextualRetrieval={useContextualRetrieval}
          onContextualRetrievalChange={setUseContextualRetrieval}
        />
      </div>

      <div className="panel">
        <p className="panel-title">Conversation</p>
        <ChatWindow useContextualRetrieval={useContextualRetrieval} />
      </div>
    </div>
  );
}
