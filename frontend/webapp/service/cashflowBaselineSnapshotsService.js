sap.ui.define(["hedgecontrol/service/apiClient"], function (apiClient) {
  "use strict";

  return {
    get: function (asOfDate) {
      return apiClient.getJson("/cashflow/baseline/snapshots?as_of_date=" + encodeURIComponent(asOfDate));
    },
    create: function (payload) {
      return apiClient.postJson("/cashflow/baseline/snapshots", payload);
    }
  };
});
