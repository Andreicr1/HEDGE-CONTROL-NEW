sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/model/json/JSONModel",
  "sap/m/MessageBox",
  "hedgecontrol/service/scenarioService",
  "hedgecontrol/util/jsonUtil"
], function (Controller, JSONModel, MessageBox, scenarioService, jsonUtil) {
  "use strict";

  return Controller.extend("hedgecontrol.controller.Scenario", {
    onInit: function () {
      var model = new JSONModel({
        busy: false,
        requestBody: "{}",
        responseText: "",
        errorText: ""
      });
      this.getView().setModel(model, "scenario");
    },

    onRun: function () {
      var model = this.getView().getModel("scenario");
      var payload;
      try {
        payload = jsonUtil.parse(model.getProperty("/requestBody"));
      } catch (e) {
        MessageBox.error("Invalid JSON: " + e.message);
        return;
      }
      if (payload === undefined) {
        MessageBox.error("Request body is required");
        return;
      }

      model.setProperty("/busy", true);
      model.setProperty("/errorText", "");

      scenarioService
        .runWhatIf(payload)
        .then(function (response) {
          model.setProperty("/responseText", jsonUtil.pretty(response));
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
