/**
 * Request payload for POST /chat/ — mirrors backend ChatRequest.
 */
export interface ChatRequest {
  question: string;
  use_contextual_retrieval: boolean;
}

/**
 * Response body from POST /chat/ — mirrors backend ChatResponse.
 */
export interface ChatResponse {
  answer: string;
  model_used: string;
  cost_usd: number;
  latency_ms: number;
  cache_hit: boolean;
  tool_calls: string[];
  trace_url: string | null;
}

/**
 * Current gateway cache/routing state.
 */
export interface GatewayStatus {
  cache_enabled: boolean;
  routing_enabled: boolean;
  [key: string]: unknown;
}

/** Moment 1 — Cost Optimization */
export interface CostScenarioResponse {
  before_cost_usd: number;
  after_cost_usd: number;
  cost_delta_usd: number;
  before_cache_hit: boolean;
  after_cache_hit: boolean;
}

/** Moment 2 — Quality Trap */
export interface QualityTrapResponse {
  answer: string;
  relevancy: number;
  faithfulness: number;
  is_quality_trap: boolean;
}

/** Moment 3, part 1 — Context Comparison */
export interface ContextComparisonResponse {
  plain_faithfulness: number;
  contextual_faithfulness: number;
  faithfulness_delta: number;
}

/** Moment 3 — single interactive turn (ask-toggle-ask flow) */
export interface ContextSingleTurnResponse {
  answer: string;
  relevancy: number;
  faithfulness: number;
  retrieval_mode: string;
  trace_url: string | null;
}

/** Moment 3, part 2 — Stale Context */
export interface StaleContextResponse {
  answer: string;
  faithfulness: number;
  passes_eval_but_wrong: boolean;
}

/** Moment 4 — Reliability */
export interface ReliabilityScenarioResponse {
  answer: string;
  failed_over: boolean;
}

/** One individual MCP tool call's outcome. */
export interface ToolCallDetail {
  tool_name: string;
  status: string;
  latency_ms: number;
  error_message: string | null;
}

/** Moment 5 — Traceability */
export interface TraceabilityScenarioResponse {
  answer: string;
  tool_call_count: number;
  all_calls_succeeded: boolean;
  tool_calls: ToolCallDetail[];
  trace_url: string | null;
}
