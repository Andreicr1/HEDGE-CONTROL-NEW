sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/exposuresService",
  "hedgecontrol/service/ordersService",
  "hedgecontrol/service/contractsService",
  "hedgecontrol/service/rfqService"
], function (BaseController, exposuresService, ordersService, contractsService, rfqService) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.Home", {

    _bLoadingKpis: false,

    onInit: function () {
      this.initViewModel("home", {
        kpiExposureValue: "–",
        kpiExposureScale: "",
        kpiExposureColor: "Neutral",
        kpiOrdersCount: "–",
        kpiContractsCount: "–",
        kpiRfqsCount: "–",
        kpiPnlValue: "–",
        kpiPnlColor: "Neutral",
        kpiPnlReady: false,
        kpiCashflowValue: "–",
        kpiCashflowReady: false,
        kpiState: "Loading",
        lastRefresh: "",
        errorMessage: ""
      });

      this.getRouter().getRoute("home").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this.setLayout("OneColumn");
      this._loadKpis();
    },

    _loadKpis: function () {
      if (this._bLoadingKpis) { return; }
      this._bLoadingKpis = true;
      var oModel = this.getViewModel();
      oModel.setProperty("/kpiState", "Loading");
      oModel.setProperty("/errorMessage", "");

      this.loadParallel([
        function () { return exposuresService.getNet(); },
        function () { return ordersService.getCount(); },
        function () { return contractsService.getCount(); },
        function () { return rfqService.getCount(); }
      ]).then(function (aResults) {
        var oExposure   = aResults[0];
        var oOrders     = aResults[1];
        var oContracts  = aResults[2];
        var oRfqs       = aResults[3];

        // Exposure net (MT) — API returns { net_position: number, ... }
        if (oExposure && oExposure.net_position !== undefined) {
          var fNet = parseFloat(oExposure.net_position);
          oModel.setProperty("/kpiExposureValue", Math.abs(fNet).toLocaleString("pt-BR", { maximumFractionDigits: 0 }));
          oModel.setProperty("/kpiExposureScale", "MT");
          oModel.setProperty("/kpiExposureColor", fNet < 0 ? "Critical" : (fNet === 0 ? "Neutral" : "Good"));
        }

        // Orders count
        oModel.setProperty("/kpiOrdersCount", typeof (oOrders && oOrders.count) === "number" ? String(oOrders.count) : "–");

        // Contracts count
        oModel.setProperty("/kpiContractsCount", typeof (oContracts && oContracts.count) === "number" ? String(oContracts.count) : "–");

        // RFQs count
        oModel.setProperty("/kpiRfqsCount", typeof (oRfqs && oRfqs.count) === "number" ? String(oRfqs.count) : "–");

        oModel.setProperty("/kpiState", "Loaded");

        var now = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
        oModel.setProperty("/lastRefresh", this.getI18nText("homeLastRefresh", [now]));
      }.bind(this)).catch(function () {
        oModel.setProperty("/kpiState", "Failed");
        oModel.setProperty("/errorMessage", this.getI18nText("errorRequestFailed"));
      }.bind(this)).finally(function () {
        this._bLoadingKpis = false;
      }.bind(this));
    },

    onRefresh: function () {
      this._loadKpis();
    },

    // ── Navigation ──────────────────────────────────────────────
    onNavToExposures: function () { this.navToList("exposures"); },
    onNavToOrders:    function () { this.navToList("orders"); },
    onNavToRfq:       function () { this.navToList("rfq"); },
    onNavToContracts: function () { this.navToList("contracts"); },
    onNavToCashflow:  function () { this.navToList("cashflow"); },
    onNavToPnl:       function () { this.navToList("pnl"); }
  });
});
