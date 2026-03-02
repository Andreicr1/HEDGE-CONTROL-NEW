sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/rfqService",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator",
  "sap/ui/core/Fragment",
  "sap/m/MessageBox",
  "sap/m/MessageToast"
], function (BaseController, rfqService, Filter, FilterOperator, Fragment, MessageBox, MessageToast) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.RfqList", {
    onInit: function () {
      this.initViewModel("rfq", {
        items: []
      });
      // Create model also used by the creation dialog
      this._initCreateModel();
      this.getRouter().getRoute("rfq").attachPatternMatched(this._onRouteMatched, this);
      this.getRouter().getRoute("rfqDetail").attachPatternMatched(this._onRouteMatched, this);
      this.getRouter().getRoute("rfqDocument").attachPatternMatched(this._onRouteMatched, this);
    },

    _initCreateModel: function () {
      var oModel = new sap.ui.model.json.JSONModel({
        intent: "SPREAD",
        commodity: "",
        direction: "BUY",
        quantity_mt: "",
        delivery_window_start: "",
        delivery_window_end: "",
        order_id: ""
      });
      this.getView().setModel(oModel, "rfqCrt");
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

    /* ─── Create RFQ Dialog ─── */

    onCreateRfq: function () {
      var that = this;
      if (!this._pCreateDialog) {
        this._pCreateDialog = Fragment.load({
          id: this.getView().getId(),
          name: "hedgecontrol.view.fragment.RfqCreateDialog",
          controller: this
        }).then(function (oDialog) {
          that.getView().addDependent(oDialog);
          return oDialog;
        });
      }
      this._pCreateDialog.then(function (oDialog) {
        that._resetCreateModel();
        oDialog.open();
      });
    },

    _resetCreateModel: function () {
      this.getView().getModel("rfqCrt").setData({
        intent: "SPREAD",
        commodity: "",
        direction: "BUY",
        quantity_mt: "",
        delivery_window_start: "",
        delivery_window_end: "",
        order_id: ""
      });
    },

    onSubmitRfq: function () {
      var that = this;
      var oData = this.getView().getModel("rfqCrt").getData();

      // Basic validation
      if (!oData.commodity || !oData.quantity_mt || !oData.delivery_window_start || !oData.delivery_window_end) {
        MessageBox.warning(this.getI18nText("validationRequiredFields"));
        return;
      }

      var oPayload = {
        intent: oData.intent,
        commodity: oData.commodity,
        direction: oData.direction,
        quantity_mt: parseFloat(oData.quantity_mt),
        delivery_window_start: oData.delivery_window_start,
        delivery_window_end: oData.delivery_window_end,
        order_id: oData.order_id || undefined
      };

      this.submitData(function () {
        return rfqService.create(oPayload);
      }, this.getI18nText("rfqCreated")).then(function (oResult) {
        if (oResult) {
          that._pCreateDialog.then(function (oDialog) { oDialog.close(); });
          that._loadRfqs();
          if (oResult.id) {
            that.navToDetail("rfqDetail", { rfqId: oResult.id });
          }
        }
      });
    },

    onCancelCreateRfq: function () {
      this._pCreateDialog.then(function (oDialog) { oDialog.close(); });
    }
  });
});
