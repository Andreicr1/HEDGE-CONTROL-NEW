sap.ui.define(["hedgecontrol/service/apiClient"], function (apiClient) {
  "use strict";

  return {
    create: function (payload) {
      return apiClient.postJson("/rfqs", payload);
    },
    getById: function (rfqId) {
      return apiClient.getJson("/rfqs/" + encodeURIComponent(rfqId));
    },
    createQuote: function (rfqId, payload) {
      return apiClient.postJson("/rfqs/" + encodeURIComponent(rfqId) + "/quotes", payload);
    },
    getRanking: function (rfqId) {
      return apiClient.getJson("/rfqs/" + encodeURIComponent(rfqId) + "/ranking");
    },
    getTradeRanking: function (rfqId) {
      return apiClient.getJson("/rfqs/" + encodeURIComponent(rfqId) + "/trade-ranking");
    },
    award: function (rfqId, payload) {
      return apiClient.postJson("/rfqs/" + encodeURIComponent(rfqId) + "/actions/award", payload);
    },
    refresh: function (rfqId, payload) {
      return apiClient.postJson("/rfqs/" + encodeURIComponent(rfqId) + "/actions/refresh", payload);
    },
    reject: function (rfqId, payload) {
      return apiClient.postJson("/rfqs/" + encodeURIComponent(rfqId) + "/actions/reject", payload);
    }
  };
});
