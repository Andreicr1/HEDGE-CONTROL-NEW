---
date: 2026-03-09
topic: agent-native-remediation
---

# Agent-Native Remediation for Hedge Control

## What We're Building
We are defining the first agent-native foundation for Hedge Control as internal platform infrastructure, not as a user-facing chat product. The goal is to create a consistent agent capability layer across the platform while proving the write-capable model deeply in the RFQ domain first.

The first milestone should establish the contracts that every future agent-facing domain will use: explicit tool surfaces, capability discovery, context injection, auditability, and execution boundaries. RFQ becomes the proving slice because it already contains the only real AI-assisted workflow in the product, while the rest of the platform can initially adopt thinner wrappers over existing service boundaries.

## Why This Approach
We considered three directions: a uniform thin skeleton across all domains, a deep RFQ slice with a thin cross-domain skeleton, and a read-only foundation first. The chosen approach is the middle path.

This approach gives the platform a real agent-native center of gravity without forcing every domain to mature at the same speed. It fits the current codebase: RFQ already has the only LLM-assisted workflow, the backend already has strong service boundaries, and the audit showed that shared data is strong while agent entry points, discovery, and execution contracts are missing. A deep RFQ slice proves the hard parts, while the thin skeleton prevents the solution from becoming RFQ-specific infrastructure.

## Key Decisions
- Build platform foundation first: The first phase is infrastructure-only, with no end-user agent UI.
- Target internal engineering users first: The immediate customer is the team building the capability layer, not traders or risk users directly.
- Use RFQ as the deep proving slice: RFQ gets write-capable agent depth first because it already contains the only AI-assisted runtime path.
- Keep thin cross-domain coverage from day one: Orders, contracts, exposures, analytics, and audit should adopt the same capability shape even if initially shallow.
- Optimize for explicit agent contracts: REST endpoints alone do not count as agent-native capability; the platform needs a real tool surface, discovery model, context model, and audit path.
- Preserve shared workspace architecture: Agent actions must continue to operate on the same persistent data stores already used by the UI and services.
- Defer user-facing agent UX: Capability discovery for product users can come after the internal platform layer is stable.

## Resolved Questions
- Primary goal: Platform foundation first.
- First beneficiary: Internal engineering team.
- Success bar: A full agent platform skeleton across domains.
- User-facing scope in phase one: Infrastructure-only.
- Coverage strategy: Deep RFQ slice plus thin coverage elsewhere.

## Open Questions
None at this stage. The remaining work belongs to planning and sequencing, not additional product-definition discovery.

## Next Steps
Move to planning with a phased design that defines:
- the minimum platform contracts for agent tools, context injection, capability discovery, and auditability,
- the RFQ deep-slice scope that proves write-capable agent execution safely,
- the thin adapter pattern for the rest of the domains,
- and the rollout criteria for introducing user-facing agent experiences later.

-> /ce-plan for implementation details.
