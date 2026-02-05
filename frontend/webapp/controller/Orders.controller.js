sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/model/json/JSONModel",
  "sap/m/MessageBox",
  "hedgecontrol/service/ordersService",
  "hedgecontrol/service/mtmService",
  "hedgecontrol/util/jsonUtil"
], function (Controller, JSONModel, MessageBox, ordersService, mtmService, jsonUtil) {
  "use strict";

  return Controller.extend("hedgecontrol.controller.Orders", {
    onInit: function () {
      var model = new JSONModel({
        busy: false,
        createSalesBody: "{}",
        createPurchaseBody: "{}",
        orderId: "",
        mtmAsOfDate: "",
        responseText: "",
        errorText: ""
      });
      this.getView().setModel(model, "orders");
    },

    onCreateSales: function () {
      this._postFromTextArea("/createSalesBody", function (payload) {
        return ordersService.createSales(payload);
      });
    },

    onCreatePurchase: function () {
      this._postFromTextArea("/createPurchaseBody", function (payload) {
        return ordersService.createPurchase(payload);
      });
    },

    onGetOrder: function () {
      var model = this.getView().getModel("orders");
      var orderId = (model.getProperty("/orderId") || "").trim();
      if (!orderId) {
        MessageBox.error("order_id is required");
        return;
      }
      this._run(function () {
        return ordersService.getById(orderId);
      });
    },

    onGetOrderMtm: function () {
      var model = this.getView().getModel("orders");
      var orderId = (model.getProperty("/orderId") || "").trim();
      var asOfDate = (model.getProperty("/mtmAsOfDate") || "").trim();
      if (!orderId) {
        MessageBox.error("order_id is required");
        return;
      }
      if (!asOfDate) {
        MessageBox.error("as_of_date is required");
        return;
      }
      this._run(function () {
        return mtmService.getForOrder(orderId, asOfDate);
      });
    },

    _postFromTextArea: function (path, fn) {
      var model = this.getView().getModel("orders");
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
      var model = this.getView().getModel("orders");
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
