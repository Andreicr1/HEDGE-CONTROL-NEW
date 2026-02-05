sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/model/json/JSONModel",
  "sap/m/MessageBox",
  "hedgecontrol/service/rfqService",
  "hedgecontrol/util/jsonUtil"
], function (Controller, JSONModel, MessageBox, rfqService, jsonUtil) {
  "use strict";

  return Controller.extend("hedgecontrol.controller.Rfq", {
    onInit: function () {
      var model = new JSONModel({
        busy: false,
        rfqId: "",
        createRfqBody: "{}",
        quoteBody: "{}",
        awardBody: "{}",
        refreshBody: "{}",
        rejectBody: "{}",
        responseText: "",
        errorText: ""
      });
      this.getView().setModel(model, "rfq");
    },

    onCreateRfq: function () {
      this._postBody("/createRfqBody", function (payload) {
        return rfqService.create(payload);
      });
    },

    onGetRfq: function () {
      var rfqId = this._requireId();
      if (!rfqId) {
        return;
      }
      this._run(function () {
        return rfqService.getById(rfqId);
      });
    },

    onCreateQuote: function () {
      var rfqId = this._requireId();
      if (!rfqId) {
        return;
      }
      this._postBody("/quoteBody", function (payload) {
        return rfqService.createQuote(rfqId, payload);
      });
    },

    onGetRanking: function () {
      var rfqId = this._requireId();
      if (!rfqId) {
        return;
      }
      this._run(function () {
        return rfqService.getRanking(rfqId);
      });
    },

    onGetTradeRanking: function () {
      var rfqId = this._requireId();
      if (!rfqId) {
        return;
      }
      this._run(function () {
        return rfqService.getTradeRanking(rfqId);
      });
    },

    onAward: function () {
      var rfqId = this._requireId();
      if (!rfqId) {
        return;
      }
      this._postBody("/awardBody", function (payload) {
        return rfqService.award(rfqId, payload);
      });
    },

    onRefresh: function () {
      var rfqId = this._requireId();
      if (!rfqId) {
        return;
      }
      this._postBody("/refreshBody", function (payload) {
        return rfqService.refresh(rfqId, payload);
      });
    },

    onReject: function () {
      var rfqId = this._requireId();
      if (!rfqId) {
        return;
      }
      this._postBody("/rejectBody", function (payload) {
        return rfqService.reject(rfqId, payload);
      });
    },

    _requireId: function () {
      var model = this.getView().getModel("rfq");
      var rfqId = (model.getProperty("/rfqId") || "").trim();
      if (!rfqId) {
        MessageBox.error("rfq_id is required");
        return "";
      }
      return rfqId;
    },

    _postBody: function (path, fn) {
      var model = this.getView().getModel("rfq");
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
      var model = this.getView().getModel("rfq");
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
