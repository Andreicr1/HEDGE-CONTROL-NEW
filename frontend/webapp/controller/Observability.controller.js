sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/model/json/JSONModel",
  "sap/m/MessageBox",
  "hedgecontrol/service/observabilityService"
], function (Controller, JSONModel, MessageBox, observabilityService) {
  "use strict";

  return Controller.extend("hedgecontrol.controller.Observability", {
    onInit: function () {
      var model = new JSONModel({
        busy: false,
        healthItems: [],
        readyItems: [],
        metricsText: ""
      });
      this.getView().setModel(model, "observability");
      this._loadObservability();
    },

    _loadObservability: function () {
      var model = this.getView().getModel("observability");
      model.setProperty("/busy", true);

      var healthPromise = observabilityService.getHealth();
      var readyPromise = observabilityService.getReady();
      var metricsPromise = observabilityService.getMetrics();

      Promise.all([healthPromise, readyPromise, metricsPromise])
        .then(function (responses) {
          var health = responses[0] || {};
          var ready = responses[1] || {};
          var metricsText = responses[2] || "";

          model.setProperty("/healthItems", this._toKeyValueItems(health));
          model.setProperty("/readyItems", this._toKeyValueItems(ready));
          model.setProperty("/metricsText", metricsText);
        }.bind(this))
        .catch(function (error) {
          var status = error && error.status ? " (HTTP " + error.status + ")" : "";
          MessageBox.error("Observability fetch failed" + status + ": " + error.message);
        })
        .finally(function () {
          model.setProperty("/busy", false);
        });
    },

    _toKeyValueItems: function (payload) {
      return Object.keys(payload).map(function (key) {
        return {
          label: key,
          value: String(payload[key])
        };
      });
    }
  });
});