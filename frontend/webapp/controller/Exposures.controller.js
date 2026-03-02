sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/exposuresService",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator",
  "sap/m/MessageBox"
], function (BaseController, exposuresService, Filter, FilterOperator, MessageBox) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.Exposures", {
    onInit: function () {
      this.initViewModel("exp", {
        commercial: [],
        global: [],
        engineItems: [],
        netItems: [],
        tasks: [],
        reconcileResult: null
      });
      this._loadLegacy();
    },

    _loadLegacy: function () {
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

    _loadEngineExposures: function () {
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
      exposuresService.getNet().then(function (oData) {
        if (oData && oData.items) {
          that.getViewModel().setProperty("/netItems", oData.items);
        }
      }).catch(function () {
        that.getViewModel().setProperty("/netItems", []);
      });
    },

    _loadTasks: function () {
      var that = this;
      exposuresService.listTasks().then(function (oData) {
        if (oData && oData.items) {
          that.getViewModel().setProperty("/tasks", oData.items);
        }
      }).catch(function () {
        that.getViewModel().setProperty("/tasks", []);
      });
    },

    onRefresh: function () {
      var sKey = this.byId("exposuresTabBar").getSelectedKey();
      if (sKey === "commercial" || sKey === "global") {
        this._loadLegacy();
      } else if (sKey === "engine") {
        this._loadEngineExposures();
        this._loadNetExposure();
      } else if (sKey === "tasks") {
        this._loadTasks();
      }
    },

    onTabSelect: function (oEvent) {
      var sKey = oEvent.getParameter("key");
      if (sKey === "engine") {
        this._loadEngineExposures();
        this._loadNetExposure();
      } else if (sKey === "tasks") {
        this._loadTasks();
      }
    },

    onReconcile: function () {
      var that = this;
      this.submitData(function () {
        return exposuresService.reconcile();
      }, this.getI18nText("reconcileSuccess")).then(function (oData) {
        if (oData) {
          that.getViewModel().setProperty("/reconcileResult", oData);
          that._loadEngineExposures();
          that._loadNetExposure();
          that._loadTasks();
        }
      });
    },

    onExecuteTask: function (oEvent) {
      var oCtx = oEvent.getSource().getBindingContext("exp");
      var sTaskId = oCtx.getProperty("id");
      var that = this;
      MessageBox.confirm(this.getI18nText("confirmExecuteTask"), {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            that.submitData(function () {
              return exposuresService.executeTask(sTaskId);
            }, that.getI18nText("taskExecuted")).then(function () {
              that._loadTasks();
            });
          }
        }
      });
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

    onSearchEngine: function (oEvent) {
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
      this.byId("engineTable").getBinding("items").filter(aFilters);
    }
  });
});
