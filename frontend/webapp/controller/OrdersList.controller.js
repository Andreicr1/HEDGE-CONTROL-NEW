sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/ordersService",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator"
], function (BaseController, ordersService, Filter, FilterOperator) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.OrdersList", {
    onInit: function () {
      this.initViewModel("ord", {
        items: []
      });
      this.getRouter().getRoute("orders").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this._loadOrders();
    },

    _loadOrders: function () {
      var that = this;
      this.loadData(function () {
        return ordersService.list();
      }, "/rawResponse").then(function (oData) {
        if (oData && oData.items) {
          that.getViewModel().setProperty("/items", oData.items);
        }
      });
    },

    onRefresh: function () {
      this._loadOrders();
    },

    onSearch: function (oEvent) {
      var sQuery = oEvent.getParameter("query");
      var aFilters = [];
      if (sQuery) {
        aFilters = [new Filter({
          filters: [
            new Filter("order_type", FilterOperator.Contains, sQuery),
            new Filter("price_type", FilterOperator.Contains, sQuery)
          ],
          and: false
        })];
      }
      this.byId("ordersList").getBinding("items").filter(aFilters);
    },

    onOrderSelect: function (oEvent) {
      var oItem = oEvent.getParameter("listItem");
      var sId = oItem.getBindingContext("ord").getProperty("id");
      this.navToDetail("orderDetail", { orderId: sId });
    },

    onCreateSales: function () {
      this.getRouter().navTo("orderCreate", { type: "sales" });
    },

    onCreatePurchase: function () {
      this.getRouter().navTo("orderCreate", { type: "purchase" });
    }
  });
});
