sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "sap/ui/Device",
  "sap/f/library"
], function (BaseController, Device, fioriLibrary) {
  "use strict";

  var LayoutType = fioriLibrary.LayoutType;

  /**
   * Map route names to the nav key that should be highlighted.
   */
  var ROUTE_TO_NAV = {
    home: "home",
    exposures: "exposures",
    orders: "orders",
    orderCreate: "orders",
    orderDetail: "orders",
    rfq: "rfq",
    rfqCreate: "rfq",
    rfqDetail: "rfq",
    contracts: "contracts",
    contractCreate: "contracts",
    contractDetail: "contracts",
    hedges: "hedges",
    hedgeCreate: "hedges",
    hedgeDetail: "hedges",
    deals: "deals",
    dealCreate: "deals",
    dealDetail: "deals",
    counterparties: "counterparties",
    counterpartyCreate: "counterparties",
    counterpartyDetail: "counterparties",
    linkages: "linkages",
    linkageDetail: "linkages",
    cashflow: "cashflow",
    pnl: "pnl",
    scenario: "scenario",
    mtm: "mtm",
    auditTrail: "auditTrail",
    financePipeline: "financePipeline",
    marketData: "marketData"
  };

  /**
   * Map route names to FCL layout.
   */
  var ROUTE_TO_LAYOUT = {
    orderDetail: LayoutType.TwoColumnsMidExpanded,
    orderCreate: LayoutType.EndColumnFullScreen,
    rfqDetail: LayoutType.TwoColumnsMidExpanded,
    rfqDocument: LayoutType.ThreeColumnsMidExpanded,
    contractDetail: LayoutType.TwoColumnsMidExpanded,
    contractCreate: LayoutType.EndColumnFullScreen,
    hedgeDetail: LayoutType.TwoColumnsMidExpanded,
    hedgeCreate: LayoutType.EndColumnFullScreen,
    dealDetail: LayoutType.TwoColumnsMidExpanded,
    dealCreate: LayoutType.EndColumnFullScreen,
    counterpartyDetail: LayoutType.TwoColumnsMidExpanded,
    counterpartyCreate: LayoutType.EndColumnFullScreen,
    linkageDetail: LayoutType.TwoColumnsMidExpanded
  };

  return BaseController.extend("hedgecontrol.controller.App", {
    onInit: function () {
      this._router = this.getRouter();
      this._router.attachRouteMatched(this._onRouteMatched, this);
      this._applyInitialSideState();
    },

    _applyInitialSideState: function () {
      var toolPage = this.byId("toolPage");
      if (toolPage) {
        toolPage.setSideExpanded(!Device.system.phone);
      }
    },

    onMenuButtonPressed: function () {
      var toolPage = this.byId("toolPage");
      if (toolPage) {
        toolPage.toggleSideContentMode();
      }
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
      this.getAppModel().setProperty("/layout", LayoutType.OneColumn);
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
      var appModel = this.getAppModel();

      // Set FCL layout
      var layout = ROUTE_TO_LAYOUT[routeName] || LayoutType.OneColumn;
      appModel.setProperty("/layout", layout);

      // Set nav highlight
      var selectedKey = ROUTE_TO_NAV[routeName] || routeName;
      appModel.setProperty("/selectedKey", selectedKey);
    }
  });
});
