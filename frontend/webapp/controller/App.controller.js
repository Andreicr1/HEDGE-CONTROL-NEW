sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/core/UIComponent",
  "sap/ui/Device",
  "sap/ui/model/json/JSONModel"
], function (Controller, UIComponent, Device, JSONModel) {
  "use strict";

  return Controller.extend("hedgecontrol.controller.App", {
    onInit: function () {
      this._router = UIComponent.getRouterFor(this);
      this._router.attachRouteMatched(this._onRouteMatched, this);
      this.getView().setModel(new JSONModel({
        selectedKey: "home"
      }), "appModel");
      this._applyInitialSideState();
    },

    _applyInitialSideState: function () {
      var toolPage = this.byId("toolPage");
      if (!toolPage) {
        return;
      }
      toolPage.setSideExpanded(!Device.system.phone);
    },

    onMenuButtonPressed: function () {
      var toolPage = this.byId("toolPage");
      if (!toolPage) {
        return;
      }
      toolPage.toggleSideContentMode();
    },

    onNavigationItemSelect: function (event) {
      var item = event.getParameter("item");
      if (!item) {
        return;
      }
      var route = item.getKey();
      if (!route) {
        return;
      }
      this._router.navTo(route, {}, false);
      if (Device.system.phone) {
        var toolPage = this.byId("toolPage");
        if (toolPage) {
          toolPage.setSideExpanded(false);
        }
      }
    },

    _onRouteMatched: function (event) {
      var routeName = event.getParameter("name");
      var model = this.getView().getModel("appModel");
      if (!model) {
        return;
      }
      model.setProperty("/selectedKey", routeName);
    }
  });
});