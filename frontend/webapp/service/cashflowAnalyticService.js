sap.ui.define(["hedgecontrol/service/apiClient"], function (apiClient) {
  "use strict";

  return {
    get: function (asOfDate) {
      return apiClient.getJson("/cashflow/analytic?as_of_date=" + encodeURIComponent(asOfDate));
    }
  };
});
