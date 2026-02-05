sap.ui.define(["hedgecontrol/service/apiClient"], function (apiClient) {
  "use strict";

  return {
    getHealth: function () {
      return apiClient.getJson("/health");
    },
    getReady: function () {
      return apiClient.getJson("/ready");
    },
    getMetrics: function () {
      return apiClient.getText("/metrics");
    }
  };
});