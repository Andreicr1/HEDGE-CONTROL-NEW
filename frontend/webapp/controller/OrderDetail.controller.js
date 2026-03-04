sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/ordersService",
  "hedgecontrol/service/dealsService",
  "sap/m/MessageBox"
], function (BaseController, ordersService, dealsService, MessageBox) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.OrderDetail", {
    onInit: function () {
      this.initViewModel("ordDet", {
        detail: {},
        deal: null
      });
      this.getRouter().getRoute("orderDetail").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (oEvent) {
      var sOrderId = oEvent.getParameter("arguments").orderId;
      this._sOrderId = sOrderId;
      this._loadOrder(sOrderId);
    },

    _loadOrder: function (sOrderId) {
      var that = this;
      this.loadData(function () {
        return ordersService.getById(sOrderId);
      }, "/detail").then(function () {
        that._loadDeal();
      });
    },

    _loadDeal: function () {
      var that = this;
      var oDetail = this.getViewModel().getProperty("/detail");
      if (!oDetail || !oDetail.id) { return; }
      var sLinkedType = oDetail.order_type === "SO" ? "sales_order" : "purchase_order";
      dealsService.findByLinkedEntity(sLinkedType, oDetail.id).then(function (oDeal) {
        that.getViewModel().setProperty("/deal", oDeal || null);
      }).catch(function () {
        that.getViewModel().setProperty("/deal", null);
      });
    },

    onNavigateToDeal: function () {
      var oDeal = this.getViewModel().getProperty("/deal");
      if (oDeal && oDeal.id) {
        this.navToDetail("dealDetail", { dealId: oDeal.id });
      }
    },

    onArchive: function () {
      var that = this;
      MessageBox.confirm(this.getI18nText("confirmArchive"), {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            that.submitData(function () {
              return ordersService.archive(that._sOrderId);
            }, that.getI18nText("orderArchived")).then(function () {
              that.navToList("orders");
            });
          }
        }
      });
    },

    onClose: function () {
      this.navToList("orders");
    },

    onHedge: function () {
      var oDetail = this.getViewModel().getProperty("/detail") || {};
      this.getRouter().navTo("rfqCreate", {
        "?query": {
          orderId: this._sOrderId,
          orderType: oDetail.order_type || "",
          priceType: oDetail.price_type || ""
        }
      });
    }
  });
});
