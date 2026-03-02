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
    listEvents: function (oFilters) {
      return apiClient.getJson(_withQuery("/audit/events", oFilters));
    },
    verifyEvent: function (sEventId) {
      return apiClient.getJson("/audit/events/" + encodeURIComponent(sEventId) + "/verify");
    }
  };
});
