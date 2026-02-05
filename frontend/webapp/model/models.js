sap.ui.define([
  "sap/ui/model/json/JSONModel"
], function (JSONModel) {
  "use strict";

  return {
    createAppModel: function () {
      return new JSONModel({
        layout: {
          title: "Hedge Control Platform",
          badge: "Admin read-only (no auth configured)"
        },
        blocked: {
          exposures: {
            title: "Exposures",
            description: "Read-only exposure views require explicit F3 authorization.",
            blockers: [
              "F3 not yet authorized",
              "OpenAPI exposures endpoints must remain authoritative",
              "No client-side exposure inference allowed"
            ]
          },
          orders: {
            title: "Orders",
            description: "Order creation and lookup remain gated until Phase F4.",
            blockers: [
              "F4 not yet authorized",
              "Worklists blocked by Backend B1"
            ]
          },
          rfq: {
            title: "RFQ",
            description: "RFQ core flows remain gated until Phase F5.",
            blockers: [
              "F5 not yet authorized",
              "Worklist blocked by Backend B1",
              "Send/evidence blocked by Backend B2"
            ]
          },
          contracts: {
            title: "Contracts",
            description: "Contract and linkage flows are gated to Phase F6.",
            blockers: [
              "F6 not yet authorized",
              "Worklists blocked by Backend B1"
            ]
          },
          cashflow: {
            title: "Cashflow",
            description: "Cashflow, ledger, and settlement flows are gated to Phase F7.",
            blockers: ["F7 not yet authorized"]
          },
          pnl: {
            title: "P&L",
            description: "P&L computations are gated to Phase F7.",
            blockers: ["F7 not yet authorized"]
          },
          scenario: {
            title: "Scenario",
            description: "What-if scenario execution is gated to Phase F8.",
            blockers: ["F8 not yet authorized"]
          },
          notFound: {
            title: "Not Found",
            description: "The requested page does not exist.",
            blockers: []
          }
        },
        nav: [
          { key: "home", label: "Overview", route: "home" },
          { key: "observability", label: "Observability", route: "observability" },
          { key: "audit", label: "Audit", route: "audit" },
          { key: "exposures", label: "Exposures", route: "exposures" },
          { key: "orders", label: "Orders", route: "orders" },
          { key: "rfq", label: "RFQ", route: "rfq" },
          { key: "contracts", label: "Contracts", route: "contracts" },
          { key: "cashflow", label: "Cashflow", route: "cashflow" },
          { key: "pnl", label: "P&L", route: "pnl" },
          { key: "scenario", label: "Scenario", route: "scenario" }
        ]
      });
    }
  };
});