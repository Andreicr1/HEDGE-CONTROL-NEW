sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/dealsService",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator"
], function (BaseController, dealsService, Filter, FilterOperator) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.DealsList", {
    onInit: function () {
      this.initViewModel("deals", {
        items: []
      });
      this.getRouter().getRoute("deals").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this._loadData();
    },

    _loadData: function () {
      var that = this;
      this.loadData(function () {
        return dealsService.list();
      }, "/rawResponse").then(function (oData) {
        if (oData && oData.items) {
          that.getViewModel().setProperty("/items", oData.items);
        }
      });
    },

    onRefresh: function () {
      this._loadData();
    },

    onSearch: function (oEvent) {
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
      this.byId("dealsTable").getBinding("items").filter(aFilters);
    },

    onDealSelect: function (oEvent) {
      var oItem = oEvent.getParameter("listItem");
      var sId = oItem.getBindingContext("deals").getProperty("id");
      this.navToDetail("dealDetail", { dealId: sId });
    },

    onCreateDeal: function () {
      this.navToDetail("dealCreate");
    }
  });
});
