sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/model/json/JSONModel",
  "sap/m/MessageBox",
  "hedgecontrol/service/plService",
  "hedgecontrol/util/jsonUtil"
], function (Controller, JSONModel, MessageBox, plService, jsonUtil) {
  "use strict";

  return Controller.extend("hedgecontrol.controller.Pnl", {
    onInit: function () {
      var model = new JSONModel({
        busy: false,
        entityType: "hedge_contract",
        entityId: "",
        periodStart: "",
        periodEnd: "",
        snapshotCreateBody: "{}",
        responseText: "",
        errorText: ""
      });
      this.getView().setModel(model, "pnl");
    },

    onGetPl: function () {
      var args = this._requireArgs();
      if (!args) {
        return;
      }
      this._run(function () {
        return plService.getPl(args.entityType, args.entityId, args.periodStart, args.periodEnd);
      });
    },

    onGetSnapshot: function () {
      var args = this._requireArgs();
      if (!args) {
        return;
      }
      this._run(function () {
        return plService.getSnapshot(args.entityType, args.entityId, args.periodStart, args.periodEnd);
      });
    },

    onCreateSnapshot: function () {
      var model = this.getView().getModel("pnl");
      var bodyText = model.getProperty("/snapshotCreateBody");
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
        return plService.createSnapshot(payload);
      });
    },

    _requireArgs: function () {
      var model = this.getView().getModel("pnl");
      var entityType = (model.getProperty("/entityType") || "").trim();
      var entityId = (model.getProperty("/entityId") || "").trim();
      var periodStart = (model.getProperty("/periodStart") || "").trim();
      var periodEnd = (model.getProperty("/periodEnd") || "").trim();
      if (!entityType) {
        MessageBox.error("entity_type is required");
        return null;
      }
      if (!entityId) {
        MessageBox.error("entity_id is required");
        return null;
      }
      if (!periodStart || !periodEnd) {
        MessageBox.error("period_start and period_end are required");
        return null;
      }
      return { entityType: entityType, entityId: entityId, periodStart: periodStart, periodEnd: periodEnd };
    },

    _run: function (fn) {
      var model = this.getView().getModel("pnl");
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
