sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/model/json/JSONModel",
  "sap/m/MessageBox",
  "hedgecontrol/service/mtmService",
  "hedgecontrol/util/jsonUtil"
], function (Controller, JSONModel, MessageBox, mtmService, jsonUtil) {
  "use strict";

  return Controller.extend("hedgecontrol.controller.Mtm", {
    onInit: function () {
      var model = new JSONModel({
        busy: false,
        objectType: "",
        objectId: "",
        asOfDate: "",
        contractId: "",
        orderId: "",
        responseText: "",
        errorText: ""
      });
      this.getView().setModel(model, "mtm");
    },

    onGetSnapshot: function () {
      var model = this.getView().getModel("mtm");
      var objectType = (model.getProperty("/objectType") || "").trim();
      var objectId = (model.getProperty("/objectId") || "").trim();
      var asOfDate = (model.getProperty("/asOfDate") || "").trim();
      if (!objectType || !objectId || !asOfDate) {
        MessageBox.error("object_type, object_id and as_of_date are required");
        return;
      }
      this._run(function () {
        return mtmService.getSnapshot(objectType, objectId, asOfDate);
      });
    },

    onGetContractMtm: function () {
      var model = this.getView().getModel("mtm");
      var contractId = (model.getProperty("/contractId") || "").trim();
      var asOfDate = (model.getProperty("/asOfDate") || "").trim();
      if (!contractId || !asOfDate) {
        MessageBox.error("contract_id and as_of_date are required");
        return;
      }
      this._run(function () {
        return mtmService.getForHedgeContract(contractId, asOfDate);
      });
    },

    onGetOrderMtm: function () {
      var model = this.getView().getModel("mtm");
      var orderId = (model.getProperty("/orderId") || "").trim();
      var asOfDate = (model.getProperty("/asOfDate") || "").trim();
      if (!orderId || !asOfDate) {
        MessageBox.error("order_id and as_of_date are required");
        return;
      }
      this._run(function () {
        return mtmService.getForOrder(orderId, asOfDate);
      });
    },

    _run: function (fn) {
      var model = this.getView().getModel("mtm");
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
