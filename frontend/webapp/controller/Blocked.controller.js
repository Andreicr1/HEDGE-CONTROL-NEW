sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/core/UIComponent",
  "sap/ui/model/json/JSONModel"
], function (Controller, UIComponent, JSONModel) {
  "use strict";

  return Controller.extend("hedgecontrol.controller.Blocked", {
    onInit: function () {
      var router = UIComponent.getRouterFor(this);
      router.getRoute("exposures").attachPatternMatched(this._onRouteMatched, this);
      router.getRoute("orders").attachPatternMatched(this._onRouteMatched, this);
      router.getRoute("rfq").attachPatternMatched(this._onRouteMatched, this);
      router.getRoute("contracts").attachPatternMatched(this._onRouteMatched, this);
      router.getRoute("cashflow").attachPatternMatched(this._onRouteMatched, this);
      router.getRoute("pnl").attachPatternMatched(this._onRouteMatched, this);
      router.getRoute("scenario").attachPatternMatched(this._onRouteMatched, this);
      router.getRoute("notFound").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (event) {
      var routeName = event.getParameter("name");
      var appModel = this.getOwnerComponent().getModel("app");
      var blockedData = appModel.getProperty("/blocked/" + routeName) || appModel.getProperty("/blocked/notFound");
      this.getView().setModel(new JSONModel(blockedData), "blocked");
    },

    onNavBack: function () {
      var router = UIComponent.getRouterFor(this);
      router.navTo("home");
    }
  });
});