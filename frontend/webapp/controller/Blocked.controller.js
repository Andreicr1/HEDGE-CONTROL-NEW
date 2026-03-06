sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "sap/ui/model/json/JSONModel"
], function (BaseController, JSONModel) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.Blocked", {
    _aRouteNames: ["exposures", "orders", "rfq", "contracts", "cashflow", "pnl", "scenario"],

    onInit: function () {
      var oRouter = this.getRouter();
      this._aRouteNames.forEach(function (sRoute) {
        oRouter.getRoute(sRoute).attachPatternMatched(this._onRouteMatched, this);
      }, this);
    },

    onExit: function () {
      var oRouter = this.getRouter();
      this._aRouteNames.forEach(function (sRoute) {
        oRouter.getRoute(sRoute).detachPatternMatched(this._onRouteMatched, this);
      }, this);
    },

    _onRouteMatched: function (event) {
      var routeName = event.getParameter("name");
      var appModel = this.getOwnerComponent().getModel("app");
      var blockedData = (appModel.getProperty("/blocked") && appModel.getProperty("/blocked/" + routeName))
        || (appModel.getProperty("/blocked") && appModel.getProperty("/blocked/notFound"))
        || { title: routeName, message: "" };
      this.getView().setModel(new JSONModel(blockedData), "blocked");
    },

    onNavBack: function () {
      this.getRouter().navTo("home");
    }
  });
});
