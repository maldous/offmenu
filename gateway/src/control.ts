// Control plane for Morgan's Freebuff Gateway: execution-mode lease with
// fencing generations, three-slot session capacity, model/quota/budget policy,
// and a capability matrix grounded in the installed Freebuff build.
//
// This module is pure logic (no IO) so every policy is unit-testable. The
// gateway performs validated routing, lifecycle operations, capacity
// enforcement and ledger follow-through. Morgan owns management, priorities,
// task acceptance and model-selection policy; nothing here becomes a competing
// manager.
export class ControlError extends Error {
  constructor(public code: string) { super(code); }
}

// ---------------------------------------------------------------------------
// 1. Execution-mode lease (non-negotiable execution policy)
// ---------------------------------------------------------------------------

export type ExecutionMode = 'DIRECT_CODEX' | 'FREEBUFF';
export type ModePhase = 'stable' | 'switching' | 'blocked';
export type ExecutionObservation = 'idle' | 'active' | 'unknown';

export interface ModeLease {
  mode: ExecutionMode;
  phase: ModePhase;
  generation: number;          // fencing generation: increments on each transition
  holder: string | null;       // single owner of the mode lease
  leaseExpiresAt: number;
  pendingTarget: ExecutionMode | null;
  dispatchEnabled: boolean;
  blockedReason: string | null;
}

export interface SwitchOutcome {
  state: ModeLease;
  steps: string[];             // ordered steps the caller must complete
}

export function bootstrapModeLease(now: number): ModeLease {
  // The current operating reality is Freebuff-managed execution (this
  // implementation session is Freebuff-native). The mode is explicit and
  // durable from the first write; switching always goes through begin/complete.
  return {
    mode: 'FREEBUFF',
    phase: 'stable',
    generation: 1,
    holder: null,
    leaseExpiresAt: now,
    pendingTarget: null,
    dispatchEnabled: true,
    blockedReason: null,
  };
}

export function acquireModeLease(state: ModeLease, holder: string, now: number, ttlMs: number): ModeLease {
  if (!holder) throw new ControlError('MODE_HOLDER_REQUIRED');
  if (state.holder !== null && state.holder !== holder && state.leaseExpiresAt > now) {
    // A live single-owner lease exists. A stale or expired lease is NOT proof
    // that old work stopped; it only permits takeover of the lease record.
    throw new ControlError('MODE_LEASE_HELD');
  }
  return { ...state, holder, leaseExpiresAt: now + ttlMs, generation: state.generation + 1, blockedReason: null };
}

export function beginModeSwitch(
  state: ModeLease, target: ExecutionMode, holder: string, generation: number, now: number,
  observedExecution: ExecutionObservation, inFlight: number, ttlMs: number,
): SwitchOutcome {
  if (state.generation !== generation) throw new ControlError('MODE_FENCE_CONFLICT');
  if (state.phase === 'switching') throw new ControlError('MODE_SWITCH_IN_PROGRESS');
  if (state.holder !== holder) throw new ControlError('MODE_LEASE_REQUIRED');
  if (state.leaseExpiresAt <= now) throw new ControlError('MODE_LEASE_STALE');
  if (target !== 'DIRECT_CODEX' && target !== 'FREEBUFF') throw new ControlError('MODE_TARGET_INVALID');
  if (target === state.mode) throw new ControlError('MODE_ALREADY_ACTIVE');
  // Unknown execution state blocks the switch. A timeout, stale lease or
  // disconnected computer is not proof that old work stopped.
  if (observedExecution === 'unknown') throw new ControlError('MODE_UNKNOWN_EXECUTION');
  return {
    state: {
      ...state,
      phase: 'switching',
      pendingTarget: target,
      dispatchEnabled: false,          // step 1: stop new dispatch
      generation: state.generation + 1, // fence out stale writers immediately
      leaseExpiresAt: now + ttlMs,
      blockedReason: null,
    },
    steps: [
      'NEW_DISPATCH_STOPPED',
      'RECONCILE_IN_FLIGHT_REQUESTS',
      inFlight > 0 ? 'CHECKPOINT_OR_DRAIN_IN_FLIGHT' : 'NO_IN_FLIGHT_WORK',
      'VERIFY_ACTUAL_INACTIVITY',
      'COMPLETE_SWITCH',
    ],
  };
}

