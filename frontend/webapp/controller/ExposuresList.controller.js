sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/exposuresService",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator"
], function (BaseController, exposuresService, Filter, FilterOperator) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.ExposuresList", {
    onInit: function () {
      this.initViewModel("exp", {
        engineItems: [],
        netItems: [],
        reconcileMessage: ""
      });

      var oRouter = this.getRouter();
      oRouter.getRoute("exposures").attachPatternMatched(this._onRouteMatched, this);
      oRouter.getRoute("exposureDetail").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this._loadExposures();
      this._loadNetExposure();
    },

    _loadExposures: function () {
      var that = this;
      this.loadData(function () {
        return exposuresService.listExposures();
      }, "/rawEngineResponse").then(function (oData) {
        if (oData && oData.items) {
          that.getViewModel().setProperty("/engineItems", oData.items);
        }
      });
    },

    _loadNetExposure: function () {
      var that = this;
      this.loadData(function () {
        return exposuresService.getNet();
      }, "/rawNetResponse").then(function (oData) {
        if (oData && oData.items) {
          that.getViewModel().setProperty("/netItems", oData.items);
        }
      });
    },

    onRefresh: function () {
      this._loadExposures();
      this._loadNetExposure();
    },

    onReconcile: function () {
      var that = this;
      this.submitData(function () {
        return exposuresService.reconcile();
      }, this.getI18nText("reconcileSuccess")).then(function (oData) {
        if (oData) {
          that.getViewModel().setProperty("/reconcileMessage",
            that.getI18nText("reconcileResultDetail", [oData.message || "", oData.created || 0, oData.updated || 0])
          );
          that._loadExposures();
          that._loadNetExposure();
        }
      });
    },

    onExposureSelect: function (oEvent) {
      var oItem = oEvent.getParameter("listItem");
      var oCtx = oItem.getBindingContext("exp");
      var sId = oCtx.getProperty("id");
      this.navToDetail("exposureDetail", { exposureId: sId });
    },

    onSearch: function (oEvent) {
      var sQuery = oEvent.getParameter("query");
      var aFilters = [];
      if (sQuery) {
        aFilters = [new Filter({
          filters: [
            new Filter("commodity", FilterOperator.Contains, sQuery),
            new Filter("settlement_month", FilterOperator.Contains, sQuery)
          ],
          and: false
        })];
      }
      this.byId("exposureList").getBinding("items").filter(aFilters);
    }
  });
});
