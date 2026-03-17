---
status: complete
priority: p2
issue_id: "009"
tags: [code-review, performance]
dependencies: []
---

# sanitizeChartStrings deep-clone runs on every $effect trigger

## Problem Statement

`sanitizeChartStrings` performs a full recursive deep-clone of the entire ECharts options object on every `$effect` update. For charts with large data arrays (365+ MTM points, P&L entries), this creates O(n*d) allocations per update and GC pressure.

## Findings

**Location**: `EChart.svelte:97-101` calls `safeOptions(options)` in `$effect`

The sanitization should happen once when data arrives from the API, not on every render cycle.

## Proposed Solutions

### Option A: Sanitize at data insertion point
Remove `sanitize` prop from EChart. Call `escapeHtml()` on user-generated strings (counterparty names) when constructing chart options in each page. Delete `sanitizeChartStrings` recursive function — keep only `escapeHtml`.

- **Effort**: Small
- **Risk**: Low — requires identifying where user data enters chart options

## Acceptance Criteria
- [ ] No recursive sanitization in the render path
- [ ] User-generated strings still escaped before reaching ECharts
- [ ] Chart updates do not trigger full options deep-clone

## Work Log
- 2026-03-16: Identified by performance reviewer + simplicity reviewer during PR #2 review
