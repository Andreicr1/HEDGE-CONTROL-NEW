sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "sap/m/MessageBox",
  "sap/m/MessageToast",
  "hedgecontrol/service/marketDataService"
], function (BaseController, MessageBox, MessageToast, marketDataService) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.MarketData", {

    onInit: function () {
      this.initViewModel("mkt", {
        symbol: "LME_ALU_CASH_SETTLEMENT_DAILY",
        startDate: "",
        endDate: "",
        resultLoaded: false,
        summaryText: "",
        totals: {},
        prices: []
      });
      this.getRouter().getRoute("marketData").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      // Set default date range: last 30 days
      var oEnd = new Date();
      var oStart = new Date();
      oStart.setDate(oStart.getDate() - 30);
      var oModel = this.getViewModel();
      oModel.setProperty("/startDate", this._formatDate(oStart));
      oModel.setProperty("/endDate", this._formatDate(oEnd));
      oModel.setProperty("/resultLoaded", false);
      oModel.setProperty("/prices", []);
    },

    /* ─── Search ─── */

    onSearch: function () {
      var oModel = this.getViewModel();
      var sSymbol = oModel.getProperty("/symbol");
      var sStart = oModel.getProperty("/startDate");
      var sEnd = oModel.getProperty("/endDate");

      if (!sStart || !sEnd) {
        MessageBox.warning(this.getI18nText("mktFillDates"));
        return;
      }

      var that = this;
      marketDataService.listCashSettlementPrices({
        start_date: sStart,
        end_date: sEnd,
        symbol: sSymbol || undefined
      }).then(function (aData) {
        var aPrices = aData || [];
        oModel.setProperty("/prices", aPrices);
        oModel.setProperty("/resultLoaded", true);

        // Compute summary totals
        var fMin = Infinity, fMax = -Infinity, fSum = 0;
        aPrices.forEach(function (p) {
          var v = parseFloat(p.price_usd) || 0;
          if (v < fMin) { fMin = v; }
          if (v > fMax) { fMax = v; }
          fSum += v;
        });
        var nCount = aPrices.length;
        oModel.setProperty("/totals", {
          count: nCount,
          minPrice: nCount > 0 ? fMin : 0,
          maxPrice: nCount > 0 ? fMax : 0,
          avgPrice: nCount > 0 ? (fSum / nCount) : 0
        });
        oModel.setProperty("/summaryText",
          nCount + " registro(s) | " + sStart + " a " + sEnd
        );
      }).catch(function (err) {
        MessageBox.error(that._formatError(err));
        oModel.setProperty("/resultLoaded", false);
      });
    },

    /* ─── Ingest (manual entry, kept from previous version) ─── */

    onIngest: function () {
      var oModel = this.getViewModel();
      var sSymbol = oModel.getProperty("/symbol");
      var sStart = oModel.getProperty("/startDate");
      var sEnd = oModel.getProperty("/endDate");

      // Use start date as settlement date for ingest
      var sDate = sStart;
      if (!sDate) {
        sDate = this._formatDate(new Date());
      }

      var that = this;
      var oPayload = { settlement_date: sDate };
      marketDataService.ingestWestmetallAluminumCashSettlement(oPayload)
        .then(function () {
          MessageToast.show(that.getI18nText("msgPriceIngested"));
          // Auto-refresh results
          that.onSearch();
        })
        .catch(function (err) {
          MessageBox.error(that._formatError(err));
        });
    },

    /* ─── Export CSV ─── */

    onExportCSV: function () {
      var oModel = this.getViewModel();
      var aPrices = oModel.getProperty("/prices") || [];
      if (aPrices.length === 0) { return; }

      var aLines = ["settlement_date,price_usd,symbol,source"];
      aPrices.forEach(function (p) {
        aLines.push([p.settlement_date, p.price_usd, p.symbol, p.source].join(","));
      });
      var sCSV = aLines.join("\n");

      var oBlob = new Blob([sCSV], { type: "text/csv;charset=utf-8" });
      var sUrl = URL.createObjectURL(oBlob);
      var oLink = document.createElement("a");
      oLink.href = sUrl;
      oLink.download = "market_data_export.csv";
      oLink.click();
      URL.revokeObjectURL(sUrl);
    },

    /* ─── Helpers ─── */

    _formatDate: function (oDate) {
      return oDate.getFullYear() + "-" +
        String(oDate.getMonth() + 1).padStart(2, "0") + "-" +
        String(oDate.getDate()).padStart(2, "0");
    }
  });
});
