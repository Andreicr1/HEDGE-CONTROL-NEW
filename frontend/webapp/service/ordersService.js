sap.ui.define(["hedgecontrol/service/apiClient"], function (apiClient) {
  "use strict";

  return {
    createSales: function (payload) {
      return apiClient.postJson("/orders/sales", payload);
    },
    createPurchase: function (payload) {
      return apiClient.postJson("/orders/purchase", payload);
    },
    getById: function (orderId) {
      return apiClient.getJson("/orders/" + encodeURIComponent(orderId));
    }
  };
});
