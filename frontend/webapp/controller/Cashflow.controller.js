sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/cashflowAnalyticService",
  "hedgecontrol/service/cashflowBaselineSnapshotsService",
  "hedgecontrol/service/cashflowLedgerService",
  "hedgecontrol/service/cashflowProjectionService",
  "sap/m/MessageBox",
  "sap/m/MessageToast"
], function (BaseController, analyticService, baselineService, ledgerService, projectionService, MessageBox, MessageToast) {
  "use strict";

  var INSTRUMENT_LABELS = {
    sales_order: "instrSalesOrder",
    purchase_order: "instrPurchaseOrder",
    hedge_buy: "instrHedgeBuy",
    hedge_sell: "instrHedgeSell",
    hedge_contract: "instrHedgeContract"
  };

  var PRICE_SOURCE_LABELS = {
    fixed: "priceSourceFixed",
    market: "priceSourceMarket",
    entry: "priceSourceEntry"
  };

  return BaseController.extend("hedgecontrol.controller.Cashflow", {

    onInit: function () {
      this.initViewModel("cf", {
        analytic: { cashflow_items: [], total_net_cashflow: 0 },
        analyticBusy: false,
        baseline: {},
        baselineLoaded: false,
        baselineError: "",
        ledger: { entries: [] },
        ledgerBusy: false,
        projection: { items: [], summary: { total_inflows: 0, total_outflows: 0, net_cashflow: 0, instrument_count: 0 } },
        projectionBusy: false,
        projectionLoaded: false
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

    onLoadProjection: function () {
      var sDate = this.byId("projectionDate").getValue();
      if (!sDate) {
        MessageBox.warning(this.getI18nText("dateRequired"));
        return;
      }
      var oModel = this.getViewModel();
      oModel.setProperty("/projectionBusy", true);
      oModel.setProperty("/projectionLoaded", false);
      projectionService.get(sDate).then(function (oData) {
        oModel.setProperty("/projection", oData);
        oModel.setProperty("/projectionLoaded", true);
      }).catch(function (oError) {
        MessageBox.error(this._formatError(oError));
      }.bind(this)).finally(function () {
        oModel.setProperty("/projectionBusy", false);
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

    formatInstrumentType: function (sType) {
      var sKey = INSTRUMENT_LABELS[sType];
      return sKey ? this.getI18nText(sKey) : sType;
    },

    formatPriceSource: function (sSource) {
      var sKey = PRICE_SOURCE_LABELS[sSource];
      return sKey ? this.getI18nText(sKey) : sSource;
    },

    formatAmountState: function (fAmount) {
      if (fAmount > 0) { return "Success"; }
      if (fAmount < 0) { return "Error"; }
      return "None";
    },

    formatAmountHighlight: function (fAmount) {
      if (fAmount > 0) { return "Success"; }
      if (fAmount < 0) { return "Error"; }
      return "None";
    },

    hasValue: function (sVal) {
      return !!sVal;
    }
  });
});