export function completeModeSwitch(
  state: ModeLease, holder: string, generation: number, now: number,
  observedExecution: ExecutionObservation, inFlight: number, ttlMs: number,
): ModeLease {
  if (state.generation !== generation) throw new ControlError('MODE_FENCE_CONFLICT');
  if (state.phase !== 'switching' || state.pendingTarget === null) throw new ControlError('MODE_NOT_SWITCHING');
  if (state.holder !== holder) throw new ControlError('MODE_LEASE_REQUIRED');
  if (inFlight > 0) throw new ControlError('MODE_DRAIN_INCOMPLETE');
  // Completion requires verified inactivity, not elapsed time.
  if (observedExecution !== 'idle') throw new ControlError('MODE_EXECUTION_NOT_VERIFIED');
  return {
    ...state,
    mode: state.pendingTarget,
    phase: 'stable',
    pendingTarget: null,
    dispatchEnabled: true,
    generation: state.generation + 1,
    leaseExpiresAt: now + ttlMs,
    blockedReason: null,
  };
}

export function abortModeSwitch(state: ModeLease, holder: string, generation: number, reason: string): ModeLease {
  if (state.generation !== generation) throw new ControlError('MODE_FENCE_CONFLICT');
  if (state.phase !== 'switching') throw new ControlError('MODE_NOT_SWITCHING');
  if (state.holder !== holder) throw new ControlError('MODE_LEASE_REQUIRED');
  if (!/^[A-Z0-9_:.-]{1,128}$/.test(reason)) throw new ControlError('MODE_REASON_INVALID');
  // Blocked: retain the concrete owner, reason and next permitted action.
  return {
    ...state, phase: 'blocked', pendingTarget: null, dispatchEnabled: false,
    generation: state.generation + 1, blockedReason: reason,
  };
}

export function assertDispatchAllowed(state: ModeLease, now: number): void {
  if (state.phase === 'switching') throw new ControlError('DISPATCH_DRAINING');
  if (state.phase === 'blocked') throw new ControlError('DISPATCH_BLOCKED');
  if (state.mode !== 'FREEBUFF') throw new ControlError('DISPATCH_HALTED_NOT_FREEBUFF_ROUTE');
  if (!state.dispatchEnabled) throw new ControlError('DISPATCH_DISABLED');
  if (state.leaseExpiresAt <= now) throw new ControlError('MODE_LEASE_STALE');
}

// ---------------------------------------------------------------------------
// 2. Three-session capacity (Freebuff's platform limit)
// ---------------------------------------------------------------------------

export type SessionSource = 'discovered' | 'adopted' | 'gateway_created' | 'manual_observed';
export type SessionExecState = 'active' | 'starting' | 'uncertain' | 'idle' | 'stopped';

export interface SessionRecord {
  sessionId: string;
  source: SessionSource;
  projectPath: string;
  account: string;
  provider: string;            // exact mapping: 'freebuff-native' | 'openrouter' | 'codex' | ...
  state: SessionExecState;
  slotHeld: boolean;
  observedAt: number;
  updatedAt: number;
}

export interface ReleaseEvidence {
  type: 'platform_inventory' | 'verified_stop';
  detail: string;
  observedAt: number;
}

export const MAX_SESSION_SLOTS = 3;

// Starting sessions and uncertain creations count against capacity
// conservatively. A slot is never freed merely because a request timed out.
export function slotHolders(registry: SessionRecord[]): SessionRecord[] {
  return registry.filter(r => r.slotHeld && (r.state === 'active' || r.state === 'starting' || r.state === 'uncertain'));
}

export function admitSession(registry: SessionRecord[], target: Omit<SessionRecord, 'slotHeld' | 'updatedAt'>, now: number): SessionRecord[] {
  const existing = registry.find(r => r.sessionId === target.sessionId);
  if (existing) {
    if (existing.state === 'stopped') throw new ControlError('SESSION_REQUIRES_ADOPT_AFTER_STOP');
    return registry.map(r => r.sessionId === target.sessionId ? { ...r, ...target, slotHeld: true, updatedAt: now } : r);
  }
  if (slotHolders(registry).length >= MAX_SESSION_SLOTS) throw new ControlError('CAPACITY_EXCEEDED');
  return [...registry, { ...target, slotHeld: true, updatedAt: now }];
}

export function releaseSlot(registry: SessionRecord[], sessionId: string, evidence: ReleaseEvidence, now: number): SessionRecord[] {
  const target = registry.find(r => r.sessionId === sessionId);
  if (!target) throw new ControlError('SESSION_UNKNOWN');
  if (!target.slotHeld) return registry;
  if (!evidence || (evidence.type !== 'platform_inventory' && evidence.type !== 'verified_stop')) {
    throw new ControlError('CAPACITY_RELEASE_UNVERIFIED');
  }
  if (!evidence.detail || evidence.observedAt > now + 5000) throw new ControlError('CAPACITY_RELEASE_UNVERIFIED');
  // Reconciled release: state is recorded from authoritative observation.
  return registry.map(r => r.sessionId === sessionId
    ? { ...r, slotHeld: false, state: evidence.type === 'verified_stop' ? 'stopped' : 'idle', observedAt: evidence.observedAt, updatedAt: now }
    : r);
}

