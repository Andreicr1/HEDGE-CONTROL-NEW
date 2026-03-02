sap.ui.define(["hedgecontrol/service/apiClient"], function (apiClient) {
  "use strict";

  return {
    createHedge: function (payload) {
      return apiClient.postJson("/contracts/hedge", payload);
    },
    getHedgeById: function (contractId) {
      return apiClient.getJson("/contracts/hedge/" + encodeURIComponent(contractId));
    },
    list: function () {
      return apiClient.getJson("/contracts/hedge");
    },
    archive: function (contractId) {
      return apiClient.patchJson("/contracts/hedge/" + encodeURIComponent(contractId) + "/archive");
    }
  };
});
