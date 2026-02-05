sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/model/json/JSONModel",
  "sap/m/MessageBox",
  "hedgecontrol/service/cashflowsService",
  "hedgecontrol/service/cashflowAnalyticService",
  "hedgecontrol/service/cashflowBaselineSnapshotsService",
  "hedgecontrol/service/cashflowLedgerService",
  "hedgecontrol/util/jsonUtil"
], function (
  Controller,
  JSONModel,
  MessageBox,
  cashflowsService,
  cashflowAnalyticService,
  cashflowBaselineSnapshotsService,
  cashflowLedgerService,
  jsonUtil
) {
  "use strict";

  return Controller.extend("hedgecontrol.controller.Cashflow", {
    onInit: function () {
      var model = new JSONModel({
        busy: false,
        cashflowId: "",
        cashflowIdUnderscore: "1",
        cashflowCreateBody: "{}",
        asOfDate: "",
        baselineCreateBody: "{}",
        settleContractId: "",
        settleBody: "{}",
        ledgerSourceEventId: "",
        ledgerSourceEventType: "HEDGE_CONTRACT_SETTLED",
        ledgerContractId: "",
        ledgerStart: "",
        ledgerEnd: "",
        responseText: "",
        errorText: ""
      });
      this.getView().setModel(model, "cashflow");
    },

    onListCashflows: function () {
      this._run(function () {
        return cashflowsService.list();
      });
    },

    onCreateCashflow: function () {
      this._postBody("/cashflowCreateBody", function (payload) {
        return cashflowsService.create(payload);
      });
    },

    onGetCashflow: function () {
      var model = this.getView().getModel("cashflow");
      var cashflowId = (model.getProperty("/cashflowId") || "").trim();
      if (!cashflowId) {
        MessageBox.error("cashflow_id is required");
        return;
      }
      var underscore = (model.getProperty("/cashflowIdUnderscore") || "").trim();
      if (!underscore) {
        MessageBox.error("OpenAPI requires query parameter '_' for /cashflows/{cashflow_id}");
        return;
      }
      this._run(function () {
        return cashflowsService.getById(cashflowId, underscore);
      });
    },

    onGetAnalytic: function () {
      var model = this.getView().getModel("cashflow");
      var asOfDate = (model.getProperty("/asOfDate") || "").trim();
      if (!asOfDate) {
        MessageBox.error("as_of_date is required");
        return;
      }
      this._run(function () {
        return cashflowAnalyticService.get(asOfDate);
      });
    },

    onGetBaselineSnapshot: function () {
      var model = this.getView().getModel("cashflow");
      var asOfDate = (model.getProperty("/asOfDate") || "").trim();
      if (!asOfDate) {
        MessageBox.error("as_of_date is required");
        return;
      }
      this._run(function () {
        return cashflowBaselineSnapshotsService.get(asOfDate);
      });
    },

    onCreateBaselineSnapshot: function () {
      this._postBody("/baselineCreateBody", function (payload) {
        return cashflowBaselineSnapshotsService.create(payload);
      });
    },

    onSettleContract: function () {
      var model = this.getView().getModel("cashflow");
      var contractId = (model.getProperty("/settleContractId") || "").trim();
      if (!contractId) {
        MessageBox.error("contract_id is required");
        return;
      }
      this._postBody("/settleBody", function (payload) {
        return cashflowLedgerService.settleContract(contractId, payload);
      });
    },

    onLedgerByEvent: function () {
      var model = this.getView().getModel("cashflow");
      var sourceEventId = (model.getProperty("/ledgerSourceEventId") || "").trim();
      if (!sourceEventId) {
        MessageBox.error("source_event_id is required");
        return;
      }
      var sourceEventType = (model.getProperty("/ledgerSourceEventType") || "").trim();
      this._run(function () {
        return cashflowLedgerService.listByEvent(sourceEventId, sourceEventType);
      });
    },

    onLedgerForContract: function () {
      var model = this.getView().getModel("cashflow");
      var contractId = (model.getProperty("/ledgerContractId") || "").trim();
      if (!contractId) {
        MessageBox.error("contract_id is required");
        return;
      }
      var start = (model.getProperty("/ledgerStart") || "").trim();
      var end = (model.getProperty("/ledgerEnd") || "").trim();
      this._run(function () {
        return cashflowLedgerService.listForContract(contractId, start, end);
      });
    },

    _postBody: function (path, fn) {
      var model = this.getView().getModel("cashflow");
      var bodyText = model.getProperty(path);
      var payload;
      try {
        payload = jsonUtil.parse(bodyText);
      } catch (e) {
        MessageBox.error("Invalid JSON: " + e.message);
        return;
      }
      if (payload === undefined) {
        MessageBox.error("Request body is required");
        return;
      }
      this._run(function () {
        return fn(payload);
      });
    },

    _run: function (fn) {
      var model = this.getView().getModel("cashflow");
      model.setProperty("/busy", true);
      model.setProperty("/errorText", "");
      fn()
        .then(function (payload) {
          model.setProperty("/responseText", jsonUtil.pretty(payload));
        })
        .catch(function (error) {
          var status = error && error.status ? "HTTP " + error.status : "HTTP ?";
          var details = error && error.details !== undefined ? "\n\n" + jsonUtil.pretty(error.details) : "";
          var message = status + ": " + (error && error.message ? error.message : "Request failed") + details;
          model.setProperty("/errorText", message);
          MessageBox.error(message);
        })
        .finally(function () {
          model.setProperty("/busy", false);
        });
    }
  });
});
