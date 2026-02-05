sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/model/json/JSONModel",
  "sap/m/MessageBox",
  "hedgecontrol/service/exposuresService",
  "hedgecontrol/util/jsonUtil"
], function (Controller, JSONModel, MessageBox, exposuresService, jsonUtil) {
  "use strict";

  return Controller.extend("hedgecontrol.controller.Exposures", {
    onInit: function () {
      var model = new JSONModel({
        busy: false,
        responseText: "",
        errorText: ""
      });
      this.getView().setModel(model, "exposures");
    },

    onLoadCommercial: function () {
      this._run(function () {
        return exposuresService.getCommercial();
      });
    },

    onLoadGlobal: function () {
      this._run(function () {
        return exposuresService.getGlobal();
      });
    },

    _run: function (fn) {
      var model = this.getView().getModel("exposures");
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
