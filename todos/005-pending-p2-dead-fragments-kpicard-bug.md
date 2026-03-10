---
status: done
priority: p2
issue_id: "005"
tags: [ui5, fragments, dead-code, kpi-card]
dependencies: []
---

# Remove Dead Fragments and Fix KpiCard Invalid Event Binding

## Problem Statement

Four fragment files in `webapp/fragment/` are completely unreferenced — no controller calls `loadFragment()` on any of them. Two of these fragments also contain hard errors that would crash the app if they were ever loaded: `KpiCard.fragment.xml` uses an invalid UI5 event binding syntax (`press="{press}"`), and `ConfirmDialog.fragment.xml` references event handlers that don't exist in any controller. The dead fragments create maintenance confusion and risk being accidentally activated with broken behavior.

## Findings

All fragments analyzed:

### `KpiCard.fragment.xml` — Hard Bug
```xml
<GenericTile press="{press}" ...>
```
`press` is an **event**, not a property. In SAP UI5, event handlers cannot be data-bound with `{expression}` syntax. This would throw a runtime exception if the fragment were loaded. The correct syntax is either `press=".onKpiTilePress"` (static handler) or a controller-defined press event.

### `ConfirmDialog.fragment.xml` — References Nonexistent Handlers
```xml
confirm="onConfirmDialogConfirm" cancel="onConfirmDialogCancel"
```
Neither `onConfirmDialogConfirm` nor `onConfirmDialogCancel` exist in any controller in `webapp/controller/`. This fragment cannot be activated without implementing those handlers.

### `EntityHeader.fragment.xml` — Redundant ObjectHeader
This fragment contains an `<ObjectHeader>` that duplicates markup already present inline in the detail views. Never referenced.

### `EmptyState.fragment.xml` — IllustratedMessage Fragment
This wraps a `<core:FragmentDefinition>` around an `sap.m.IllustratedMessage`. However, all 9 list views already inline their `<IllustratedMessage>` elements directly inside `<Table noData>` aggregations. This fragment adds an abstraction that isn't used anywhere.

**Grep verification:** No `loadFragment("KpiCard")`, `loadFragment("EmptyState")`, `loadFragment("EntityHeader")`, or `loadFragment("ConfirmDialog")` found in any controller.

## Proposed Solutions

### Option 1: Delete EntityHeader + fix KpiCard + decide on others (Recommended)

**Actions:**
1. **Delete** `webapp/fragment/EntityHeader.fragment.xml` — pure dead code, no recovery path
2. **Fix** `webapp/fragment/KpiCard.fragment.xml`:
   - Change `press="{press}"` → `press=".onKpiTilePress"` 
   - Add `onKpiTilePress` handler to any controller that would use this fragment
   - OR delete if there's no plan to use it
3. **Keep** `webapp/fragment/ConfirmDialog.fragment.xml` only if deletion confirmation dialogs are planned; otherwise delete with `confirmDelete`/`btnConfirm`/`btnCancel`/`confirmTitle` i18n keys (see todo 012)
4. **Keep** `webapp/fragment/EmptyState.fragment.xml` OR unify all inline `IllustratedMessage` usage to use this fragment for consistency

**Pros:** Eliminates dead code; fixes hard bug before it can activate
**Cons:** Opinionated — team must decide on ConfirmDialog + EmptyState roadmap
**Effort:** 30-60 minutes
**Risk:** Very Low (deletions of unreferenced files)

---

### Option 2: Activate all fragments with correct implementations

**Approach:** Wire `ConfirmDialog` with real handlers (delete confirmation UX), use `EmptyState` fragment in all tables, fix `KpiCard`, delete `EntityHeader`.

**Pros:** Completes the original design intent; improves consistency
**Cons:** Larger scope; requires design decisions on confirm-delete UX
**Effort:** 1-2 days
**Risk:** Low

---

### Option 3: Delete all four fragments

**Pros:** Maximum simplicity; no dead code at all
**Cons:** Deletes potentially useful ConfirmDialog/EmptyState patterns
**Effort:** 15 minutes
**Risk:** Very Low

## Recommended Action

Apply a focused version of Option 1:
1. Delete `EntityHeader.fragment.xml` immediately (no recovery value)
2. Fix `KpiCard.fragment.xml` `press` binding immediately (it's a hard error)
3. Document ConfirmDialog and EmptyState as "activate or delete" decisions to make before v2 release

## Technical Details

**Files to delete:**
- `webapp/fragment/EntityHeader.fragment.xml`

**Files to fix:**
- `webapp/fragment/KpiCard.fragment.xml` — line with `press="{press}"`

**Files to decide:**
- `webapp/fragment/ConfirmDialog.fragment.xml` — needs `onConfirmDialogConfirm` + `onConfirmDialogCancel` in a controller, or deletion
- `webapp/fragment/EmptyState.fragment.xml` — use everywhere or delete

**Related i18n keys (dead if ConfirmDialog deleted):**
- `confirmDelete`, `btnConfirm`, `btnCancel`, `confirmTitle`

**Database changes:** No

## Acceptance Criteria

- [ ] `EntityHeader.fragment.xml` is deleted
- [ ] `KpiCard.fragment.xml` no longer has `press="{press}"` (either fixed or deleted)
- [ ] No fragment file references nonexistent controller event handlers
- [ ] All remaining fragments have a documented intent (either active use or explicit "activate in sprint N" comment)
- [ ] No console errors related to fragment event binding if any fragment is loaded

## Work Log

### 2025-01-31 - Discovered in architecture and code-simplicity review

**By:** architecture-strategist agent + code-simplicity-reviewer agent

**Actions:**
- Confirmed no `loadFragment` calls reference any of the 4 fragments in webapp/controller/
- Confirmed `KpiCard.fragment.xml` has invalid event binding syntax
- Confirmed `ConfirmDialog.fragment.xml` references nonexistent handlers
- Rated P2: Hard bug (KpiCard press) is dangerous; dead fragment files create maintenance confusion
