sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/contractsService",
  "hedgecontrol/service/counterpartiesService",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator"
], function (BaseController, contractsService, counterpartiesService, Filter, FilterOperator) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.ContractsList", {

    onInit: function () {
      this.initViewModel("ctr", { items: [] });
      this._oCounterpartyMap = {};
      this.getRouter().getRoute("contracts").attachPatternMatched(this._onRouteMatched, this);
      this.getRouter().getRoute("contractDetail").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this._loadCounterparties().then(this._loadContracts.bind(this));
    },

    /* ── counterparty map ── */
    _loadCounterparties: function () {
      var that = this;
      return counterpartiesService.list({ limit: 200 }).then(function (oRes) {
        var aItems = oRes.items || oRes || [];
        that._oCounterpartyMap = {};
        aItems.forEach(function (o) {
          that._oCounterpartyMap[o.id] = o.short_name || o.name || o.id;
        });
      }).catch(function () { /* keep empty map */ });
    },

    _resolveCounterpartyNames: function (aItems) {
      var oMap = this._oCounterpartyMap;
      return aItems.map(function (o) {
        o._counterparty_name = oMap[o.counterparty_id] || o.counterparty_id || "";
        return o;
      });
    },

    /* ── contracts ── */
    _loadContracts: function () {
      var oModel = this.getViewModel();
      oModel.setProperty("/busy", true);
      contractsService.list().then(function (oResponse) {
        var aItems = oResponse.items || [];
        oModel.setProperty("/items", this._resolveCounterpartyNames(aItems));
      }.bind(this)).catch(function (oError) {
        oModel.setProperty("/errorMessage", this._formatError(oError));
      }.bind(this)).finally(function () {
        oModel.setProperty("/busy", false);
      });
    },

    onSearch: function (oEvent) {
      var sQuery = oEvent.getParameter("newValue");
      var oList = this.byId("contractsList");
      var oBinding = oList.getBinding("items");
      if (!sQuery) {
        oBinding.filter([]);
        return;
      }
      var aFilters = [
        new Filter("commodity", FilterOperator.Contains, sQuery),
        new Filter("_counterparty_name", FilterOperator.Contains, sQuery),
        new Filter("reference", FilterOperator.Contains, sQuery),
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
      this.getRouter().navTo("contractCreate");
    }
  });
});
