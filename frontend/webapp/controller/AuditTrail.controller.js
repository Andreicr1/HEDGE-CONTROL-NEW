sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/auditService",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator",
  "sap/m/MessageBox"
], function (BaseController, auditService, Filter, FilterOperator, MessageBox) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.AuditTrail", {
    onInit: function () {
      this.initViewModel("audit", {
        events: [],
        entityTypeFilter: "",
        verifyResult: null
      });
      this.getRouter().getRoute("auditTrail").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this._loadEvents();
    },

    _loadEvents: function () {
      var oModel = this.getViewModel();
      var sEntityType = oModel.getProperty("/entityTypeFilter");
      var oFilters = {};
      if (sEntityType) {
        oFilters.entity_type = sEntityType;
      }

      var that = this;
      this.loadData(function () {
        return auditService.listEvents(oFilters);
      }, "/rawResponse").then(function (oData) {
        if (oData && oData.events) {
          that.getViewModel().setProperty("/events", oData.events);
        }
      });
    },

    onRefresh: function () {
      this._loadEvents();
    },

    onFilterChange: function () {
      this._loadEvents();
    },

    onSearch: function (oEvent) {
      var sQuery = oEvent.getParameter("query");
      var aFilters = [];
      if (sQuery) {
        aFilters = [new Filter({
          filters: [
            new Filter("entity_type", FilterOperator.Contains, sQuery),
            new Filter("event_type", FilterOperator.Contains, sQuery)
          ],
          and: false
        })];
      }
      this.byId("auditTable").getBinding("items").filter(aFilters);
    },

    onVerify: function (oEvent) {
      var oCtx = oEvent.getSource().getBindingContext("audit");
      var sEventId = oCtx.getProperty("id");
      var that = this;

      that.getViewModel().setProperty("/verifyResult", null);
      auditService.verifyEvent(sEventId).then(function (oResult) {
        that.getViewModel().setProperty("/verifyResult", oResult);
        if (oResult.valid) {
          MessageBox.success(that.getI18nText("auditVerifyValid"));
        } else {
          MessageBox.warning(oResult.detail || that.getI18nText("auditVerifyInvalid"));
        }
      }).catch(function (oError) {
        MessageBox.error(that._formatError(oError));
      });
    },

    onTogglePayload: function (oEvent) {
      var oPanel = oEvent.getSource().getParent();
      if (oPanel && oPanel.getExpanded) {
        oPanel.setExpanded(!oPanel.getExpanded());
      }
    }
  });
});
