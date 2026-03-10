---
status: done
priority: p3
issue_id: "011"
tags: [ui5, css, theming, kpi, fiori]
dependencies: []
---

# Fix CSS KPI Color Token Bug and Remove Unused KPI Color Classes

## Problem Statement

`webapp/css/style.css` defines three KPI color classes (`.hcKpiPositive`, `.hcKpiNegative`, `.hcKpiCritical`). The `.hcKpiCritical` class contains a copy-paste error: it maps to `var(--sapNegativeColor)` (red) instead of `var(--sapCriticalColor)` (orange/amber). More importantly, all three classes are **never applied to any element** in any view — the views use the `valueColor` property binding approach instead. The CSS classes and the `valueColor` approach serve the same purpose (coloring KPI values) and are in conflict; retaining both creates maintenance confusion.

## Findings

- `webapp/css/style.css` — full KPI color section:
  ```css
  .hcKpiPositive .sapMNCSValue { color: var(--sapPositiveColor); }   /* green ✓ */
  .hcKpiNegative .sapMNCSValue { color: var(--sapNegativeColor); }   /* red ✓ */
  .hcKpiCritical .sapMNCSValue { color: var(--sapNegativeColor); }   /* red ✗ — should be sapCriticalColor (amber) */
  ```
- **No XML view** in `webapp/view/` applies `.hcKpiPositive`, `.hcKpiNegative`, or `.hcKpiCritical` to any element
- `Home.view.xml` uses `valueColor="{viewModel>/kpiExposureStatus}"` on `NumericContent` controls — this uses the built-in `sap.m.ValueColor` enum binding, which is the recommended Fiori approach for KPI tile coloring
- The CSS approach and `valueColor` approach both attempt to color the same `sapMNCSValue` element; if the CSS classes were ever applied alongside `valueColor`, they would **conflict** (CSS specificity battle)

**Root cause of the token error:** `.hcKpiCritical` was likely copy-pasted from `.hcKpiNegative` and the CSS variable not updated.

## Proposed Solutions

### Option 1: Delete all three CSS KPI color classes (Recommended if valueColor is preferred)

**Approach:** Remove the 3 CSS rules from `style.css`. The `valueColor` binding approach in Home.view.xml is the correct Fiori pattern and handles the same coloring without custom CSS.

```css
/* DELETE these three rules: */
.hcKpiPositive .sapMNCSValue { color: var(--sapPositiveColor); }
.hcKpiNegative .sapMNCSValue { color: var(--sapNegativeColor); }
.hcKpiCritical .sapMNCSValue { color: var(--sapNegativeColor); } /* also buggy */
```

**Pros:** Cleaner CSS; eliminates dead code; eliminates the potential conflict with `valueColor`; no wrong color token in the codebase
**Cons:** If any view outside of the review scope uses these classes (unlikely but check), it would lose styling
**Effort:** 5 minutes
**Risk:** Very Low (classes verified as unattached)

---

### Option 2: Fix the token and document classes for future use

**Approach:**
```css
/* Fix .hcKpiCritical token: */
.hcKpiCritical .sapMNCSValue { color: var(--sapCriticalColor); } /* was sapNegativeColor — FIXED */
```

Add a CSS comment documenting when to use these classes vs. `valueColor`:
```css
/*
 * KPI color classes: use only when valueColor binding is unavailable.
 * Prefer valueColor="{expr}" on NumericContent for Fiori compliance.
 */
```

**Pros:** Preserves the option to use CSS classes; fixes the actual bug
**Cons:** Dead CSS persists; conflict risk if both approaches are used simultaneously
**Effort:** 5 minutes
**Risk:** Very Low

---

### Option 3: Remove classes AND add explicit valueColor binding documentation

**Approach:** Same as Option 1 plus add an i18n comment in the view explaining the pattern.

**Pros:** Eliminates confusion for new developers
**Cons:** Adds comment that may be overlooked; same effort as Option 1
**Effort:** 10 minutes

## Recommended Action

Apply **Option 1** — delete the three unused CSS rules. The `valueColor` binding is the correct idiomatic UI5/Fiori pattern and is already in use. Carrying dead CSS with a token bug is a risk; cleaning it out is zero-regression.

**Before deleting:** Run a global search for `hcKpiPositive`, `hcKpiNegative`, `hcKpiCritical` across all files to confirm no view or controller references these class names.

## Technical Details

**Affected files:**
- `webapp/css/style.css` — remove 3 CSS rules (lines with `.hcKpiPositive`, `.hcKpiNegative`, `.hcKpiCritical`)

**Token reference (for documentation):**
- `--sapPositiveColor` → `#107E3E` (green) — use for positive P&L, active status
- `--sapNegativeColor` → `#BB0000` (red) — use for negative P&L, error status
- `--sapCriticalColor` → `#E9730C` (orange/amber) — use for critical/warning state
- These tokens are defined by sap_horizon theme; always use tokens, never hardcode hex values

**`valueColor` enum values (the preferred approach):**
- `sap.m.ValueColor.Good` → green
- `sap.m.ValueColor.Critical` → orange
- `sap.m.ValueColor.Error` → red
- `sap.m.ValueColor.Neutral` → grey (default)

**Database changes:** No

## Acceptance Criteria

- [ ] `style.css` contains no reference to `.hcKpiPositive`, `.hcKpiNegative`, or `.hcKpiCritical`
- [ ] OR: If kept, `.hcKpiCritical` uses `var(--sapCriticalColor)` not `var(--sapNegativeColor)`
- [ ] Global search confirms no XML view applies any of the 3 KPI CSS classes
- [ ] Home dashboard KPI tiles retain correct colors via `valueColor` binding
- [ ] No visual regression on KPI tiles in any color state (positive, negative, neutral)

## Work Log

### 2025-01-31 - Discovered in architecture review

**By:** architecture-strategist agent

**Actions:**
- Confirmed `.hcKpiCritical` maps to `var(--sapNegativeColor)` via source read of `style.css`
- Confirmed no XML view applies any of the 3 CSS classes via grep
- Confirmed `Home.view.xml` uses `valueColor` binding approach instead
- Rated P3: Wrong color token (visual bug if activated); dead code; low urgency since classes never applied
