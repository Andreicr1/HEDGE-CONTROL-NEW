sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/contractsService",
  "hedgecontrol/service/cashflowLedgerService",
  "sap/m/MessageBox",
  "sap/m/Dialog",
  "sap/m/Button",
  "sap/m/Label",
  "sap/m/Input",
  "sap/m/VBox",
  "sap/m/MessageToast"
], function (BaseController, contractsService, cashflowLedgerService, MessageBox, Dialog, Button, Label, Input, VBox, MessageToast) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.ContractDetail", {

    onInit: function () {
      this.initViewModel("ctrDet", {});
      this.getRouter().getRoute("contractDetail").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (oEvent) {
      this._sContractId = oEvent.getParameter("arguments").contractId;
      this._loadContract();
    },

    _loadContract: function () {
      this.loadData(function () {
        return contractsService.getHedgeById(this._sContractId);
      }.bind(this), "/");
    },

    onArchive: function () {
      var that = this;
      MessageBox.confirm(this.getI18nText("confirmArchiveContract"), {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            that.submitData(function () {
              return contractsService.archive(that._sContractId);
            }, that.getI18nText("contractArchived")).then(function () {
              that.navToList("contracts");
            });
          }
        }
      });
    },

    onSettle: function () {
      var that = this;
      var oAmountInput = new Input({ type: "Number", placeholder: "0.00" });
      var oCurrencyInput = new Input({ value: "USD", maxLength: 3 });

      var oDialog = new Dialog({
        title: that.getI18nText("settle"),
        type: "Message",
        content: new VBox({
          items: [
            new Label({ text: that.getI18nText("settlementAmount") }),
            oAmountInput,
            new Label({ text: that.getI18nText("settlementCurrency") }),
            oCurrencyInput
          ]
        }).addStyleClass("sapUiSmallMargin"),
        beginButton: new Button({
          type: "Emphasized",
          text: that.getI18nText("settle"),
          press: function () {
            var fAmount = parseFloat(oAmountInput.getValue());
            if (!fAmount || fAmount <= 0) {
              MessageBox.warning(that.getI18nText("settlementAmount"));
              return;
            }
            that.submitData(function () {
              return cashflowLedgerService.settleContract(that._sContractId, {
                settlement_amount: fAmount,
                currency: oCurrencyInput.getValue().toUpperCase()
              });
            }, that.getI18nText("settlementSuccess")).then(function (oData) {
              if (oData) { that._loadContract(); }
              oDialog.close();
            });
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

    onClose: function () {
      this.navToList("contracts");
    },

    isNotArchived: function (sDeletedAt) {
      return !sDeletedAt;
    },

    isSettleable: function (sStatus, sDeletedAt) {
      return sStatus === "active" && !sDeletedAt;
    },

    formatClassificationState: function (sClassification) {
      if (!sClassification) { return "None"; }
      return sClassification === "long" ? "Success" : "Error";
    }
  });
});