export function capacityStatus(registry: SessionRecord[], now: number) {
  const holders = slotHolders(registry);
  return {
    maxSlots: MAX_SESSION_SLOTS,
    used: holders.length,
    free: Math.max(0, MAX_SESSION_SLOTS - holders.length),
    holders: holders.map(r => ({ sessionId: r.sessionId, state: r.state, source: r.source, provider: r.provider })),
    conservative: true,
    note: 'Starting and uncertain sessions hold slots. Timeouts never release capacity.',
    observedAt: now,
  };
}

// ---------------------------------------------------------------------------
// 3. Model selection, quota accounting and budget policy
// ---------------------------------------------------------------------------

export type ProviderKind = 'freebuff-native' | 'openrouter' | 'codex';

export interface ModelObservation {
  modelId: string;
  provider: ProviderKind;
  toolSupport: 'verified' | 'unknown' | 'none';
  contextSize: number | null;      // unknown stays null, never invented
  available: boolean | null;       // unknown stays null
  rateLimitKnown: boolean;
  dailyAllowance: string | null;   // free-text verified terms, else null
  freeWindow: string | null;
  costNote: string | null;         // verified terms only
  resetTimezone: string | null;
  observedFailures: number;
  lastFailureAt: number | null;
  observedAt: number;
}

export interface ModelRequirements {
  needsTools: boolean;
  minContext: number | null;
  difficulty: 'low' | 'medium' | 'high';
  allowMetered: boolean;           // explicit budget decision per task
}

export interface FallbackEvidence {
  // Codex fallback requires recorded evidence that BOTH non-Codex routes lack
  // a suitable available option. A single transient error is not this evidence.
  freebuffNativeUnavailable: string;
  openrouterUnavailable: string;
  recordedAt: number;
}

export interface BudgetPolicy {
  allowMetered: boolean;
  maxSpendUsd: number;             // defaults to zero
}

export const DEFAULT_BUDGET: BudgetPolicy = { allowMetered: false, maxSpendUsd: 0 };

export function selectModel(
  catalog: ModelObservation[], requirements: ModelRequirements, budget: BudgetPolicy = DEFAULT_BUDGET,
  fallbackEvidence: FallbackEvidence | null = null,
): { selected: ModelObservation | null; reason: string; skipped: { modelId: string; why: string }[]; codexAllowed: boolean } {
  const skipped: { modelId: string; why: string }[] = [];
  const nonCodex: ModelObservation[] = [];
  const codex: ModelObservation[] = [];
  for (const m of catalog) {
    if (m.available === false) { skipped.push({ modelId: m.modelId, why: 'UNAVAILABLE' }); continue; }
    if (requirements.needsTools && m.toolSupport !== 'verified') { skipped.push({ modelId: m.modelId, why: 'TOOL_SUPPORT_UNVERIFIED' }); continue; }
    if (requirements.minContext !== null && (m.contextSize === null || m.contextSize < requirements.minContext)) {
      skipped.push({ modelId: m.modelId, why: m.contextSize === null ? 'CONTEXT_UNKNOWN' : 'CONTEXT_TOO_SMALL' }); continue;
    }
    const metered = m.costNote !== null && !/^free\b/i.test(m.costNote);
    if (metered && (!budget.allowMetered || budget.maxSpendUsd <= 0)) {
      skipped.push({ modelId: m.modelId, why: 'BUDGET_REFUSAL_METERED' }); continue;
    }
    (m.provider === 'codex' ? codex : nonCodex).push(m);
  }
  const order = (a: ModelObservation, b: ModelObservation) => {
    const tier = (m: ModelObservation) => (m.toolSupport === 'verified' ? 0 : 1) + (m.available === null ? 1 : 0) + m.observedFailures;
    return tier(a) - tier(b);
  };
  if (nonCodex.length > 0) {
    const selected = [...nonCodex].sort(order)[0];
    return { selected, reason: 'SELECTED_WITHIN_BUDGET', skipped, codexAllowed: false };
  }
  // Only Codex candidates remain: both non-Codex routes must be recorded as
  // lacking a suitable available option before Codex fallback is permitted.
  const evidenceOk = !!fallbackEvidence
    && typeof fallbackEvidence.freebuffNativeUnavailable === 'string' && fallbackEvidence.freebuffNativeUnavailable.length >= 8
    && typeof fallbackEvidence.openrouterUnavailable === 'string' && fallbackEvidence.openrouterUnavailable.length >= 8;
  if (!evidenceOk) {
    return { selected: null, reason: 'CODEX_FALLBACK_PREREQUISITE_NOT_MET', skipped, codexAllowed: false };
  }
  if (codex.length > 0) return { selected: [...codex].sort(order)[0], reason: 'CODEX_FALLBACK_WITH_RECORDED_EVIDENCE', skipped, codexAllowed: true };
  return { selected: null, reason: 'NO_SUITABLE_AVAILABLE_OPTION', skipped, codexAllowed: false };
}

