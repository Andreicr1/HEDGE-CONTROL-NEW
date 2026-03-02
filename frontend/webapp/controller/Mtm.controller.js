sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "sap/ui/model/json/JSONModel",
  "sap/m/MessageBox",
  "sap/m/MessageToast",
  "hedgecontrol/service/mtmService"
], function (BaseController, JSONModel, MessageBox, MessageToast, mtmService) {
  "use strict";

  function _emptyForm() {
    return {
      objectType: "hedge_contract",
      objectId: "",
      asOfDate: "",
      hasCalcResult: false,
      calcResult: null,
      snapObjectType: "hedge_contract",
      snapObjectId: "",
      snapAsOfDate: "",
      hasSnapResult: false,
      snapResult: null
    };
  }

  return BaseController.extend("hedgecontrol.controller.Mtm", {

    onInit: function () {
      this.initViewModel("mtm", _emptyForm());
      this.getRouter().getRoute("mtm").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this.getViewModel().setData(_emptyForm());
    },

    /* ─── Calculate ─── */

    onCalculate: function () {
      var oModel = this.getViewModel();
      var sType = oModel.getProperty("/objectType");
      var sId = oModel.getProperty("/objectId").trim();
      var sDate = oModel.getProperty("/asOfDate");

      if (!sId || !sDate) {
        MessageBox.warning(this.getI18nText("msgProvideObjectIdDate"));
        return;
      }

      var fnCall = sType === "hedge_contract"
        ? mtmService.getForHedgeContract(sId, sDate)
        : mtmService.getForOrder(sId, sDate);

      var that = this;
      fnCall
        .then(function (oData) {
          oModel.setProperty("/calcResult", oData);
          oModel.setProperty("/hasCalcResult", true);
        })
        .catch(function (err) {
          oModel.setProperty("/hasCalcResult", false);
          MessageBox.error(that._formatError(err));
        });
    },

    /* ─── Snapshots ─── */

    onLoadSnapshot: function () {
      var oModel = this.getViewModel();
      var sType = oModel.getProperty("/snapObjectType");
      var sId = oModel.getProperty("/snapObjectId").trim();
      var sDate = oModel.getProperty("/snapAsOfDate");

      if (!sType || !sId || !sDate) {
        MessageBox.warning(this.getI18nText("msgProvideSnapshotFields"));
        return;
      }

      var that = this;
      mtmService.getSnapshot(sType, sId, sDate)
        .then(function (oData) {
          oModel.setProperty("/snapResult", oData);
          oModel.setProperty("/hasSnapResult", true);
        })
        .catch(function (err) {
          oModel.setProperty("/hasSnapResult", false);
          MessageBox.error(that._formatError(err));
        });
    },

    onCreateSnapshot: function () {
      var oModel = this.getViewModel();
      var sType = oModel.getProperty("/snapObjectType");
      var sId = oModel.getProperty("/snapObjectId").trim();
      var sDate = oModel.getProperty("/snapAsOfDate");

      if (!sType || !sId || !sDate) {
        MessageBox.warning(this.getI18nText("msgProvideAllSnapshotFields"));
        return;
      }

      var oPayload = {
        object_type: sType,
        object_id: sId,
        as_of_date: sDate,
        correlation_id: crypto.randomUUID()
      };

      var that = this;
      mtmService.createSnapshot(oPayload)
        .then(function (oData) {
          oModel.setProperty("/snapResult", oData);
          oModel.setProperty("/hasSnapResult", true);
          MessageToast.show(that.getI18nText("snapshotCreatedMtm"));
        })
        .catch(function (err) {
          MessageBox.error(that._formatError(err));
        });
    }
  });
});
