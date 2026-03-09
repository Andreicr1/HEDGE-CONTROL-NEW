---
title: feat: Build agent platform skeleton with RFQ proving slice
type: feat
status: completed
date: 2026-03-09
origin: docs/brainstorms/2026-03-09-agent-native-remediation-brainstorm.md
---

# feat: Build agent platform skeleton with RFQ proving slice

## Overview
Build the first internal agent-native platform foundation for Hedge Control. The target is not a user-facing chat experience yet. The goal is to establish a consistent capability layer that agents can use safely across domains, while proving the full write-capable pattern deeply in RFQ first.

This plan carries forward the brainstorm decision to prioritize platform contracts over surface UX and to use RFQ as the proving slice while giving other domains thin, consistent coverage from day one (see brainstorm: docs/brainstorms/2026-03-09-agent-native-remediation-brainstorm.md).

## Problem Statement / Motivation
The current platform has strong backend services, broad REST coverage, and a shared persistent data model, but it is not agent-native. The audit found no product-facing agent entry point, no explicit tool surface, minimal dynamic context injection, weak capability discovery, and mostly silent or delayed UI reflection for automated actions.

At the same time, the repo already contains the right building blocks for a safe foundation: a unified FastAPI app in [backend/app/main.py](backend/app/main.py), a shared SQLAlchemy data layer in [backend/app/core/database.py](backend/app/core/database.py), domain services under [backend/app/services](backend/app/services), and an RFQ workflow that already mixes orchestration with LLM-assisted parsing in [backend/app/services/llm_agent.py](backend/app/services/llm_agent.py) and [backend/app/services/rfq_orchestrator.py](backend/app/services/rfq_orchestrator.py).

## Proposed Solution
Introduce a new internal agent platform layer with four core contracts:

1. Tool contract
Each domain exposes explicit agent-callable capabilities rather than relying on raw REST routes as the agent interface.

2. Context contract
Each agent execution can receive structured, dynamic domain context and capability metadata.

3. Execution contract
Agent actions must support explicit completion, review boundaries, idempotency, and audit metadata.

4. Discovery contract
The platform must be able to describe what tools exist, what they operate on, and what scope or permissions apply.

RFQ is the first deep slice. Orders, contracts, exposures, analytics, audit, and market data adopt the same contract shape initially through thinner adapters.

## Why This Approach
Three options were considered in the brainstorm: a uniform thin skeleton everywhere, a deep RFQ slice with a thin cross-domain skeleton, and a read-only foundation first. The selected direction is the middle path because it proves the hard workflow without forcing equal domain maturity up front (see brainstorm: docs/brainstorms/2026-03-09-agent-native-remediation-brainstorm.md).

This matches the codebase:
- RFQ already has the only AI-assisted runtime path.
- Service boundaries are clear enough to wrap without a large rewrite.
- Shared persistent data is already strong.
- The main missing pieces are explicit agent contracts, discovery, context, and event propagation.

## Scope Boundaries

### In Scope
- Internal agent capability layer and contracts
- RFQ deep slice with write-capable tools
- Thin adapter pattern for other domains
- Context injection for agent executions
- Audit metadata for agent actions
- Capability registry and discovery surface
- UI/update propagation design for automated changes

### Out of Scope
- Full end-user chat/operator UI
- Broad autonomous trading or decisioning across all domains
- Replacing existing REST APIs
- Rebuilding the current UI5 information architecture

## Research Findings

