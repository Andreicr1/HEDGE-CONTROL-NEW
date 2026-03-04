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
      return apiClient.getJson(_withQuery("/deals", oFilters));
    },
    getById: function (sDealId) {
      return apiClient.getJson("/deals/" + _enc(sDealId));
    },
    create: function (oPayload) {
      return apiClient.postJson("/deals", oPayload);
    },
    addLink: function (sDealId, oPayload) {
      return apiClient.postJson("/deals/" + _enc(sDealId) + "/links", oPayload);
    },
    removeLink: function (sDealId, sLinkId) {
      return apiClient.deleteJson("/deals/" + _enc(sDealId) + "/links/" + _enc(sLinkId));
    },
    triggerPnlSnapshot: function (sDealId, sDate) {
      var sPath = "/deals/" + _enc(sDealId) + "/pnl-snapshot";
      if (sDate) {
        sPath += "?snapshot_date=" + encodeURIComponent(sDate);
      }
      return apiClient.postJson(sPath);
    },
    getPnlHistory: function (sDealId) {
      return apiClient.getJson("/deals/" + _enc(sDealId) + "/pnl-history");
    },
    getPnlBreakdown: function (aIds, sDate) {
      return apiClient.postJson("/deals/pnl-breakdown", {
        deal_ids: aIds || [],
        snapshot_date: sDate
      });
    },
    findByLinkedEntity: function (sLinkedType, sLinkedId) {
      return apiClient.getJson(_withQuery("/deals/by-linked-entity", {
        linked_type: sLinkedType,
        linked_id: sLinkedId
      }));
    }
  };
});
