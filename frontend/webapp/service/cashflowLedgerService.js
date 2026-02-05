sap.ui.define(["hedgecontrol/service/apiClient"], function (apiClient) {
  "use strict";

  var withQuery = function (path, query) {
    var parts = [];
    Object.keys(query || {}).forEach(function (key) {
      var value = query[key];
      if (value === undefined || value === null || value === "") {
        return;
      }
      parts.push(encodeURIComponent(key) + "=" + encodeURIComponent(String(value)));
    });
    return path + (parts.length ? "?" + parts.join("&") : "");
  };

  return {
    settleContract: function (contractId, payload) {
      return apiClient.postJson("/cashflow/contracts/" + encodeURIComponent(contractId) + "/settle", payload);
    },
    listByEvent: function (sourceEventId, sourceEventType) {
      return apiClient.getJson(withQuery("/cashflow/ledger", {
        source_event_id: sourceEventId,
        source_event_type: sourceEventType
      }));
    },
    listForContract: function (contractId, start, end) {
      return apiClient.getJson(withQuery("/cashflow/ledger/hedge-contracts/" + encodeURIComponent(contractId), {
        start: start,
        end: end
      }));
    }
  };
});
