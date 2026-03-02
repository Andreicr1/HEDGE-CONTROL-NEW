sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/plService",
  "sap/m/MessageBox",
  "sap/m/MessageToast"
], function (BaseController, plService, MessageBox, MessageToast) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.Pnl", {

    onInit: function () {
      this.initViewModel("pl", {
        entityType: "hedge_contract",
        entityId: "",
        result: {},
        resultLoaded: false,
        snapEntityType: "hedge_contract",
        snapEntityId: "",
        snapshot: {},
        snapLoaded: false
      });
      this.getRouter().getRoute("pnl").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      // Reset on navigation
    },

    onCalculatePl: function () {
      var oModel = this.getViewModel();
      var sEntityType = oModel.getProperty("/entityType");
      var sEntityId = oModel.getProperty("/entityId").trim();
      var sPeriodStart = this.byId("plStart").getValue();
      var sPeriodEnd = this.byId("plEnd").getValue();

      if (!sEntityId) {
        MessageBox.warning(this.getI18nText("entityIdRequired"));
        return;
      }

      oModel.setProperty("/busy", true);
      plService.getPl(sEntityType, sEntityId, sPeriodStart, sPeriodEnd).then(function (oData) {
        oModel.setProperty("/result", oData);
        oModel.setProperty("/resultLoaded", true);
      }).catch(function (oError) {
        MessageBox.error(this._formatError(oError));
        oModel.setProperty("/resultLoaded", false);
      }.bind(this)).finally(function () {
        oModel.setProperty("/busy", false);
      });
    },

    onCreatePlSnapshot: function () {
      var oModel = this.getViewModel();
      var sEntityType = oModel.getProperty("/entityType");
      var sEntityId = oModel.getProperty("/entityId").trim();
      var sPeriodStart = this.byId("plStart").getValue();
      var sPeriodEnd = this.byId("plEnd").getValue();

      if (!sEntityId || !sPeriodStart || !sPeriodEnd) {
        MessageBox.warning(this.getI18nText("allFieldsRequired"));
        return;
      }

      var oPayload = {
        entity_type: sEntityType,
        entity_id: sEntityId,
        period_start: sPeriodStart,
        period_end: sPeriodEnd
      };

      var that = this;
      plService.createSnapshot(oPayload).then(function (oData) {
        MessageToast.show(that.getI18nText("snapshotCreated"));
        oModel.setProperty("/snapshot", oData);
        oModel.setProperty("/snapLoaded", true);
      }).catch(function (oError) {
        MessageBox.error(that._formatError(oError));
      });
    },

    onLoadSnapshot: function () {
      var oModel = this.getViewModel();
      var sEntityType = oModel.getProperty("/snapEntityType");
      var sEntityId = oModel.getProperty("/snapEntityId").trim();
      var sPeriodStart = this.byId("snapStart").getValue();
      var sPeriodEnd = this.byId("snapEnd").getValue();

      if (!sEntityId) {
        MessageBox.warning(this.getI18nText("entityIdRequired"));
        return;
      }

      oModel.setProperty("/busy", true);
      plService.getSnapshot(sEntityType, sEntityId, sPeriodStart, sPeriodEnd).then(function (oData) {
        oModel.setProperty("/snapshot", oData);
        oModel.setProperty("/snapLoaded", true);
      }).catch(function (oError) {
        MessageBox.error(this._formatError(oError));
        oModel.setProperty("/snapLoaded", false);
      }.bind(this)).finally(function () {
        oModel.setProperty("/busy", false);
      });
    },

    formatPlState: function (fValue) {
      if (fValue === undefined || fValue === null) { return "None"; }
      var n = parseFloat(fValue);
      if (n > 0) { return "Success"; }
      if (n < 0) { return "Error"; }
      return "None";
    }
  });
});
