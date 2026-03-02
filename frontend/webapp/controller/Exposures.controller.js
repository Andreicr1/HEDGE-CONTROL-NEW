sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/exposuresService",
  "sap/ui/model/json/JSONModel",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator"
], function (BaseController, exposuresService, JSONModel, Filter, FilterOperator) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.Exposures", {
    onInit: function () {
      this.initViewModel("exp", {
        commercial: [],
        global: []
      });
      this._loadExposures();
    },

    _loadExposures: function () {
      var oModel = this.getViewModel();
      oModel.setProperty("/busy", true);
      oModel.setProperty("/errorMessage", "");

      var that = this;
      Promise.all([
        exposuresService.getCommercial(),
        exposuresService.getGlobal()
      ]).then(function (aResults) {
        oModel.setProperty("/commercial", aResults[0] || []);
        oModel.setProperty("/global", aResults[1] || []);
      }).catch(function (oError) {
        oModel.setProperty("/errorMessage", that._formatError(oError));
      }).finally(function () {
        oModel.setProperty("/busy", false);
      });
    },

    onRefresh: function () {
      this._loadExposures();
    },

    onSearchCommercial: function (oEvent) {
      var sQuery = oEvent.getParameter("query");
      var aFilters = sQuery ? [new Filter("commodity", FilterOperator.Contains, sQuery)] : [];
      this.byId("commercialTable").getBinding("items").filter(aFilters);
    },

    onSearchGlobal: function (oEvent) {
      var sQuery = oEvent.getParameter("query");
      var aFilters = sQuery ? [new Filter("commodity", FilterOperator.Contains, sQuery)] : [];
      this.byId("globalTable").getBinding("items").filter(aFilters);
    },

    onTabSelect: function () {
      // placeholder for tab-specific logic
    }
  });
});
