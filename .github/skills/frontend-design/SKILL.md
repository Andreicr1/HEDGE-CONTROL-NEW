---
name: frontend-design
description: This skill should be used when creating production-grade SAP UI5 frontend interfaces following the Fiori design system. It applies when the user asks to build UI5 views, XML fragments, controllers, or components for this application. Generates correct, idiomatic SAP UI5 code using XML views, sap_horizon theme tokens, and established app patterns.
license: Complete terms in LICENSE.txt
---

This skill guides creation of production-grade SAP UI5 (Fiori) frontend code for the **Hedge Control** application. The design system is **SAP Fiori / sap_horizon** — all UI is expressed as XML views, JS controllers, and SAP CSS token overrides. Never generate plain HTML, React, CSS frameworks (Bootstrap, Tailwind), or custom fonts.

The user provides a frontend requirement: a new view, fragment, controller, or enhancement to an existing screen.

## Technology Stack

| Layer | Technology |
|---|---|
| Framework | SAP UI5 ≥ 1.136.0 |
| Theme | `sap_horizon` |
| View format | XML views (`.view.xml`) |
| Controller format | AMD-style JS (`.controller.js`) |
| Fragments | XML fragments (`.fragment.xml`) |
| Routing | `sap.f.routing.Router` + Flexible Column Layout |
| App shell | `sap.tnt.ToolPage` + `sap.f.ShellBar` |
| Styling | `css/style.css` — SAP CSS token overrides only |
| i18n | `i18n/i18n.properties` — all user-visible text |
| Formatters | `hedgecontrol/util/formatter` |

## Codebase Conventions

### File Locations
- Views: `frontend/webapp/view/<Name>.view.xml`
- Controllers: `frontend/webapp/controller/<Name>.controller.js`
- Fragments: `frontend/webapp/view/fragment/<Name>.fragment.xml`
- Services: `frontend/webapp/service/<name>Service.js`
- CSS additions: `frontend/webapp/css/style.css`
- i18n keys: `frontend/webapp/i18n/i18n.properties`

### XML View Skeleton
Every view must follow this pattern:
```xml
<mvc:View
  controllerName="hedgecontrol.controller.<Name>"
  xmlns:mvc="sap.ui.core.mvc"
  xmlns="sap.m"
  xmlns:f="sap.f"
  xmlns:core="sap.ui.core"
  core:require="{ formatter: 'hedgecontrol/util/formatter' }">
  <!-- content -->
</mvc:View>
```

Include only namespaces actually used in the view:
- `xmlns:layout="sap.ui.layout"` — Grid
- `xmlns:form="sap.ui.layout.form"` — Form / ColumnLayout
- `xmlns:uxap="sap.uxap"` — ObjectPageLayout
- `xmlns:tnt="sap.tnt"` — ToolPage / SideNavigation

### Controller Skeleton
```js
sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/someService"
], function (BaseController, someService) {
  "use strict";
  return BaseController.extend("hedgecontrol.controller.<Name>", {
    onInit: function () {
      this.initViewModel("<modelPrefix>", { busy: false });
      this.getRouter().getRoute("<routeName>").attachPatternMatched(this._onRouteMatched, this);
    },
    _onRouteMatched: function () { /* load data */ }
  });
});
```

Always extend `hedgecontrol/controller/BaseController`. Never extend `sap.ui.core.mvc.Controller` directly.

## Layout Patterns

### List View (DynamicPage + List)
Use for entity list screens (Orders, Contracts, Exposures…):
```xml
<f:DynamicPage id="<entity>ListPage" headerExpanded="true" showFooter="false" busy="{vm>/busy}">
  <f:title>
    <f:DynamicPageTitle>
      <f:heading><Title text="{i18n>...}" /></f:heading>
      <f:actions>
        <Button text="{i18n>new...}" icon="sap-icon://add" type="Emphasized" press=".onCreate" />
      </f:actions>
    </f:DynamicPageTitle>
  </f:title>
  <f:header>
    <f:DynamicPageHeader>
      <HBox alignItems="Center">
        <SearchField width="20rem" liveChange=".onSearch" placeholder="{i18n>search...}" />
      </HBox>
    </f:DynamicPageHeader>
  </f:header>
  <f:content>
    <List id="<entity>List" items="{vm>/items}" growing="true" growingThreshold="50"
          mode="SingleSelectMaster" itemPress=".onItemSelect" noDataText="{i18n>noData}">
      <items>
        <ObjectListItem title="..." type="Navigation">
          <attributes>
            <ObjectAttribute text="..." />
          </attributes>
          <firstStatus>
            <ObjectStatus text="{path: 'vm>status', formatter: 'formatter.capitalize'}"
              state="{path: 'vm>status', formatter: 'formatter.statusState'}" />
          </firstStatus>
        </ObjectListItem>
      </items>
    </List>
  </f:content>
</f:DynamicPage>
```

