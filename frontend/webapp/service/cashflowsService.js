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
    list: function () {
      return apiClient.getJson("/cashflows");
    },
    create: function (payload) {
      return apiClient.postJson("/cashflows", payload);
    },
    getById: function (cashflowId, requiredUnderscoreParam) {
      return apiClient.getJson(withQuery("/cashflows/" + encodeURIComponent(cashflowId), { _: requiredUnderscoreParam }));
    }
  };
});
