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

  var _enc = function (sId) {
    return encodeURIComponent(sId);
  };

  return {
    list: function (oFilters) {
      return apiClient.getJson(_withQuery("/hedges", oFilters));
    },
    getById: function (sHedgeId) {
      return apiClient.getJson("/hedges/" + _enc(sHedgeId));
    },
    create: function (oPayload) {
      return apiClient.postJson("/hedges", oPayload);
    },
    createFromRfq: function (sRfqId) {
      return apiClient.postJson("/hedges/from-rfq/" + _enc(sRfqId));
    },
    update: function (sHedgeId, oPayload) {
      return apiClient.patchJson("/hedges/" + _enc(sHedgeId), oPayload);
    },
    updateStatus: function (sHedgeId, sStatus) {
      return apiClient.patchJson("/hedges/" + _enc(sHedgeId) + "/status", { status: sStatus });
    },
    cancel: function (sHedgeId) {
      return apiClient.deleteJson("/hedges/" + _enc(sHedgeId));
    }
  };
});
