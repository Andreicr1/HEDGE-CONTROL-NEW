sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/counterpartiesService",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator"
], function (BaseController, counterpartiesService, Filter, FilterOperator) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.CounterpartiesList", {
    onInit: function () {
      this.initViewModel("cpty", {
        items: []
      });
      this.getRouter().getRoute("counterparties").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this._loadData();
    },

    _loadData: function () {
      var that = this;
      this.loadData(function () {
        return counterpartiesService.list();
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
            new Filter("name", FilterOperator.Contains, sQuery),
            new Filter("short_name", FilterOperator.Contains, sQuery),
            new Filter("tax_id", FilterOperator.Contains, sQuery)
          ],
          and: false
        })];
      }
      this.byId("counterpartiesTable").getBinding("items").filter(aFilters);
    },

    onCounterpartySelect: function (oEvent) {
      var oItem = oEvent.getParameter("listItem");
      var sId = oItem.getBindingContext("cpty").getProperty("id");
      this.navToDetail("counterpartyDetail", { counterpartyId: sId });
    },

    onCreateCounterparty: function () {
      this.navToDetail("counterpartyCreate");
    }
  });
});
