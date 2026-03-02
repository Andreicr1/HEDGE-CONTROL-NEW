sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/hedgesService",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator"
], function (BaseController, hedgesService, Filter, FilterOperator) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.HedgesList", {
    onInit: function () {
      this.initViewModel("hdg", {
        items: []
      });
      this.getRouter().getRoute("hedges").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this._loadData();
    },

    _loadData: function () {
      var that = this;
      this.loadData(function () {
        return hedgesService.list();
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
            new Filter("commodity", FilterOperator.Contains, sQuery)
          ],
          and: false
        })];
      }
      this.byId("hedgesTable").getBinding("items").filter(aFilters);
    },

    onHedgeSelect: function (oEvent) {
      var oItem = oEvent.getParameter("listItem");
      var sId = oItem.getBindingContext("hdg").getProperty("id");
      this.navToDetail("hedgeDetail", { hedgeId: sId });
    },

    onCreateHedge: function () {
      this.navToDetail("hedgeCreate");
    }
  });
});