### Detail View (ObjectPageLayout)
Use for entity detail screens:
```xml
<uxap:ObjectPageLayout id="<entity>DetailPage" busy="{vm>/busy}" showTitleInHeaderContent="true">
  <uxap:headerTitle>
    <uxap:ObjectPageDynamicHeaderTitle>
      <uxap:heading>
        <HBox alignItems="Center">
          <Title text="{vm>/reference}" class="sapUiSmallMarginEnd" />
          <ObjectStatus text="{vm>/status}" state="{path: 'vm>/status', formatter: 'formatter.statusState'}" />
        </HBox>
      </uxap:heading>
      <uxap:actions>
        <Button text="{i18n>action}" type="Emphasized" press=".onAction" />
        <Button text="{i18n>close}" type="Default" press=".onClose" />
      </uxap:actions>
    </uxap:ObjectPageDynamicHeaderTitle>
  </uxap:headerTitle>
  <uxap:headerContent>
    <HBox>
      <VBox class="sapUiSmallMarginEnd">
        <Label text="{i18n>field}" />
        <Text text="{vm>/field}" />
      </VBox>
    </HBox>
  </uxap:headerContent>
  <uxap:sections>
    <uxap:ObjectPageSection title="{i18n>sectionTitle}">
      <uxap:subSections>
        <uxap:ObjectPageSubSection>
          <uxap:blocks>
            <form:Form editable="false">
              <form:layout>
                <form:ColumnLayout columnsM="2" columnsL="2" columnsXL="2" />
              </form:layout>
              <form:formContainers>
                <form:FormContainer title="{i18n>groupTitle}">
                  <form:formElements>
                    <form:FormElement label="{i18n>fieldLabel}">
                      <Text text="{vm>/fieldValue}" />
                    </form:FormElement>
                  </form:formElements>
                </form:FormContainer>
              </form:formContainers>
            </form:Form>
          </uxap:blocks>
        </uxap:ObjectPageSubSection>
      </uxap:subSections>
    </uxap:ObjectPageSection>
  </uxap:sections>
</uxap:ObjectPageLayout>
```

### Create / Edit View (DynamicPage + Form + Footer)
Use `showFooter="true"` and place Save/Cancel in `f:footer`:
```xml
<f:DynamicPage id="<entity>CreatePage" showFooter="true" busy="{vm>/busy}">
  <f:title>
    <f:DynamicPageTitle>
      <f:heading><Title text="{vm>/pageTitle}" /></f:heading>
    </f:DynamicPageTitle>
  </f:title>
  <f:content>
    <VBox class="sapUiSmallMargin">
      <MessageStrip text="{vm>/errorMessage}" type="Error" showIcon="true"
        visible="{= !!${vm>/errorMessage}}" class="sapUiSmallMarginBottom" />
      <form:Form id="createForm" editable="true">
        <form:layout>
          <form:ColumnLayout columnsM="1" columnsL="2" columnsXL="2" />
        </form:layout>
        <form:formContainers>
          <form:FormContainer title="{i18n>sectionTitle}">
            <form:formElements>
              <form:FormElement label="{i18n>fieldLabel}">
                <form:fields>
                  <Input value="{vm>/form/fieldName}" />
                </form:fields>
              </form:FormElement>
            </form:formElements>
          </form:FormContainer>
        </form:formContainers>
      </form:Form>
    </VBox>
  </f:content>
  <f:footer>
    <OverflowToolbar>
      <ToolbarSpacer />
      <Button text="{i18n>save}" type="Emphasized" press=".onSave" enabled="{= !${vm>/busy}}" />
      <Button text="{i18n>cancel}" type="Default" press=".onCancel" />
    </OverflowToolbar>
  </f:footer>
</f:DynamicPage>
```

