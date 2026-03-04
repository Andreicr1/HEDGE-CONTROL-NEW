sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/rfqService",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator",
  "sap/m/MessageBox",
  "sap/m/MessageToast"
], function (BaseController, rfqService, Filter, FilterOperator, MessageBox, MessageToast) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.RfqList", {
    onInit: function () {
      this.initViewModel("rfq", {
        items: []
      });
      this.getRouter().getRoute("rfq").attachPatternMatched(this._onRouteMatched, this);
      this.getRouter().getRoute("rfqDetail").attachPatternMatched(this._onRouteMatched, this);
      this.getRouter().getRoute("rfqDocument").attachPatternMatched(this._onRouteMatched, this);
      this.getRouter().getRoute("rfqCreate").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this._loadRfqs();
    },

    _loadRfqs: function () {
      var that = this;
      this.loadData(function () {
        return rfqService.list();
      }, "/rawResponse").then(function (oData) {
        if (oData && oData.items) {
          that.getViewModel().setProperty("/items", oData.items);
        }
      });
    },

    onRefresh: function () {
      this._loadRfqs();
    },

    onSearch: function (oEvent) {
      var sQuery = oEvent.getParameter("newValue") || oEvent.getParameter("query") || "";
      var aFilters = [];
      if (sQuery) {
        aFilters = [new Filter({
          filters: [
            new Filter("rfq_number", FilterOperator.Contains, sQuery),
            new Filter("commodity", FilterOperator.Contains, sQuery),
            new Filter("state", FilterOperator.Contains, sQuery)
          ],
          and: false
        })];
      }
      this.byId("rfqTable").getBinding("items").filter(aFilters);
    },

    onRfqSelect: function (oEvent) {
      var oItem = oEvent.getParameter("listItem");
      var sId = oItem.getBindingContext("rfq").getProperty("id");
      this.navToDetail("rfqDetail", { rfqId: sId });
    },

    onCreateRfq: function () {
      this.getRouter().navTo("rfqCreate");
    }
  });
});
