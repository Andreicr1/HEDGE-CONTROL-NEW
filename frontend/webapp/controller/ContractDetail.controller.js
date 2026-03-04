sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/contractsService",
  "hedgecontrol/service/counterpartiesService",
  "hedgecontrol/service/mtmService",
  "hedgecontrol/service/cashflowLedgerService",
  "sap/m/MessageBox",
  "sap/m/Dialog",
  "sap/m/Button",
  "sap/m/Label",
  "sap/m/Input",
  "sap/m/VBox",
  "sap/m/MessageToast"
], function (BaseController, contractsService, counterpartiesService, mtmService, cashflowLedgerService, MessageBox, Dialog, Button, Label, Input, VBox, MessageToast) {
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

    /* ── load contract + enrich with counterparty name & MTM ── */
    _loadContract: function () {
      var oModel = this.getViewModel();
      oModel.setProperty("/busy", true);

      contractsService.getHedgeById(this._sContractId).then(function (oData) {
        oModel.setData(oData);
        // fire enrichment in parallel
        this._resolveCounterparty(oData.counterparty_id);
        this._loadMtm();
        this._loadLinkages();
      }.bind(this)).catch(function (oError) {
        oModel.setProperty("/errorMessage", this._formatError(oError));
      }.bind(this)).finally(function () {
        oModel.setProperty("/busy", false);
      });
    },

    _resolveCounterparty: function (sId) {
      if (!sId) { return; }
      var oModel = this.getViewModel();
      counterpartiesService.getById(sId).then(function (o) {
        oModel.setProperty("/_counterparty_name", o.short_name || o.name || sId);
      }).catch(function () {
        oModel.setProperty("/_counterparty_name", sId);
      });
    },

    _loadMtm: function () {
      var oModel = this.getViewModel();
      var oYesterday = new Date();
      oYesterday.setDate(oYesterday.getDate() - 1);
      var sDate = oYesterday.toISOString().slice(0, 10);

      mtmService.getForHedgeContract(this._sContractId, sDate).then(function (oMtm) {
        oModel.setProperty("/_mtm_value", oMtm.mtm_value != null ? oMtm.mtm_value : null);
        oModel.setProperty("/_mtm_unit", oMtm.currency || "USD");
      }).catch(function () {
        oModel.setProperty("/_mtm_value", null);
        oModel.setProperty("/_mtm_unit", "");
      });
    },

    _loadLinkages: function () {
      var oModel = this.getViewModel();
      contractsService.getLinkages(this._sContractId).then(function (oRes) {
        var aDeals = oRes.deals || [];
        oModel.setProperty("/_linkages", aDeals);

        // Flatten orders from all deals
        var aAllOrders = [];
        aDeals.forEach(function (deal) {
          if (deal.orders && deal.orders.length) {
            deal.orders.forEach(function (order) {
              aAllOrders.push(Object.assign({ _dealRef: deal.reference || "" }, order));
            });
          }
        });
        oModel.setProperty("/_allOrders", aAllOrders);
      }).catch(function () {
        oModel.setProperty("/_linkages", []);
        oModel.setProperty("/_allOrders", []);
      });
    },

    /* ── actions ── */
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

    onNavigateToDeal: function (oEvent) {
      var oCtx = oEvent.getSource().getBindingContext("ctrDet");
      if (!oCtx) { return; }
      var sDealId = oCtx.getProperty("id");
      if (sDealId) {
        this.getRouter().navTo("dealDetail", { dealId: sDealId });
      }
    },

    onNavigateToLinkedOrder: function (oEvent) {
      var oCtx = oEvent.getSource().getBindingContext("ctrDet");
      if (!oCtx) { return; }
      var sType = oCtx.getProperty("linked_type");
      var sId = oCtx.getProperty("linked_id");
      if (!sId) { return; }
      if (sType === "sales_order" || sType === "purchase_order") {
        this.getRouter().navTo("orderDetail", { orderId: sId });
      }
    },

    isNotArchived: function (sDeletedAt) {
      return !sDeletedAt;
    },

    formatMtmState: function (fValue) {
      if (fValue == null) { return "None"; }
      if (fValue > 0) { return "Success"; }
      if (fValue < 0) { return "Error"; }
      return "None";
    }
  });
});
