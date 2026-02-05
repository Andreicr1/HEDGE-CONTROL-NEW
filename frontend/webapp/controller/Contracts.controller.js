sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/model/json/JSONModel",
  "sap/m/MessageBox",
  "hedgecontrol/service/contractsService",
  "hedgecontrol/service/linkagesService",
  "hedgecontrol/service/mtmService",
  "hedgecontrol/util/jsonUtil"
], function (Controller, JSONModel, MessageBox, contractsService, linkagesService, mtmService, jsonUtil) {
  "use strict";

  return Controller.extend("hedgecontrol.controller.Contracts", {
    onInit: function () {
      var model = new JSONModel({
        busy: false,
        createContractBody: "{}",
        contractId: "",
        mtmAsOfDate: "",
        createLinkageBody: "{}",
        linkageId: "",
        responseText: "",
        errorText: ""
      });
      this.getView().setModel(model, "contracts");
    },

    onCreateContract: function () {
      this._postFromTextArea("/createContractBody", function (payload) {
        return contractsService.createHedge(payload);
      });
    },

    onGetContract: function () {
      var model = this.getView().getModel("contracts");
      var contractId = (model.getProperty("/contractId") || "").trim();
      if (!contractId) {
        MessageBox.error("contract_id is required");
        return;
      }
      this._run(function () {
        return contractsService.getHedgeById(contractId);
      });
    },

    onGetContractMtm: function () {
      var model = this.getView().getModel("contracts");
      var contractId = (model.getProperty("/contractId") || "").trim();
      var asOfDate = (model.getProperty("/mtmAsOfDate") || "").trim();
      if (!contractId) {
        MessageBox.error("contract_id is required");
        return;
      }
      if (!asOfDate) {
        MessageBox.error("as_of_date is required");
        return;
      }
      this._run(function () {
        return mtmService.getForHedgeContract(contractId, asOfDate);
      });
    },

    onCreateLinkage: function () {
      this._postFromTextArea("/createLinkageBody", function (payload) {
        return linkagesService.create(payload);
      });
    },

    onGetLinkage: function () {
      var model = this.getView().getModel("contracts");
      var linkageId = (model.getProperty("/linkageId") || "").trim();
      if (!linkageId) {
        MessageBox.error("linkage_id is required");
        return;
      }
      this._run(function () {
        return linkagesService.getById(linkageId);
      });
    },

    _postFromTextArea: function (path, fn) {
      var model = this.getView().getModel("contracts");
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
      var model = this.getView().getModel("contracts");
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
