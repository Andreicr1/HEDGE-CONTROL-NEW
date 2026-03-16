---
status: complete
priority: p2
issue_id: "011"
tags: [code-review, ci-cd]
dependencies: []
---

# CI: schema-drift soft-fail + deploy not gated on CI passing

## Problem Statement

1. Schema drift check uses `continue-on-error: true` — contradicts team philosophy "CI checks must enforce fixes (hard fail), not just detect drift"
2. `deploy.yml` triggers on push to main without requiring `ci.yml` to pass

## Findings

**Location**: `.github/workflows/ci.yml:153` (continue-on-error), `.github/workflows/deploy.yml` (no needs/dependency on CI)

## Proposed Solutions

### Option A: Move schema drift into E2E job + gate deploy on CI
1. Run schema drift check as a step in the E2E job (after backend is up) with hard failure
2. Add `workflow_run` trigger on deploy.yml that requires CI completion with success

- **Effort**: Small
- **Risk**: Low

## Acceptance Criteria
- [ ] Schema drift check fails the pipeline on drift
- [ ] Deploy only runs after CI passes

## Work Log
- 2026-03-16: Identified by architecture reviewer during PR #2 review
