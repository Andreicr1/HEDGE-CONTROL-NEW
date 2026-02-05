sap.ui.define(["hedgecontrol/service/apiClient"], function (apiClient) {
  "use strict";

  return {
    getCommercial: function () {
      return apiClient.getJson("/exposures/commercial");
    },
    getGlobal: function () {
      return apiClient.getJson("/exposures/global");
    }
  };
});
