sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/cashflowAnalyticService",
  "hedgecontrol/service/cashflowBaselineSnapshotsService",
  "hedgecontrol/service/cashflowLedgerService",
  "sap/m/MessageBox",
  "sap/m/MessageToast"
], function (BaseController, analyticService, baselineService, ledgerService, MessageBox, MessageToast) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.Cashflow", {

    onInit: function () {
      this.initViewModel("cf", {
        analytic: { cashflow_items: [], total_net_cashflow: 0 },
        analyticBusy: false,
        baseline: {},
        baselineLoaded: false,
        baselineError: "",
        ledger: { entries: [] },
        ledgerBusy: false
      });
      this.getRouter().getRoute("cashflow").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      // Reset state on navigation
    },

    onLoadAnalytic: function () {
      var sDate = this.byId("analyticDate").getValue();
      if (!sDate) {
        MessageBox.warning(this.getI18nText("dateRequired"));
        return;
      }
      var oModel = this.getViewModel();
      oModel.setProperty("/analyticBusy", true);
      analyticService.get(sDate).then(function (oData) {
        oModel.setProperty("/analytic", oData);
      }).catch(function (oError) {
        MessageBox.error(this._formatError(oError));
      }.bind(this)).finally(function () {
        oModel.setProperty("/analyticBusy", false);
      });
    },

    onLoadBaseline: function () {
      var sDate = this.byId("baselineDate").getValue();
      if (!sDate) {
        MessageBox.warning(this.getI18nText("dateRequired"));
        return;
      }
      var oModel = this.getViewModel();
      oModel.setProperty("/baselineError", "");
      oModel.setProperty("/busy", true);
      baselineService.get(sDate).then(function (oData) {
        oModel.setProperty("/baseline", oData);
        oModel.setProperty("/baselineLoaded", true);
      }).catch(function (oError) {
        oModel.setProperty("/baselineError", this._formatError(oError));
        oModel.setProperty("/baselineLoaded", false);
      }.bind(this)).finally(function () {
        oModel.setProperty("/busy", false);
      });
    },

    onCreateBaseline: function () {
      var sDate = this.byId("baselineDate").getValue();
      if (!sDate) {
        MessageBox.warning(this.getI18nText("dateRequired"));
        return;
      }
      var that = this;
      var oPayload = {
        as_of_date: sDate,
        correlation_id: "ui-" + Date.now()
      };
      baselineService.create(oPayload).then(function (oData) {
        MessageToast.show(that.getI18nText("snapshotCreated"));
        that.getViewModel().setProperty("/baseline", oData);
        that.getViewModel().setProperty("/baselineLoaded", true);
      }).catch(function (oError) {
        MessageBox.error(that._formatError(oError));
      });
    },

    onLoadLedger: function () {
      var sContractId = this.byId("ledgerContractId").getValue().trim();
      if (!sContractId) {
        MessageBox.warning(this.getI18nText("contractIdRequired"));
        return;
      }
      var sStart = this.byId("ledgerStart").getValue();
      var sEnd = this.byId("ledgerEnd").getValue();

      var oModel = this.getViewModel();
      oModel.setProperty("/ledgerBusy", true);
      ledgerService.listForContract(sContractId, sStart, sEnd).then(function (oData) {
        oModel.setProperty("/ledger/entries", Array.isArray(oData) ? oData : (oData.items || []));
      }).catch(function (oError) {
        MessageBox.error(this._formatError(oError));
      }.bind(this)).finally(function () {
        oModel.setProperty("/ledgerBusy", false);
      });
    },

    onTabSelect: function () {
      // Tab change handler — no action needed
    },

    formatDirectionState: function (sDirection) {
      if (sDirection === "IN") { return "Success"; }
      if (sDirection === "OUT") { return "Error"; }
      return "None";
    },

    hasValue: function (sVal) {
      return !!sVal;
    }
  });
});
