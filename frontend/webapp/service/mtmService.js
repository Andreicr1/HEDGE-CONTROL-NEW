sap.ui.define(["hedgecontrol/service/apiClient"], function (apiClient) {
  "use strict";

  return {
    getForHedgeContract: function (contractId, asOfDate) {
      return apiClient.getJson(
        "/mtm/hedge-contracts/" + encodeURIComponent(contractId) + "?as_of_date=" + encodeURIComponent(asOfDate)
      );
    },
    getForOrder: function (orderId, asOfDate) {
      return apiClient.getJson(
        "/mtm/orders/" + encodeURIComponent(orderId) + "?as_of_date=" + encodeURIComponent(asOfDate)
      );
    },
    getSnapshot: function (objectType, objectId, asOfDate) {
      return apiClient.getJson(
        "/mtm/snapshots?object_type=" + encodeURIComponent(objectType) + "&object_id=" + encodeURIComponent(objectId) + "&as_of_date=" + encodeURIComponent(asOfDate)
      );
    }
  };
});
