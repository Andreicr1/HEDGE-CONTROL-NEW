sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/financePipelineService",
  "sap/m/MessageBox"
], function (BaseController, financePipelineService, MessageBox) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.FinancePipeline", {
    onInit: function () {
      this.initViewModel("fp", {
        runs: [],
        selectedRun: null,
        runDate: ""
      });
      this.getRouter().getRoute("financePipeline").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this._loadRuns();
    },

    _loadRuns: function () {
      var that = this;
      this.loadData(function () {
        return financePipelineService.listRuns();
      }, "/rawResponse").then(function (oData) {
        if (oData && oData.items) {
          that.getViewModel().setProperty("/runs", oData.items);
        }
      });
    },

    onRefresh: function () {
      this._loadRuns();
      this.getViewModel().setProperty("/selectedRun", null);
    },

    onTriggerPipeline: function () {
      var oModel = this.getViewModel();
      var sDate = oModel.getProperty("/runDate");

      if (!sDate) {
        MessageBox.warning(this.getI18nText("pipelineDateRequired"));
        return;
      }

      var that = this;
      this.submitData(function () {
        return financePipelineService.triggerRun(sDate);
      }, this.getI18nText("pipelineTriggered")).then(function () {
        that._loadRuns();
      });
    },

    onRunSelect: function (oEvent) {
      var oItem = oEvent.getParameter("listItem");
      var sRunId = oItem.getBindingContext("fp").getProperty("id");
      var that = this;

      financePipelineService.getRunDetail(sRunId).then(function (oData) {
        that.getViewModel().setProperty("/selectedRun", oData);
      }).catch(function (oError) {
        MessageBox.error(that._formatError(oError));
      });
    },

    onCloseDetail: function () {
      this.getViewModel().setProperty("/selectedRun", null);
    },

    formatDuration: function (sStart, sEnd) {
      if (!sStart) { return ""; }
      var dStart = new Date(sStart);
      var dEnd = sEnd ? new Date(sEnd) : new Date();
      var iDiff = Math.round((dEnd - dStart) / 1000);
      if (iDiff < 60) { return iDiff + "s"; }
      return Math.floor(iDiff / 60) + "m " + (iDiff % 60) + "s";
    },

    formatProgress: function (iCompleted, iTotal) {
      if (!iTotal) { return "0%"; }
      return Math.round((iCompleted / iTotal) * 100) + "%";
    }
  });
});
