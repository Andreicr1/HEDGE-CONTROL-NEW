---
status: complete
priority: p1
issue_id: "003"
tags: [code-review, typescript, runtime-error]
dependencies: []
---

# JSON.parse in Svelte template crashes component on malformed data

## Problem Statement

`JSON.parse(evt.created_contract_ids)` is called directly in a Svelte `{#each}` block. If `created_contract_ids` is malformed, null, or not valid JSON, this throws an unhandled error in the render cycle, crashing the entire RFQ detail component.

## Findings

**Location**: `frontend-svelte/src/routes/(protected)/rfq/[id]/+page.svelte:494`

```svelte
{#each JSON.parse(evt.created_contract_ids) as contractId}
```

## Proposed Solutions

### Option A: Helper function with try/catch
```typescript
function parseContractIds(raw: string | null): string[] {
    if (!raw) return [];
    try { return JSON.parse(raw); } catch { return []; }
}
```

- **Effort**: Small (5 minutes)
- **Risk**: None

## Acceptance Criteria
- [ ] Malformed JSON does not crash the component
- [ ] Valid JSON still renders contract links correctly

## Work Log
- 2026-03-16: Identified by TypeScript reviewer during PR #2 review
