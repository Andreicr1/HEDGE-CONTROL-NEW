---
title: "Heal frontend-design skill: replace generic HTML/CSS/React guidance with SAP UI5 / Fiori patterns"
date: 2026-03-09
category: skill-maintenance
tags:
  - sap-ui5
  - fiori
  - skill
  - frontend-design
  - xml-views
  - sap_horizon
  - agent-skill
symptoms:
  - "Skill generated HTML/CSS/React code instead of XML views and UI5 controls"
  - "Gradient meshes, custom fonts, and CSS animations suggested despite being incompatible with UI5"
  - "No guidance for BaseController, i18n bundles, JSONModel binding, or Fiori routing"
  - "Generated code would never render correctly inside a UI5 application shell"
problem_type: skill-domain-mismatch
component: .github/skills/frontend-design
severity: high
resolution_time: 30m
---

# Heal frontend-design skill for SAP UI5 / Fiori

## Problem

The `frontend-design` skill (`.github/skills/frontend-design/SKILL.md`) was a generic web-development template that had never been adapted to the actual repository technology stack.

When AI agents invoked the skill to generate frontend code for the Hedge Control application, they produced:

- Plain HTML files and React components instead of SAP UI5 XML views
- `import React from 'react'` / JSX instead of `sap.ui.define([ ... ])` AMD modules
- Custom fonts, `@keyframes` animations, gradient meshes, and Tailwind/Bootstrap patterns instead of `var(--sapXxx)` design token variables
- Creative web aesthetic direction (brutalism, maximalism, retro-futurism) instead of Fiori design-language compliance

None of this output was usable inside the `sap.tnt.ToolPage` / `sap.f.FlexibleColumnLayout` application shell.

## Root Cause

The `frontend-design` skill was a generic template sourced outside the context of this repository. Its description field said _"creates distinctive, production-grade frontend interfaces"_ without naming any specific framework or design system. This caused the agent to interpret the skill as applicable to any web frontend task, including SAP UI5 work.

The mismatch was total — the old skill had zero salvageable content for a UI5 codebase.

## What Was Changed

The entire contents of `.github/skills/frontend-design/SKILL.md` were replaced. Key sections added:

### 1. Technology Stack Declaration Table

An explicit reference table anchors all generated code to the stack:

| Layer | Technology |
|---|---|
| Framework | SAP UI5 ≥ 1.136.0 |
| Theme | `sap_horizon` |
| View format | XML views (`.view.xml`) |
| App shell | `sap.tnt.ToolPage` + `sap.f.ShellBar` |
| Routing | `sap.f.routing.Router` + FCL |
| Detail pages | `sap.uxap.ObjectPageLayout` |
| Styling | `css/style.css` — SAP CSS token overrides only |
| Strings | `i18n/i18n.properties` — ALL user-visible text |

### 2. File Location Conventions

```
webapp/view/         → XML views        (.view.xml)
webapp/controller/   → JS controllers   (.controller.js)
webapp/view/fragment → XML fragments    (.fragment.xml)
webapp/service/      → service modules
webapp/i18n/         → i18n.properties
webapp/css/          → style.css
```

### 3. XML View Skeletons for All 3 Screen Types

**List view** (`sap.f.DynamicPage` + `sap.m.List` + `ObjectListItem`):
```xml
<mvc:View controllerName="hedgecontrol.controller.Name"
  xmlns:mvc="sap.ui.core.mvc" xmlns="sap.m" xmlns:f="sap.f"
  core:require="{ formatter: 'hedgecontrol/util/formatter' }">
  <f:DynamicPage id="listPage" showFooter="false" busy="{vm>/busy}">
    <f:title>
      <f:DynamicPageTitle>
        <f:heading><Title text="{i18n>title}"/></f:heading>
        <f:actions>
          <Button text="{i18n>create}" icon="sap-icon://add" type="Emphasized" press=".onCreate"/>
        </f:actions>
      </f:DynamicPageTitle>
    </f:title>
    <f:content>
      <List items="{vm>/items}" growing="true" growingThreshold="50"
            mode="SingleSelectMaster" itemPress=".onSelect">
        <ObjectListItem title="{vm>field}" type="Navigation">
          <firstStatus>
            <ObjectStatus text="{path:'vm>status', formatter:'formatter.capitalize'}"
              state="{path:'vm>status', formatter:'formatter.statusState'}"/>
          </firstStatus>
        </ObjectListItem>
      </List>
    </f:content>
  </f:DynamicPage>
</mvc:View>
```

