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
    list: function (oFilters) {
      return apiClient.getJson(_withQuery("/counterparties", oFilters));
    },
    getById: function (sId) {
      return apiClient.getJson("/counterparties/" + encodeURIComponent(sId));
    },
    create: function (oPayload) {
      return apiClient.postJson("/counterparties", oPayload);
    },
    update: function (sId, oPayload) {
      return apiClient.patchJson("/counterparties/" + encodeURIComponent(sId), oPayload);
    },
    remove: function (sId) {
      return apiClient.deleteJson("/counterparties/" + encodeURIComponent(sId));
    }
  };
});
