import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

/**
 * Frontend entrypoint — mounts the App component into the DOM.
 */
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
