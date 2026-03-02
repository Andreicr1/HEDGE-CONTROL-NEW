sap.ui.define(["hedgecontrol/service/apiClient"], function (apiClient) {
  "use strict";

  var _withQuery = function (sPath, oQuery) {
    var aParts = [];
    Object.keys(oQuery || {}).forEach(function (sKey) {
      var vValue = oQuery[sKey];
      if (vValue === undefined || vValue === null || vValue === "") {
        return;
      }
      aParts.push(encodeURIComponent(sKey) + "=" + encodeURIComponent(String(vValue)));
    });
    return sPath + (aParts.length ? "?" + aParts.join("&") : "");
  };

  return {
    getCommercial: function () {
      return apiClient.getJson("/exposures/commercial");
    },
    getGlobal: function () {
      return apiClient.getJson("/exposures/global");
    },
    reconcile: function () {
      return apiClient.postJson("/exposures/reconcile");
    },
    getNet: function (sCommodity) {
      return apiClient.getJson(_withQuery("/exposures/net", { commodity: sCommodity }));
    },
    listExposures: function (oFilters) {
      return apiClient.getJson(_withQuery("/exposures/list", oFilters));
    },
    getExposure: function (sId) {
      return apiClient.getJson("/exposures/" + encodeURIComponent(sId));
    },
    listTasks: function () {
      return apiClient.getJson("/exposures/tasks");
    },
    executeTask: function (sTaskId) {
      return apiClient.postJson("/exposures/tasks/" + encodeURIComponent(sTaskId) + "/execute");
    }
  };
});
