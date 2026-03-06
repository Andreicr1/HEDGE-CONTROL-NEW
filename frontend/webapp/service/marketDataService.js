sap.ui.define(["hedgecontrol/service/apiClient"], function (apiClient) {
  "use strict";

  return {
    ingestWestmetallAluminumCashSettlement: function (payload) {
      return apiClient.postJson("/market-data/westmetall/aluminum/cash-settlement/ingest", payload);
    },

    ingestWestmetallBulk: function (payload) {
      return apiClient.postJson("/market-data/westmetall/aluminum/cash-settlement/ingest-bulk", payload);
    },

    listCashSettlementPrices: function (oParams) {
      var aQuery = [];
      if (oParams.start_date) { aQuery.push("start_date=" + oParams.start_date); }
      if (oParams.end_date) { aQuery.push("end_date=" + oParams.end_date); }
      if (oParams.symbol) { aQuery.push("symbol=" + encodeURIComponent(oParams.symbol)); }
      if (oParams.limit) { aQuery.push("limit=" + oParams.limit); }
      var sUrl = "/market-data/westmetall/aluminum/cash-settlement/prices";
      if (aQuery.length) { sUrl += "?" + aQuery.join("&"); }
      return apiClient.getJson(sUrl);
    }
  };
});
