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
    getPl: function (entityType, entityId, periodStart, periodEnd) {
      return apiClient.getJson(withQuery("/pl/" + encodeURIComponent(entityType) + "/" + encodeURIComponent(entityId), {
        period_start: periodStart,
        period_end: periodEnd
      }));
    },
    getSnapshot: function (entityType, entityId, periodStart, periodEnd) {
      return apiClient.getJson(withQuery("/pl/snapshots", {
        entity_type: entityType,
        entity_id: entityId,
        period_start: periodStart,
        period_end: periodEnd
      }));
    },
    createSnapshot: function (payload) {
      return apiClient.postJson("/pl/snapshots", payload);
    }
  };
});