**Detail view** (`sap.uxap.ObjectPageLayout` with sections and `form:Form`):
Uses `uxap:ObjectPageDynamicHeaderTitle`, `uxap:ObjectPageSection`, `form:ColumnLayout columnsL="2"`.

**Create/Edit view** (`sap.f.DynamicPage` with `showFooter="true"`, `MessageStrip` for errors, `OverflowToolbar` Save/Cancel footer).

### 4. Controller Skeleton

Always extend `hedgecontrol/controller/BaseController` — never `sap.ui.core.mvc.Controller` directly:

```js
sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/someService"
], function (BaseController, someService) {
  "use strict";
  return BaseController.extend("hedgecontrol.controller.Name", {
    onInit: function () {
      this.initViewModel("vm", { busy: false, errorMessage: "" });
      this.getRouter().getRoute("routeName").attachPatternMatched(this._onRouteMatched, this);
    }
  });
});
```

### 5. BaseController API Reference

| Method | Purpose |
|---|---|
| `initViewModel(name, data)` | Create JSONModel on view |
| `getViewModel()` | Return the view's JSONModel |
| `getAppModel()` | Return shared `app` model |
| `getRouter()` | Return `sap.f.routing.Router` |
| `getI18nText(key, args)` | Translate via resource bundle |
| `setLayout(sLayout)` | Change FCL layout |
| `_formatError(oError)` | Format error for display |

### 6. Model/Binding Conventions

- Each view has its own named JSONModel with a short prefix: `ctr`, `ord`, `exp`, `vm`
- Bindings always include the model prefix: `{ctr>/items}`, `{ordCrt>/form/deal_id}`
- Always include `busy: false, errorMessage: ""` in `initViewModel` defaults
- Use `oModel.setSizeLimit(5000)` for list models

### 7. CSS/Styling Rules

- **Allowed**: `var(--sapXxx)` design token variables only
- **Forbidden**: custom fonts, `@font-face`, `@keyframes`, gradient meshes, hardcoded color hex values, CSS frameworks

### 8. i18n Rules

All user-visible strings live in `i18n/i18n.properties`. Never hard-code strings in XML or JS.

### 9. Error Handling Pattern

```js
someService.list().then(function (res) {
  oModel.setProperty("/items", res.items || []);
}).catch(function (err) {
  oModel.setProperty("/errorMessage", this._formatError(err));
}.bind(this)).finally(function () {
  oModel.setProperty("/busy", false);
});
```

Show errors via `MessageStrip` (form screens) or `MessageBox.error(...)` (destructive actions).

### 10. Pre-Generation Checklist

Added a 10-point final checklist covering: view in correct folder, controller extends BaseController, strings in i18n, icons use `sap-icon://`, model initialized, layout matches screen type, busy binding wired, CSS uses only `var(--sapXxx)`, routing attached in `onInit`, errors handled correctly.

---

## Prevention

### 1. Early Detection — Signs a Skill Is Out of Sync

- Generated files have wrong extensions (`.html`, `.jsx` in a `.xml` view codebase)
- Imports reference libraries absent from `package.json` (`react`, `tailwindcss`, `bootstrap`)
- CSS uses hardcoded hex values or custom font declarations
- Skill description mentions a framework that contradicts the actual stack
- Skill was imported from a generic template (not authored against the repo)
- `AGENTS.md` references the skill but contains no framework constraints

