sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/contractsService",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator"
], function (BaseController, contractsService, Filter, FilterOperator) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.ContractsList", {

    onInit: function () {
      this.initViewModel("ctr", { items: [] });
      this.getRouter().getRoute("contracts").attachPatternMatched(this._onRouteMatched, this);
      this.getRouter().getRoute("contractDetail").attachPatternMatched(this._onRouteMatched, this);
      this.getRouter().getRoute("contractCreate").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this._loadContracts();
    },

    _loadContracts: function () {
      var oModel = this.getViewModel();
      oModel.setProperty("/busy", true);
      contractsService.list().then(function (oResponse) {
        oModel.setProperty("/items", oResponse.items || []);
      }).catch(function (oError) {
        oModel.setProperty("/errorMessage", this._formatError(oError));
      }.bind(this)).finally(function () {
        oModel.setProperty("/busy", false);
      });
    },

    onSearch: function (oEvent) {
      var sQuery = oEvent.getParameter("newValue");
      var oTable = this.byId("contractsTable");
      var oBinding = oTable.getBinding("items");
      if (!sQuery) {
        oBinding.filter([]);
        return;
      }
      var aFilters = [
        new Filter("commodity", FilterOperator.Contains, sQuery),
        new Filter("counterparty_id", FilterOperator.Contains, sQuery),
        new Filter("classification", FilterOperator.Contains, sQuery),
        new Filter("status", FilterOperator.Contains, sQuery)
      ];
      oBinding.filter(new Filter({ filters: aFilters, and: false }));
    },

    onContractSelect: function (oEvent) {
      var oItem = oEvent.getParameter("listItem");
      var sId = oItem.getBindingContext("ctr").getProperty("id");
      this.navToDetail("contractDetail", { contractId: sId });
    },

    onCreateContract: function () {
      this.navToDetail("contractCreate", {});
    },

    formatClassificationState: function (sClassification) {
      if (!sClassification) { return "None"; }
      return sClassification === "long" ? "Success" : "Error";
    }
  });
});
