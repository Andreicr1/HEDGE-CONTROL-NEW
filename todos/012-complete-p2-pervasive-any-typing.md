---
status: complete
priority: p2
issue_id: "012"
tags: [code-review, typescript]
dependencies: ["007"]
---

# 30+ instances of `any` typing in route pages

## Problem Statement

Virtually every page component declares state as `any`: `$state<any>(null)`, `$state<any[]>([])`. This eliminates TypeScript's value for catching backend schema changes. Contradicts "correctness over convenience" principle.

## Findings

30+ instances across: rfq/[id], exposures, cashflow, contracts/[id], analytics/what-if, and more.

Depends on #007 (openapi-fetch migration) — once the typed client is used, response types are inferred automatically.

## Proposed Solutions

### Option A: Create provisional interface types
Define minimal types in `$lib/api/types/` for each entity (Rfq, Quote, Contract, Exposure, etc.) based on fields actually accessed in templates. Replace when schema.d.ts is generated.

- **Effort**: Medium
- **Risk**: Low — types can be provisional

## Acceptance Criteria
- [ ] Zero `any` in API-layer state declarations
- [ ] All template property accesses type-checked

## Work Log
- 2026-03-16: Identified by TypeScript reviewer during PR #2 review
