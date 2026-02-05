sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/model/json/JSONModel",
  "sap/m/MessageBox",
  "hedgecontrol/service/auditService"
], function (Controller, JSONModel, MessageBox, auditService) {
  "use strict";

  return Controller.extend("hedgecontrol.controller.Audit", {
    onInit: function () {
      var model = new JSONModel({
        busy: false,
        filters: {
          entity_type: "",
          entity_id: "",
          start: "",
          end: "",
          cursor: "",
          limit: 50
        },
        events: [],
        next_cursor: ""
      });
      this.getView().setModel(model, "audit");
    },

    onApplyFilter: function () {
      var model = this.getView().getModel("audit");
      var filters = model.getProperty("/filters");

      model.setProperty("/busy", true);
      auditService
        .getAuditEvents(filters)
        .then(function (response) {
          model.setProperty("/events", response.events || []);
          model.setProperty("/next_cursor", response.next_cursor || "");
        })
        .catch(function (error) {
          var status = error && error.status ? " (HTTP " + error.status + ")" : "";
          MessageBox.error("Audit fetch failed" + status + ": " + error.message);
        })
        .finally(function () {
          model.setProperty("/busy", false);
        });
    }
  });
});