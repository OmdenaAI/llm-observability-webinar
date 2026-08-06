import type {
  ChatRequest,
  ChatResponse,
  ContextComparisonResponse,
  ContextSingleTurnResponse,
  CostScenarioResponse,
  GatewayStatus,
  QualityTrapResponse,
  ReliabilityScenarioResponse,
  StaleContextResponse,
  TraceabilityScenarioResponse,
} from "../types";

// In dev (`npm run dev`), "/api" is proxied to the backend by Vite (see
// vite.config.ts) — no env var needed. The production Docker build has
// no such proxy (it's a static file server), so frontend/Dockerfile
// bakes in VITE_API_BASE_URL as a build-time constant pointing directly
// at the backend's host-mapped port.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

/**
 * Send a question to the backend's /chat/ endpoint and return the answer.
 */
export async function sendChatMessage(
  payload: ChatRequest,
): Promise<ChatResponse> {
  const res = await fetch(`${BASE_URL}/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Chat request failed: ${res.status}`);
  return res.json();
}

/** Enable or disable the gateway's response cache. */
export async function toggleCache(
  enabled: boolean,
): Promise<{ cache_enabled: boolean }> {
  const res = await fetch(`${BASE_URL}/admin/gateway/cache`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) throw new Error(`Toggle cache failed: ${res.status}`);
  return res.json();
}

/** Enable or disable the gateway's model-routing rules. */
export async function toggleRouting(
  enabled: boolean,
): Promise<{ routing_enabled: boolean }> {
  const res = await fetch(`${BASE_URL}/admin/gateway/routing`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) throw new Error(`Toggle routing failed: ${res.status}`);
  return res.json();
}

/** Fetch the gateway's current cache/routing/failover status. */
export async function getGatewayStatus(): Promise<GatewayStatus> {
  const res = await fetch(`${BASE_URL}/admin/gateway/status`);
  if (!res.ok) throw new Error(`Gateway status failed: ${res.status}`);
  return res.json();
}

/** Moment 1 — Cost Optimization. Self-contained: toggles cache/routing itself. */
export async function runCostScenario(
  question: string,
): Promise<CostScenarioResponse> {
  const params = new URLSearchParams({ question });
  const res = await fetch(`${BASE_URL}/scenarios/cost?${params}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Cost scenario failed: ${res.status}`);
  return res.json();
}

/** Moment 2 — Quality Trap. */
export async function runQualityTrapScenario(
  trapQuestion: string,
): Promise<QualityTrapResponse> {
  const params = new URLSearchParams({ trap_question: trapQuestion });
  const res = await fetch(`${BASE_URL}/scenarios/quality-trap?${params}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Quality trap scenario failed: ${res.status}`);
  return res.json();
}

/** Moment 3, part 1 — plain vs. contextual retrieval comparison (bundled). */
export async function runContextComparison(
  question: string,
): Promise<ContextComparisonResponse> {
  const params = new URLSearchParams({ question });
  const res = await fetch(
    `${BASE_URL}/scenarios/context-comparison?${params}`,
    { method: "POST" },
  );
  if (!res.ok) throw new Error(`Context comparison failed: ${res.status}`);
  return res.json();
}

/**
 * Moment 3 — one interactive turn under one retrieval mode. Used for
 * the ask-toggle-ask flow: call this once with contextual retrieval
 * off, once with it on, as two separate real turns.
 */
export async function runContextSingleTurn(
  question: string,
  useContextualRetrieval: boolean,
): Promise<ContextSingleTurnResponse> {
  const params = new URLSearchParams({
    question,
    use_contextual_retrieval: String(useContextualRetrieval),
  });
  const res = await fetch(`${BASE_URL}/scenarios/context-single?${params}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Context single-turn failed: ${res.status}`);
  return res.json();
}

/** Moment 3, part 2 — the stale-context failure case. */
export async function runStaleContextCase(
  staleQuestion: string,
): Promise<StaleContextResponse> {
  const params = new URLSearchParams({ stale_question: staleQuestion });
  const res = await fetch(`${BASE_URL}/scenarios/stale-context?${params}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Stale context scenario failed: ${res.status}`);
  return res.json();
}

/**
 * Moment 4 — Reliability. Call this AFTER the provider has been killed
 * (`make kill-provider` / the Reliability view's kill button, if wired
 * to a backend action — see that view for the current manual step).
 */
export async function runReliabilityScenario(
  question: string,
): Promise<ReliabilityScenarioResponse> {
  const res = await fetch(`${BASE_URL}/scenarios/reliability`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(`Reliability scenario failed: ${res.status}`);
  return res.json();
}

/** Moment 5 — Traceability. Fixed sprint-status question, no params needed. */
export async function runTraceabilityScenario(
  question: string,
): Promise<TraceabilityScenarioResponse> {
  const params = new URLSearchParams({ question });
  const res = await fetch(`${BASE_URL}/scenarios/traceability?${params}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Traceability scenario failed: ${res.status}`);
  return res.json();
}