### 2. Process Recommendations

- `AGENTS.md` must explicitly list the design system and framework — all agent invocations load it as constraint context
- Skill `description` fields must name the specific framework (not just "frontend"), enabling precise routing
- When onboarding a generic/external skill, audit its `SKILL.md` against `package.json`, `ui5.yaml`, and framework config files before committing
- Version `SKILL.md` files alongside `package.json` — a framework major-version bump should trigger a skill review
- Consider a CI lint step that greps skill descriptions for forbidden framework keywords (`react`, `tailwind`, `bootstrap`) relative to the stack

### 3. Checklist for New Frontend Skill Creation

- [ ] Skill `description` explicitly names the framework and design system
- [ ] `SKILL.md` references real files from the repo (actual XML view paths, actual controller files)
- [ ] Skill does NOT reference any library absent from `package.json`/`ui5.yaml`
- [ ] Generated skeleton was validated through the project build (`ui5 build`) or linter
- [ ] Skill description contains at least one **negative trigger** (what it should NOT be used for)
- [ ] A reviewer familiar with the actual tech stack approved the content
- [ ] `AGENTS.md` was updated to reference the skill with framework constraints listed

### 4. Verification Steps

After creating or healing a skill:

1. **Smoke test** — generate a simple list view and inspect: correct extension (`.xml`), correct namespace (`xmlns="sap.m"`), no non-SAP imports
2. **Build check** — run `ui5 build`; zero errors confirms syntactic validity
3. **Token audit** — grep generated CSS/JS for hardcoded colour values (`#`, `rgb(`); any hit is a regression
4. **Cross-reference `ui5.yaml`** — generated library references must match libraries declared in `ui5.yaml`
5. **Regression test** — use the exact prompt that previously produced HTML/React output; confirm the healed skill no longer generates incompatible code
6. **Peer review** — a human familiar with SAP Fiori patterns signs off before marking the skill stable

---

## Related Documentation

### Existing Solution Files (not UI5-specific)
- [docs/solutions/integration-issues/twilio-brazil-phone-8-9-digit-normalization.md](../integration-issues/twilio-brazil-phone-8-9-digit-normalization.md)
- [docs/solutions/logic-errors/llm-hallucinated-prices-rfq-trivial-message-guard.md](../logic-errors/llm-hallucinated-prices-rfq-trivial-message-guard.md)
- [docs/solutions/security-issues/fastapi-missing-rbac-require-any-role.md](../security-issues/fastapi-missing-rbac-require-any-role.md)

### Frontend Design System Sources
- [frontend/webapp/manifest.json](../../../frontend/webapp/manifest.json) — `sap_horizon` theme, `minUI5Version: 1.136.0`, library list
- [frontend/ui5.yaml](../../../frontend/ui5.yaml) — UI5 Tooling spec, backend proxy paths
- [frontend/webapp/controller/BaseController.js](../../../frontend/webapp/controller/BaseController.js) — shared base controller (authoritative API reference)
- [frontend/webapp/css/style.css](../../../frontend/webapp/css/style.css) — CSS token overrides (reference for allowable styling patterns)

### Platform & Architecture Docs
- [docs/integration-audit.md](../../integration-audit.md) — FastAPI ↔ UI5 endpoint coverage map; ghost endpoints list
- [docs/systemconstitucion.md](../../systemconstitucion.md) — "Frontend is a presenter" architectural rule; zero economic logic in UI layer

### Agent / Skill Cross-References
- [.github/skills/frontend-design/SKILL.md](../../../.github/skills/frontend-design/SKILL.md) — **healed skill** (primary output of this fix)
- [AGENTS.md](../../../AGENTS.md) — mandates `get_guidelines` UI5 MCP tool usage before any UI5 code generation
- `.github/agents/design-iterator.agent.md` — loads `frontend-design` skill automatically; `<frontend_aesthetics>` section still contains generic web guidance → **potential follow-up: also heal `design-iterator` to reference Fiori constraints**
