sap.ui.define(["hedgecontrol/service/apiClient"], function (apiClient) {
  "use strict";

  return {
    getAuditEvents: function (oFilter) {
      var aParams = [];

      if (oFilter.entity_type) {
        aParams.push("entity_type=" + encodeURIComponent(oFilter.entity_type));
      }
      if (oFilter.entity_id) {
        aParams.push("entity_id=" + encodeURIComponent(oFilter.entity_id));
      }
      if (oFilter.start) {
        aParams.push("start=" + encodeURIComponent(oFilter.start));
      }
      if (oFilter.end) {
        aParams.push("end=" + encodeURIComponent(oFilter.end));
      }
      if (oFilter.cursor) {
        aParams.push("cursor=" + encodeURIComponent(oFilter.cursor));
      }
      if (oFilter.limit) {
        aParams.push("limit=" + oFilter.limit);
      }

      var sUrl = "/audit/events" + (aParams.length ? "?" + aParams.join("&") : "");

      return apiClient.getJson(sUrl);
    }
  };
});