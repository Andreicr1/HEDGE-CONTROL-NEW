sap.ui.define(["hedgecontrol/service/apiClient"], function (apiClient) {
  "use strict";

  return {
    create: function (payload) {
      return apiClient.postJson("/linkages", payload);
    },
    getById: function (linkageId) {
      return apiClient.getJson("/linkages/" + encodeURIComponent(linkageId));
    }
  };
});
