sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/ordersService",
  "sap/m/MessageBox"
], function (BaseController, ordersService, MessageBox) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.OrderDetail", {
    onInit: function () {
      this.initViewModel("ordDet", {
        detail: {}
      });
      this.getRouter().getRoute("orderDetail").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (oEvent) {
      var sOrderId = oEvent.getParameter("arguments").orderId;
      this._sOrderId = sOrderId;
      this._loadOrder(sOrderId);
    },

    _loadOrder: function (sOrderId) {
      this.loadData(function () {
        return ordersService.getById(sOrderId);
      }, "/detail");
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
    }
  });
});
