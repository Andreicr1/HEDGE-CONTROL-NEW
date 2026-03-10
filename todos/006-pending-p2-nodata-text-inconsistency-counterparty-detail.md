---
status: done
priority: p2
issue_id: "006"
tags: [ui5, ux, nodata, counterparty-detail, illustrated-message]
dependencies: []
---

# Fix noDataText Inconsistency in CounterpartyDetail Tables

## Problem Statement

All 9 list views in the application use an `<IllustratedMessage>` inside the `<Table noData>` aggregation to display a rich empty-state graphic with title, description, and optional action button. The two tables in `CounterpartyDetail.view.xml` use a plain `noDataText="..."` attribute string instead. This creates a visible design inconsistency for end users: empty states in CounterpartyDetail look completely different from every other screen in the application.

## Findings

- `webapp/view/CounterpartyDetail.view.xml` — Contracts table:
  ```xml
  <Table items="{cptyDet>/contracts}" noDataText="{i18n>noContractsForCounterparty}">
  ```
- `webapp/view/CounterpartyDetail.view.xml` — Exposures table:
  ```xml
  <Table items="{cptyDet>/exposures}" noDataText="{i18n>noExposuresForCounterparty}">
  ```
- All other list views (Contracts, Orders, Exposures, Rfqs, Linkages views) use:
  ```xml
  <Table ...>
    <noData>
      <m:IllustratedMessage
        illustrationType="sapIllus-EmptyList"
        title="{i18n>noDataTitle}"
        description="{i18n>noDataDescription}"
      />
    </noData>
  </Table>
  ```

**Impact:** Users see an inconsistent UI. When the counterparty has no contracts or exposures, the table shows a plain grey text string instead of the Fiori-compliant illustrated empty state. This is especially noticeable when navigating from a list view to a detail view.

## Proposed Solutions

### Option 1: Replace noDataText with IllustratedMessage aggregation (Recommended)

**Approach:**

Replace both table `noDataText` attributes with the `<noData>` aggregation:

```xml
<!-- Contracts table — before -->
<Table items="{cptyDet>/contracts}" noDataText="{i18n>noContractsForCounterparty}">

<!-- Contracts table — after -->
<Table items="{cptyDet>/contracts}">
  <noData>
    <m:IllustratedMessage
      illustrationType="sapIllus-EmptyList"
      title="{i18n>noContractsForCounterparty}"
      description="{i18n>noDataDescription}"
    />
  </noData>
  ...
```

Apply the same pattern to the Exposures table.

Reuse existing i18n keys where possible; the existing `noContractsForCounterparty` and `noExposuresForCounterparty` keys can serve as the `title` binding.

**Pros:** Consistent with all other views; uses Fiori design system correctly; single locale key change
**Cons:** Minor XML change only
**Effort:** 15-20 minutes
**Risk:** Very Low

---

### Option 2: Create a shared `EmptyState` fragment and use it everywhere (including here)

**Approach:** Activate `webapp/fragment/EmptyState.fragment.xml` (see todo 005) and load it in all tables.

**Pros:** Consistent AND reduces duplication
**Cons:** Larger scope; depends on todo 005 completion; fragment needs a parameterized title
**Effort:** 2-3 hours for unified refactor
**Risk:** Low

## Recommended Action

Apply Option 1 immediately (15 minutes). If the team later decides to centralize empty-state into the `EmptyState.fragment.xml` (see todo 005, Option 2), the migration from Option 1 is trivial.

## Technical Details

**Affected files:**
- `webapp/view/CounterpartyDetail.view.xml` — both table definitions

**i18n keys involved:**
- `noContractsForCounterparty` (existing) — use as `title` attribute
- `noExposuresForCounterparty` (existing) — use as `title` attribute  
- `noDataDescription` (existing in other views) — use as `description` attribute

**Illustrator type:** `sapIllus-EmptyList` (consistent with other views)

**Database changes:** No

## Acceptance Criteria

- [ ] Both tables in `CounterpartyDetail.view.xml` use `<noData><m:IllustratedMessage .../></noData>` aggregation
- [ ] Neither table uses the `noDataText` attribute
- [ ] Illustrated empty state shows correct contextual title for contracts vs. exposures
- [ ] Visual appearance matches the empty state on the Contracts list view and Exposures list view
- [ ] No regression in table rendering when data is present

## Work Log

### 2025-01-31 - Discovered in architecture review

**By:** architecture-strategist agent

**Actions:**
- Confirmed both CounterpartyDetail tables use `noDataText` attribute (not IllustratedMessage)
- Confirmed all 9 list views use `IllustratedMessage` aggregation
- Rated P2: User-facing design inconsistency; Fiori standard not followed
