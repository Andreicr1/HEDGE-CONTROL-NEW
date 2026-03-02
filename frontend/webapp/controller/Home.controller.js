sap.ui.define([
  "hedgecontrol/controller/BaseController"
], function (BaseController) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.Home", {
    onInit: function () {},

    onNavToExposures: function () {
      this.getRouter().navTo("exposures");
    },
    onNavToOrders: function () {
      this.getRouter().navTo("orders");
    },
    onNavToRfq: function () {
      this.getRouter().navTo("rfq");
    },
    onNavToContracts: function () {
      this.getRouter().navTo("contracts");
    },
    onNavToCashflow: function () {
      this.getRouter().navTo("cashflow");
    },
    onNavToPnl: function () {
      this.getRouter().navTo("pnl");
    }
  });
});
