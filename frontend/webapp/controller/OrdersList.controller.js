sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/ordersService",
  "hedgecontrol/service/dealsService",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator"
], function (BaseController, ordersService, dealsService, Filter, FilterOperator) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.OrdersList", {
    onInit: function () {
      this.initViewModel("ord", {
        items: [],
        deals: [],
        salesOrders: [],
        purchaseOrders: [],
        dealsCount: "0",
        soCount: "0",
        poCount: "0",
        selectedTab: "deals"
      });
      this.getRouter().getRoute("orders").attachPatternMatched(this._onRouteMatched, this);
      this.getRouter().getRoute("deals").attachPatternMatched(this._onRouteMatchedDeals, this);
    },

    _onRouteMatched: function () {
      this._loadAll();
    },

    _onRouteMatchedDeals: function () {
      this.getViewModel().setProperty("/selectedTab", "deals");
      this._loadAll();
    },

    _loadAll: function () {
      this._loadOrders();
      this._loadDeals();
    },

    _loadOrders: function () {
      var that = this;
      ordersService.list().then(function (oData) {
        var aItems = (oData && oData.items) || [];
        var aSO = aItems.filter(function (o) { return o.order_type === "SO"; });
        var aPO = aItems.filter(function (o) { return o.order_type === "PO"; });
        var oModel = that.getViewModel();
        oModel.setProperty("/items", aItems);
        oModel.setProperty("/salesOrders", aSO);
        oModel.setProperty("/purchaseOrders", aPO);
        oModel.setProperty("/soCount", String(aSO.length));
        oModel.setProperty("/poCount", String(aPO.length));
      }).catch(function (oError) {
        that.getViewModel().setProperty("/errorMessage", that._formatError(oError));
      });
    },

    _loadDeals: function () {
      var that = this;
      dealsService.list().then(function (oData) {
        var aItems = (oData && oData.items) || [];
        var oModel = that.getViewModel();
        oModel.setProperty("/deals", aItems);
        oModel.setProperty("/dealsCount", String(aItems.length));
      }).catch(function (oError) {
        that.getViewModel().setProperty("/errorMessage", that._formatError(oError));
      });
    },

    onRefresh: function () {
      this._loadAll();
    },

    onTabSelect: function () {
      // Tab switch handled by binding; no-op unless special logic needed
    },

    // ── Deal search & navigation ──
    onSearchDeals: function (oEvent) {
      var sQuery = oEvent.getParameter("query");
      var aFilters = [];
      if (sQuery) {
        aFilters = [new Filter({
          filters: [
            new Filter("reference", FilterOperator.Contains, sQuery),
            new Filter("name", FilterOperator.Contains, sQuery),
            new Filter("commodity", FilterOperator.Contains, sQuery)
          ],
          and: false
        })];
      }
      this.byId("dealsTabList").getBinding("items").filter(aFilters);
    },

    onDealSelect: function (oEvent) {
      var oItem = oEvent.getParameter("listItem");
      var sId = oItem.getBindingContext("ord").getProperty("id");
      this.navToDetail("dealDetail", { dealId: sId });
    },

    onCreateDeal: function () {
      this.getRouter().navTo("dealCreate");
    },

    // ── SO search & navigation ──
    onSearchSO: function (oEvent) {
      var sQuery = oEvent.getParameter("query");
      var aFilters = [];
      if (sQuery) {
        aFilters = [new Filter({
          filters: [
            new Filter("price_type", FilterOperator.Contains, sQuery)
          ],
          and: false
        })];
      }
      this.byId("soList").getBinding("items").filter(aFilters);
    },

    // ── PO search ──
    onSearchPO: function (oEvent) {
      var sQuery = oEvent.getParameter("query");
      var aFilters = [];
      if (sQuery) {
        aFilters = [new Filter({
          filters: [
            new Filter("price_type", FilterOperator.Contains, sQuery)
          ],
          and: false
        })];
      }
      this.byId("poList").getBinding("items").filter(aFilters);
    },

    // ── Order navigation ──
    onOrderSelect: function (oEvent) {
      var oItem = oEvent.getParameter("listItem");
      var sId = oItem.getBindingContext("ord").getProperty("id");
      this.navToDetail("orderDetail", { orderId: sId });
    },

    onCreateSales: function () {
      this.navToDetail("orderCreate", { type: "sales" });
    },

    onCreatePurchase: function () {
      this.navToDetail("orderCreate", { type: "purchase" });
    }
  });
});
