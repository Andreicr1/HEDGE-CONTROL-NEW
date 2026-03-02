sap.ui.define(["hedgecontrol/service/apiClient"], function (apiClient) {
  "use strict";

  return {
    triggerRun: function (sRunDate) {
      return apiClient.postJson("/finance/pipeline/run", { run_date: sRunDate });
    },
    listRuns: function (iLimit) {
      var sPath = "/finance/pipeline/runs";
      if (iLimit) {
        sPath += "?limit=" + encodeURIComponent(String(iLimit));
      }
      return apiClient.getJson(sPath);
    },
    getRunDetail: function (sRunId) {
      return apiClient.getJson("/finance/pipeline/runs/" + encodeURIComponent(sRunId));
    }
  };
});