## BaseController API — Always Available

| Method | Purpose |
|---|---|
| `this.initViewModel(name, data)` | Create JSONModel on view, sets `_sModelName` |
| `this.getViewModel()` | Return the view's JSONModel |
| `this.getAppModel()` | Return the shared `app` model |
| `this.getRouter()` | Return `sap.f.routing.Router` |
| `this.getI18nText(key, args)` | Translate via resource bundle |
| `this.setLayout(sLayout)` | Change FCL layout (e.g. `"TwoColumnsMidExpanded"`) |
| `this._formatError(oError)` | Format error for `MessageBox`/`MessageStrip` |

## Model & Binding Conventions

- Each view gets its own JSONModel, named with a short prefix: `ctr`, `ord`, `exp`, etc.
- Binding paths prefix with the model name: `{ctr>/items}`, `{ordCrt>/form/deal_id}`
- Global state lives in the `app` JSONModel (layout, userInitials, notificationsCount)
- Always set `busy: false` and `errorMessage: ""` as defaults in `initViewModel`
- Use `oModel.setSizeLimit(5000)` for list models

## Formatting & State

Use `hedgecontrol/util/formatter` via `core:require`:
```xml
core:require="{ formatter: 'hedgecontrol/util/formatter' }"
```
Available formatters: `formatter.capitalize`, `formatter.statusState`, `formatter.classificationText`,
`formatter.classificationState`, `formatter.numberTwoDecimals`, `formatter.priceFourDecimals`,
`formatter.dateDisplay`.

State values for `ObjectStatus`/`ObjectNumber`: `"Success"`, `"Warning"`, `"Error"`, `"Information"`, `"None"`.

## Icons

Use only `sap-icon://` icons. Common icons used in this app:
`add`, `product`, `sales-order`, `request`, `document`, `money-bills`, `line-chart`,
`customer-and-supplier`, `decline`, `delete`, `sys-help`, `home`, `document-text`.

## CSS / Styling Rules

- **Only** add styles to `css/style.css`
- **Only** use SAP CSS tokens: `var(--sapXxx)` (e.g. `var(--sapNeutralBackground)`, `var(--sapContent_ForegroundBorderColor)`, `var(--sapContent_Space_M)`)
- **Never** use custom fonts, `@font-face`, animations, gradients, or external CSS libraries
- Use SAP margin/padding utility classes: `sapUiSmallMargin`, `sapUiSmallMarginEnd`, `sapUiSmallMarginTop`, `sapUiSmallMarginBottom`, `sapUiMediumMargin`
- Target SAP-generated class names for overrides (e.g. `.sapMTable .sapMListTblCell`)

## i18n Rules

- Every user-visible string must be defined in `i18n/i18n.properties` and referenced as `{i18n>key}`
- Never hard-code strings in XML views or controllers
- When adding new keys, follow existing naming: `entityAction` (e.g. `contractsTitle`, `newHedgeContract`, `noContracts`)

## Navigation / Routing

FCL layout strings: `"OneColumn"`, `"TwoColumnsMidExpanded"`, `"TwoColumnsBeginExpanded"`, `"ThreeColumnsMidExpanded"`, `"MidColumnFullScreen"`.

Route pattern from `manifest.json` — always attach via `this.getRouter().getRoute("<name>").attachPatternMatched(...)` in `onInit`.

## Error Handling Pattern

In controllers, always use this pattern:
```js
someService.list().then(function (oResponse) {
  oModel.setProperty("/items", oResponse.items || []);
}).catch(function (oError) {
  oModel.setProperty("/errorMessage", this._formatError(oError));
}.bind(this)).finally(function () {
  oModel.setProperty("/busy", false);
});
```

Show errors inline via `MessageStrip` (forms) or `MessageBox.error(...)` (critical/destructive actions).

## Checklist Before Generating Code

1. Is the view XML and stored in the right folder?
2. Does the controller extend `BaseController`?
3. Are all strings in i18n?
4. Are icons `sap-icon://` only?
5. Is the model initialized with `initViewModel`?
6. Does the layout match the screen type (list / detail / create)?
7. Is `busy` binding wired to the page/container?
8. Are new CSS rules using only `var(--sapXxx)` tokens?
9. Is routing attached in `onInit`?
10. Are errors handled with `_formatError` + `MessageStrip` or `MessageBox`?