// ---------------------------------------------------------------------------
// 4. Capability matrix — grounded in the installed Freebuff build + live checks
// ---------------------------------------------------------------------------

export type CapabilityState = 'live-verified' | 'build-verified' | 'unsupported';

export interface Capability {
  name: string;
  state: CapabilityState;
  route: string | null;
  evidence: string;
}

// Route strings were extracted from the installed Freebuff UI bundle on foo
// (2026-10-17); live-verified entries were exercised against the loopback API.
// Anything not on this list is not a gateway capability. Endpoints are never
// guessed: an unverified route stays build-verified or unsupported.
export const CAPABILITIES: readonly Capability[] = Object.freeze([
  { name: 'read_session_snapshot', state: 'live-verified', route: 'GET /api/thread/:id?projectPath=', evidence: 'HTTP 200 on bac212ab, 823715-byte body, top-level thread/messages/items' },
  { name: 'queue_message', state: 'build-verified', route: 'POST /api/thread/:id/queue {projectPath,text,now:false}', evidence: 'installed poller README + Freebuff route; live write pending the approved round trip' },
  { name: 'interrupt_generation', state: 'build-verified', route: 'POST /api/thread/:id/stop', evidence: 'route string in installed UI bundle; interrupts active generation, does not pause the queue' },
  { name: 'resume_thread', state: 'build-verified', route: 'POST /api/thread/:id/resume', evidence: 'route string in installed UI bundle; not activated — policy excludes automatic resume' },
  { name: 'pause_queue', state: 'unsupported', route: null, evidence: 'no distinct queue-pause route found in the installed build; thread.queuePaused is observed state only' },
  { name: 'create_session', state: 'unsupported', route: null, evidence: 'no verified session-creation route; policy excludes session creation' },
  { name: 'adopt_session', state: 'live-verified', route: null, evidence: 'registry-only record of an allowlisted existing session; no local API call' },
  { name: 'list_models', state: 'unsupported', route: null, evidence: 'no verified catalog endpoint on the loopback API; the gateway reports recorded observations only' },
  { name: 'select_model', state: 'unsupported', route: null, evidence: 'no verified model-selection route at a safe run boundary in the installed build' },
  { name: 'read_run_status', state: 'live-verified', route: 'GET /api/thread/:id (thread.turnState)', evidence: 'thread.turnState observed live (idle/running) in the verified response shape' },
  { name: 'read_receipts', state: 'live-verified', route: null, evidence: 'gateway receipts: accepted/delivered/started/completed/failed/uncertain' },
]);

export function capability(name: string): Capability {
  const found = CAPABILITIES.find(c => c.name === name);
  if (!found) throw new ControlError('CAPABILITY_UNKNOWN');
  return found;
}

export function requireCapability(name: string): Capability {
  const c = capability(name);
  if (c.state === 'unsupported') throw new ControlError('CAPABILITY_UNSUPPORTED');
  return c;
}

// ---------------------------------------------------------------------------
// 5. Durable work queue (lossless mapping of legacy work; three lanes)
// ---------------------------------------------------------------------------

export type WorkStatus = 'ready' | 'active' | 'blocked' | 'review_pending' | 'done';

export interface WorkItem {
  itemId: string;
  lane: 1 | 2 | 3;
  title: string;
  origin: string;              // original session/task ID
  status: WorkStatus;
  artifactRefs: string[];      // exact paths/hashes — never re-derived
  dependencies: string[];
  acceptance: string;
  nextAction: string;
  owner: string;
  updatedAt: number;
}

export function assertWorkItem(item: WorkItem): WorkItem {
  if (!item.itemId || !item.origin || !item.acceptance || !item.nextAction || !item.owner) throw new ControlError('WORK_ITEM_INVALID');
  if (![1, 2, 3].includes(item.lane)) throw new ControlError('WORK_LANE_INVALID');
  if (!['ready', 'active', 'blocked', 'review_pending', 'done'].includes(item.status)) throw new ControlError('WORK_STATUS_INVALID');
  return item;
}
