sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/ordersService",
  "sap/m/MessageBox",
  "sap/m/Dialog",
  "sap/m/Button",
  "sap/m/Label",
  "sap/m/Input",
  "sap/m/VBox"
], function (BaseController, ordersService, MessageBox, Dialog, Button, Label, Input, VBox) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.OrderDetail", {
    onInit: function () {
      this.initViewModel("ordDet", {
        detail: {},
        links: []
      });
      this.getRouter().getRoute("orderDetail").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (oEvent) {
      var sOrderId = oEvent.getParameter("arguments").orderId;
      this._sOrderId = sOrderId;
      this._loadOrder(sOrderId);
      this._loadLinks();
    },

    _loadOrder: function (sOrderId) {
      this.loadData(function () {
        return ordersService.getById(sOrderId);
      }, "/detail");
    },

    _loadLinks: function () {
      var that = this;
      ordersService.listLinks().then(function (oData) {
        if (oData && oData.items) {
          var sId = that._sOrderId;
          var aFiltered = oData.items.filter(function (oLink) {
            return oLink.sales_order_id === sId || oLink.purchase_order_id === sId;
          });
          that.getViewModel().setProperty("/links", aFiltered);
        }
      }).catch(function () {
        that.getViewModel().setProperty("/links", []);
      });
    },

    onAddLink: function () {
      var that = this;
      var oDetail = this.getViewModel().getProperty("/detail");
      var bIsSales = oDetail.order_type === "SO";

      var oIdInput = new Input({ placeholder: "UUID", width: "100%" });
      var oTonsInput = new Input({ placeholder: "0.00", type: "Number", width: "100%" });

      var sLabel = bIsSales
        ? that.getI18nText("linkPurchaseOrderId")
        : that.getI18nText("linkSalesOrderId");

      var oDialog = new Dialog({
        title: that.getI18nText("addSoPoLink"),
        type: "Message",
        content: new VBox({
          items: [
            new Label({ text: sLabel }),
            oIdInput,
            new Label({ text: that.getI18nText("linkedTons"), design: "Bold" }).addStyleClass("sapUiSmallMarginTop"),
            oTonsInput
          ]
        }).addStyleClass("sapUiSmallMargin"),
        beginButton: new Button({
          text: that.getI18nText("submit"),
          type: "Emphasized",
          press: function () {
            var sLinkedId = oIdInput.getValue().trim();
            var fTons = parseFloat(oTonsInput.getValue());
            if (!sLinkedId || isNaN(fTons) || fTons <= 0) { return; }

            var oPayload = {
              linked_tons: fTons
            };
            if (bIsSales) {
              oPayload.sales_order_id = that._sOrderId;
              oPayload.purchase_order_id = sLinkedId;
            } else {
              oPayload.purchase_order_id = that._sOrderId;
              oPayload.sales_order_id = sLinkedId;
            }

            that.submitData(function () {
              return ordersService.createLink(oPayload);
            }, that.getI18nText("soPoLinkCreated")).then(function (oData) {
              if (oData) {
                that._loadLinks();
              }
            });
            oDialog.close();
          }
        }),
        endButton: new Button({
          text: that.getI18nText("cancel"),
          press: function () { oDialog.close(); }
        }),
        afterClose: function () { oDialog.destroy(); }
      });
      oDialog.open();
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
