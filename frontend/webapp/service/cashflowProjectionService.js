sap.ui.define(["hedgecontrol/service/apiClient"], function (apiClient) {
  "use strict";

  return {
    get: function (asOfDate) {
      return apiClient.getJson("/cashflow/projection?as_of_date=" + encodeURIComponent(asOfDate));
    }
  };
});
