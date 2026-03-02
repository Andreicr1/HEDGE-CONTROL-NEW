sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/dealsService",
  "sap/m/MessageBox",
  "sap/m/Dialog",
  "sap/m/Button",
  "sap/m/Label",
  "sap/m/Input",
  "sap/m/Select",
  "sap/m/VBox",
  "sap/ui/core/Item"
], function (BaseController, dealsService, MessageBox, Dialog, Button, Label, Input, Select, VBox, Item) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.DealDetail", {
    onInit: function () {
      this.initViewModel("dealDet", {
        detail: {},
        links: [],
        pnlHistory: []
      });
      this.getRouter().getRoute("dealDetail").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (oEvent) {
      this._sDealId = oEvent.getParameter("arguments").dealId;
      this._loadDetail();
      this._loadPnlHistory();
    },

    _loadDetail: function () {
      var that = this;
      this.loadData(function () {
        return dealsService.getById(that._sDealId);
      }, "/detail").then(function (oData) {
        if (oData) {
          that.getViewModel().setProperty("/links", oData.links || []);
        }
      });
    },

    _loadPnlHistory: function () {
      var that = this;
      dealsService.getPnlHistory(this._sDealId).then(function (oData) {
        if (oData && oData.items) {
          that.getViewModel().setProperty("/pnlHistory", oData.items);
        }
      }).catch(function () {
        that.getViewModel().setProperty("/pnlHistory", []);
      });
    },

    onRefresh: function () {
      this._loadDetail();
      this._loadPnlHistory();
    },

    onAddLink: function () {
      var that = this;
      var oTypeSelect = new Select({ width: "100%" });
      oTypeSelect.addItem(new Item({ key: "sales_order", text: that.getI18nText("linkTypeSalesOrder") }));
      oTypeSelect.addItem(new Item({ key: "purchase_order", text: that.getI18nText("linkTypePurchaseOrder") }));
      oTypeSelect.addItem(new Item({ key: "hedge", text: that.getI18nText("linkTypeHedge") }));
      oTypeSelect.addItem(new Item({ key: "contract", text: that.getI18nText("linkTypeContract") }));

      var oIdInput = new Input({ placeholder: "UUID", width: "100%" });

      var oDialog = new Dialog({
        title: that.getI18nText("addLink"),
        type: "Message",
        content: new VBox({
          items: [
            new Label({ text: that.getI18nText("linkType") }),
            oTypeSelect,
            new Label({ text: "ID", design: "Bold" }).addStyleClass("sapUiSmallMarginTop"),
            oIdInput
          ]
        }).addStyleClass("sapUiSmallMargin"),
        beginButton: new Button({
          text: that.getI18nText("submit"),
          type: "Emphasized",
          press: function () {
            var sType = oTypeSelect.getSelectedKey();
            var sLinkedId = oIdInput.getValue().trim();
            if (!sLinkedId) { return; }
            that.submitData(function () {
              return dealsService.addLink(that._sDealId, {
                linked_type: sType,
                linked_id: sLinkedId
              });
            }, that.getI18nText("linkAdded")).then(function (oData) {
              if (oData) {
                that._loadDetail();
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

    onRemoveLink: function (oEvent) {
      var oCtx = oEvent.getSource().getBindingContext("dealDet");
      var sLinkId = oCtx.getProperty("id");
      var that = this;
      MessageBox.confirm(this.getI18nText("confirmRemoveLink"), {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            that.submitData(function () {
              return dealsService.removeLink(that._sDealId, sLinkId);
            }, that.getI18nText("linkRemoved")).then(function () {
              that._loadDetail();
            });
          }
        }
      });
    },

    onTriggerPnlSnapshot: function () {
      var that = this;
      this.submitData(function () {
        return dealsService.triggerPnlSnapshot(that._sDealId);
      }, this.getI18nText("pnlSnapshotCreated")).then(function (oData) {
        if (oData) {
          that._loadPnlHistory();
        }
      });
    },

    onClose: function () {
      this.navToList("deals");
    }
  });
});
