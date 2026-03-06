sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "sap/ui/Device",
  "sap/f/library",
  "sap/m/MessageToast",
  "sap/m/ActionSheet",
  "sap/m/Button"
], function (BaseController, Device, fioriLibrary, MessageToast, ActionSheet, Button) {
  "use strict";

  var LayoutType = fioriLibrary.LayoutType;

  /**
   * Map route names to the nav key that should be highlighted.
   */
  var ROUTE_TO_NAV = {
    home: "home",
    exposures: "exposures",
    exposureDetail: "exposures",
    orders: "orders",
    orderCreate: "orders",
    orderDetail: "orders",
    rfq: "rfq",
    rfqCreate: "rfq",
    rfqDetail: "rfq",
    contracts: "contracts",
    contractCreate: "contracts",
    contractDetail: "contracts",
    deals: "orders",
    dealCreate: "orders",
    dealDetail: "orders",
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
    orderCreate: LayoutType.MidColumnFullScreen,
    rfqDetail: LayoutType.TwoColumnsMidExpanded,
    rfqCreate: LayoutType.MidColumnFullScreen,
    rfqDocument: LayoutType.ThreeColumnsMidExpanded,
    contractDetail: LayoutType.TwoColumnsMidExpanded,
    contractCreate: LayoutType.MidColumnFullScreen,
    exposureDetail: LayoutType.TwoColumnsMidExpanded,
    dealDetail: LayoutType.TwoColumnsMidExpanded,
    dealCreate: LayoutType.MidColumnFullScreen,
    counterpartyDetail: LayoutType.TwoColumnsMidExpanded,
    counterpartyCreate: LayoutType.MidColumnFullScreen,
    linkageDetail: LayoutType.TwoColumnsMidExpanded
  };

  /** Map title‑menu item text keys to route names. */
  var TITLE_MENU_ROUTES = {
    navOverview: "home",
    navExposures: "exposures",
    navComercial: "orders",
    navRfq: "rfq",
    navContracts: "contracts"
  };

  return BaseController.extend("hedgecontrol.controller.App", {
    onInit: function () {
      this._router = this.getRouter();
      this._router.attachRouteMatched(this._onRouteMatched, this);
      this._applyInitialSideState();
      this._initAppModelDefaults();
    },

    /**
     * Set default dynamic properties for the ShellBar.
     */
    _initAppModelDefaults: function () {
      var appModel = this.getAppModel();
      appModel.setProperty("/showNavButton", false);
      appModel.setProperty("/notificationsCount", "");
      appModel.setProperty("/userInitials", "AU");
    },

    _applyInitialSideState: function () {
      var toolPage = this.byId("toolPage");
      if (toolPage) {
        toolPage.setSideExpanded(!Device.system.phone);
      }
    },

    /* ── ShellBar event handlers ────────────────────────────── */

    onMenuButtonPressed: function () {
      var toolPage = this.byId("toolPage");
      if (toolPage) {
        toolPage.toggleSideContentMode();
      }
    },

    onNavButtonPressed: function () {
      window.history.go(-1);
    },

    onHomeIconPressed: function () {
      this.getAppModel().setProperty("/layout", LayoutType.OneColumn);
      this._router.navTo("home");
    },

    onNotificationsPressed: function (oEvent) {
      MessageToast.show(this.getI18nText("shellbarNoNotifications"));
    },

    onAvatarPressed: function (oEvent) {
      var oButton = oEvent.getParameter("avatar");
      if (!this._oUserMenu) {
        this._oUserMenu = new ActionSheet({
          showCancelButton: Device.system.phone,
          buttons: [
            new Button({ text: this.getI18nText("shellbarUserSettings"), icon: "sap-icon://action-settings", press: function () { MessageToast.show(this.getI18nText("shellbarUserSettings")); }.bind(this) }),
            new Button({ text: this.getI18nText("shellbarUserLogout"), icon: "sap-icon://log", press: function () { MessageToast.show(this.getI18nText("shellbarUserLogout")); }.bind(this) })
          ]
        });
        this.getView().addDependent(this._oUserMenu);
      }
      this._oUserMenu.openBy(oButton);
    },

    onHelpPressed: function () {
      MessageToast.show(this.getI18nText("shellbarHelpMsg"));
    },

    onShellSearch: function (oEvent) {
      var sQuery = oEvent.getParameter("query");
      if (sQuery) {
        MessageToast.show(this.getI18nText("search") + ": " + sQuery);
      }
    },

    onTitleMenuAction: function (oEvent) {
      var oItem = oEvent.getSource();
      var sText = oItem.getText();
      var that = this;
      var sRoute;

      Object.keys(TITLE_MENU_ROUTES).some(function (key) {
        if (that.getI18nText(key) === sText) {
          sRoute = TITLE_MENU_ROUTES[key];
          return true;
        }
        return false;
      });

      if (sRoute) {
        this.getAppModel().setProperty("/layout", LayoutType.OneColumn);
        this._router.navTo(sRoute);
      }
    },

    /* ── Side Navigation ────────────────────────────────────── */

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

    /* ── Route handling ─────────────────────────────────────── */

    _onRouteMatched: function (event) {
      var routeName = event.getParameter("name");
      var appModel = this.getAppModel();

      // Set FCL layout
      var layout = ROUTE_TO_LAYOUT[routeName] || LayoutType.OneColumn;
      appModel.setProperty("/layout", layout);

      // Set nav highlight
      var selectedKey = ROUTE_TO_NAV[routeName] || routeName;
      appModel.setProperty("/selectedKey", selectedKey);

      // Show nav-back button when inside a detail/create view
      var bShowBack = !!ROUTE_TO_LAYOUT[routeName];
      appModel.setProperty("/showNavButton", bShowBack);
    }
  });
});
