sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "sap/ui/model/json/JSONModel",
  "sap/m/MessageBox",
  "sap/m/MessageToast",
  "hedgecontrol/service/marketDataService"
], function (BaseController, JSONModel, MessageBox, MessageToast, marketDataService) {
  "use strict";

  function _emptyForm() {
    return {
      symbol: "",
      settlement_date: "",
      price_usd: "",
      source: "westmetall",
      error: "",
      success: ""
    };
  }

  return BaseController.extend("hedgecontrol.controller.MarketData", {

    onInit: function () {
      this.initViewModel("mkt", _emptyForm());
      this.getRouter().getRoute("market-data").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this.getViewModel().setData(_emptyForm());
    },

    onIngest: function () {
      var oModel = this.getViewModel();
      oModel.setProperty("/error", "");
      oModel.setProperty("/success", "");

      var sSymbol = oModel.getProperty("/symbol").trim();
      var sDate = oModel.getProperty("/settlement_date");
      var sPrice = oModel.getProperty("/price_usd");
      var sSource = oModel.getProperty("/source").trim();

      if (!sSymbol || !sDate || !sPrice) {
        MessageBox.warning(this.getI18nText("msgFillSymbolDatePrice"));
        return;
      }

      var oPayload = {
        symbol: sSymbol,
        settlement_date: sDate,
        price_usd: parseFloat(sPrice),
        source: sSource || "westmetall"
      };

      var that = this;
      marketDataService.ingestWestmetallAluminumCashSettlement(oPayload)
        .then(function () {
          oModel.setProperty("/success", that.getI18nText("msgPriceIngestSuccess"));
          MessageToast.show(that.getI18nText("msgPriceIngested"));
        })
        .catch(function (err) {
          oModel.setProperty("/error", that._formatError(err));
        });
    }
  });
});
