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
    },
    rejectQuote: function (rfqId, quoteId, payload) {
      return apiClient.postJson("/rfqs/" + encodeURIComponent(rfqId) + "/actions/reject-quote?quote_id=" + encodeURIComponent(quoteId), payload);
    },
    refreshCounterparty: function (rfqId, payload) {
      return apiClient.postJson("/rfqs/" + encodeURIComponent(rfqId) + "/actions/refresh-counterparty", payload);
    },
    awardQuote: function (rfqId, payload) {
      return apiClient.postJson("/rfqs/" + encodeURIComponent(rfqId) + "/actions/award-quote", payload);
    },
    list: function () {
      return apiClient.getJson("/rfqs");
    },
    listQuotes: function (rfqId) {
      return apiClient.getJson("/rfqs/" + encodeURIComponent(rfqId) + "/quotes");
    },
    listStateEvents: function (rfqId) {
      return apiClient.getJson("/rfqs/" + encodeURIComponent(rfqId) + "/state-events");
    },
    archive: function (rfqId) {
      return apiClient.patchJson("/rfqs/" + encodeURIComponent(rfqId) + "/archive");
    },
    previewText: function (oPayload) {
      return apiClient.postJson("/rfqs/preview-text", oPayload);
    },
    getCount: function () {
      return apiClient.getJson("/rfqs/count");
    }
  };
});
