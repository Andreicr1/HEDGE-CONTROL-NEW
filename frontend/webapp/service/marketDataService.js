sap.ui.define(["hedgecontrol/service/apiClient"], function (apiClient) {
  "use strict";

  return {
    ingestWestmetallAluminumCashSettlement: function (payload) {
      return apiClient.postJson("/market-data/westmetall/aluminum/cash-settlement/ingest", payload);
    }
  };
});