### Repo Evidence
- FastAPI route composition is centralized in [backend/app/main.py](backend/app/main.py#L210).
- RFQ AI parsing is implemented in [backend/app/services/llm_agent.py](backend/app/services/llm_agent.py#L43) and orchestrated in [backend/app/services/rfq_orchestrator.py](backend/app/services/rfq_orchestrator.py#L338).
- RFQ state and quote updates already persist in the shared database via existing services in [backend/app/services/rfq_service.py](backend/app/services/rfq_service.py).
- Shared persistence is consistent through [backend/app/core/database.py](backend/app/core/database.py) and the models in [backend/app/models](backend/app/models).
- The scenario engine intentionally uses non-persistent simulation state in [backend/app/services/scenario_whatif_service.py](backend/app/services/scenario_whatif_service.py), which is a useful boundary to preserve.
- UI reflection for automated RFQ changes currently relies on polling in [frontend/webapp/controller/RfqDetail.controller.js](frontend/webapp/controller/RfqDetail.controller.js#L51).
- Scheduled automation already exists in [backend/app/tasks/scheduler.py](backend/app/tasks/scheduler.py), but there is no event bridge to the frontend.

### Repo Learnings
- No `docs/solutions/` library was present in this workspace during planning.

### Research Decision
Proceed without external research. The feature is architecture-heavy, but this repo already provides strong local context, recent audit findings, and clear domain/service boundaries.

## System-Wide Impact
- Interaction graph: Agent requests will sit above existing domain services and below any future user-facing agent UI. Tool handlers should call service-layer logic rather than duplicate route logic.
- Error propagation: Tool errors must normalize service exceptions, validation failures, auth failures, and partial-completion states into a stable execution result format.
- State lifecycle risks: Multi-step RFQ operations can create partial effects if message send, quote creation, ranking refresh, or state transitions are not explicitly bounded.
- API surface parity: Existing HTTP routes remain intact, but new agent tools must avoid drifting into a second business-logic layer.
- Integration testing: Cross-layer tests are required for tool invocation, audit tagging, context assembly, idempotent retries, and UI visibility after automation.

## Architecture Decisions

### 1. Add an Internal Agent Platform Module
Create a dedicated module under the backend for agent capabilities, separate from HTTP routes and existing service implementations.

Suggested shape:
- capability registry
- tool definitions
- context builders
- execution result schema
- audit tagging helpers

This layer should call existing services rather than routes.

### 2. Define a Stable Tool Taxonomy
Split tools into:
- platform primitives: list capabilities, fetch context, complete task, refresh context
- domain tools: create RFQ, list RFQs, add quote, refresh RFQ, award quote, reject quote
- thin adapters for non-RFQ domains: orders, contracts, exposures, MTM, P&L, audit, market data

### 3. Make RFQ the First Full Execution Slice
RFQ must prove:
- read and write capabilities
- context assembly per execution
- explicit completion signaling
- audit traceability for automated actors
- event or notification propagation back to the UI layer

### 4. Preserve Shared Workspace Semantics
Agent actions must continue to mutate the same database-backed domain models already used by the app. No separate persistent agent datastore should be introduced for business state.

### 5. Keep User-Facing UX Deferred
No broad end-user agent UI in the first phase. Any discovery surface created now should primarily serve internal engineering and observability.

## Rollout Plan

### Phase 1: Platform Contracts
- Define execution schemas for tool inputs, outputs, completion state, and failure state.
- Define capability registry metadata: domain, operation, mutability, auth scope, idempotency expectations.
- Define context builder interfaces and baseline context payload shape.
- Define agent audit metadata format, including actor type, capability name, execution id, and correlation id.

### Phase 2: RFQ Deep Slice
- Wrap RFQ actions as explicit tools backed by RFQ services.
- Move RFQ-specific context construction into dedicated context builders instead of inline prompt concatenation.
- Decompose [backend/app/services/rfq_orchestrator.py](backend/app/services/rfq_orchestrator.py) where hidden business decisions should become tool-visible execution steps or explicit policies.
- Introduce explicit completion/review semantics for quote parsing and auto-creation flows.

### Phase 3: Thin Cross-Domain Skeleton
- Add thin tools for orders, contracts, exposures, analytics, audit, and market data using the same contracts.
- Favor read capabilities first outside RFQ, with carefully selected write operations where risk is low.
- Ensure each tool is discoverable through the capability registry.

### Phase 4: Operability and Visibility
- Add event propagation design for automated state changes. Minimum acceptable fallback is explicit polling contracts; preferred outcome is SSE or equivalent for RFQ updates.
- Add internal observability for agent runs, including success/failure metrics and audit references.
- Expose internal discovery and documentation for engineering users.

## Acceptance Criteria
- [x] A new internal capability layer exists and is isolated from route handlers.
- [x] The platform can enumerate registered capabilities with metadata for domain, mutability, and auth scope.
- [x] RFQ has a full deep-slice tool set covering its first milestone operations.
- [x] RFQ context is assembled dynamically through a context builder rather than ad hoc prompt string assembly.
- [x] Agent executions produce explicit completion or review-required results.
- [x] Agent-triggered mutations carry audit metadata linking action, execution id, and resulting domain change.
- [x] At least one UI visibility path exists for RFQ automation beyond silent background mutation.
- [x] At least three non-RFQ domains expose thin tools using the same platform contracts.
- [x] No business state is duplicated into a separate persistent agent store.
- [x] Existing REST endpoints and current UI flows continue to work unchanged.

## Spec and Flow Gaps to Address
- The platform needs a clear mutability policy by domain so thin adapters do not accidentally over-expose risky actions.
- RFQ automation needs clear boundaries between parse, validate, persist, notify, and transition so retries do not duplicate state.
- UI reflection needs an explicit contract for background-originated changes, especially around RFQ quotes and scheduled jobs.
- Tool discovery must distinguish internal-only platform capabilities from any later user-facing discovery layer.
- Context freshness rules must be defined so long-running agent executions do not act on stale RFQ or market state.

## Success Metrics
- Internal engineering can invoke RFQ capabilities through the platform layer without using raw REST routes as the agent interface.
- RFQ tool executions are fully traceable in logs and audit metadata.
- Cross-domain thin adapters can be added with a repeatable pattern instead of bespoke glue.
- The gap between current REST coverage and actual agent-native capability is materially reduced in the next audit.

## Dependencies and Risks

### Dependencies
- Existing domain services remain the source of business logic.
- Auth and role enforcement patterns in the backend remain reusable for tool scope decisions.
- Current RFQ tests provide a base for regression coverage.

### Risks
- A thin platform layer can become a second orchestration layer if it duplicates logic already embedded in services.
- RFQ automation retries may create duplicate quotes or invalid transitions if idempotency is not designed first.
- Tool discovery can expose unsafe write operations if mutability and actor scope are not explicit.
- UI visibility work can sprawl if it attempts to solve all background eventing at once.

### Mitigations
- Route all tool execution through service-layer boundaries.
- Require explicit idempotency and completion semantics for write-capable tools.
- Start UI reflection with the RFQ proving slice only.
- Keep non-RFQ domains thin until the RFQ execution model is proven.

## Implementation Detail Level
Use a comprehensive implementation pass. This is an architectural feature with cross-layer impact and should be broken into phased work items rather than handled as a single change.

## Sources and References
- Origin brainstorm: [docs/brainstorms/2026-03-09-agent-native-remediation-brainstorm.md](docs/brainstorms/2026-03-09-agent-native-remediation-brainstorm.md)
- App route composition: [backend/app/main.py](backend/app/main.py)
- RFQ parser prompts: [backend/app/services/llm_agent.py](backend/app/services/llm_agent.py)
- RFQ orchestration flow: [backend/app/services/rfq_orchestrator.py](backend/app/services/rfq_orchestrator.py)
- Shared database setup: [backend/app/core/database.py](backend/app/core/database.py)
- Scheduler/background jobs: [backend/app/tasks/scheduler.py](backend/app/tasks/scheduler.py)
- RFQ polling behavior: [frontend/webapp/controller/RfqDetail.controller.js](frontend/webapp/controller/RfqDetail.controller.js)
- Cross-reference audit: [AUDIT_CROSS_REFERENCE.md](AUDIT_CROSS_REFERENCE.md)
- Integration audit: [docs/integration-audit.md](docs/integration-audit.md)
