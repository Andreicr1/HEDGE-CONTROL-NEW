sap.ui.define(["hedgecontrol/service/apiClient"], function (apiClient) {
  "use strict";

  return {
    runWhatIf: function (payload) {
      return apiClient.postJson("/scenario/what-if/run", payload);
    }
  };
});
