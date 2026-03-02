sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/rfqService",
  "sap/m/MessageBox",
  "sap/m/Dialog",
  "sap/m/Button",
  "sap/m/Label",
  "sap/m/Input",
  "sap/m/Select",
  "sap/ui/core/Item",
  "sap/m/VBox",
  "sap/m/MessageToast",
  "sap/f/library"
], function (BaseController, rfqService, MessageBox, Dialog, Button, Label, Input, Select, Item, VBox, MessageToast, fioriLibrary) {
  "use strict";

  var LayoutType = fioriLibrary.LayoutType;

  return BaseController.extend("hedgecontrol.controller.RfqDetail", {
    onInit: function () {
      this.initViewModel("rfqDet", {
        detail: {},
        quotes: [],
        ranking: {},
        midFullScreen: false
      });
      this.getRouter().getRoute("rfqDetail").attachPatternMatched(this._onRouteMatched, this);
      this.getRouter().getRoute("rfqDocument").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (oEvent) {
      var sRfqId = oEvent.getParameter("arguments").rfqId;
      this._sRfqId = sRfqId;
      this._loadRfq(sRfqId);
      this._loadQuotes(sRfqId);
    },

    _loadRfq: function (sRfqId) {
      this.loadData(function () {
        return rfqService.getById(sRfqId);
      }, "/detail");
    },

    _loadQuotes: function (sRfqId) {
      var oModel = this.getViewModel();
      rfqService.listQuotes(sRfqId).then(function (aQuotes) {
        oModel.setProperty("/quotes", aQuotes || []);
      }).catch(function () {
        oModel.setProperty("/quotes", []);
      });
    },

    onAddQuote: function () {
      var that = this;
      var oCounterpartyInput = new Input({ placeholder: that.getI18nText("placeholderCounterpartyId") });
      var oFixedPriceInput = new Input({ type: "Number", placeholder: "0,0000" });
      var oFixedPriceUnitInput = new Input({ value: "USD/MT" });
      var oConventionSelect = new Select({
        items: [
          new Item({ key: "avg", text: "AVG" }),
          new Item({ key: "avginter", text: "AVGInter" }),
          new Item({ key: "c2r", text: "C2R" })
        ]
      });

      var oDialog = new Dialog({
        title: that.getI18nText("addQuote"),
        type: "Message",
        content: new VBox({
          items: [
            new Label({ text: that.getI18nText("colCounterpartyId") }),
            oCounterpartyInput,
            new Label({ text: that.getI18nText("colFixedPriceValue") }),
            oFixedPriceInput,
            new Label({ text: that.getI18nText("colFixedPriceUnit") }),
            oFixedPriceUnitInput,
            new Label({ text: that.getI18nText("colFloatConvention") }),
            oConventionSelect
          ]
        }).addStyleClass("sapUiSmallMargin"),
        beginButton: new Button({
          type: "Emphasized",
          text: that.getI18nText("submit"),
          press: function () {
            var oPayload = {
              rfq_id: that._sRfqId,
              counterparty_id: oCounterpartyInput.getValue(),
              fixed_price_value: parseFloat(oFixedPriceInput.getValue()),
              fixed_price_unit: oFixedPriceUnitInput.getValue(),
              float_pricing_convention: oConventionSelect.getSelectedKey(),
              received_at: new Date().toISOString()
            };
            rfqService.createQuote(that._sRfqId, oPayload).then(function () {
              MessageToast.show(that.getI18nText("quoteAdded"));
              that._loadQuotes(that._sRfqId);
              oDialog.close();
            }).catch(function (oError) {
              MessageBox.error(that._formatError(oError));
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

    onViewRanking: function () {
      var that = this;
      var oModel = this.getViewModel();
      var sIntent = oModel.getProperty("/detail/intent");
      var fnRanking = sIntent === "SPREAD"
        ? function () { return rfqService.getRanking(oModel.getProperty("/detail/id")); }
        : function () { return rfqService.getTradeRanking(oModel.getProperty("/detail/id")); };

      fnRanking().then(function (oRanking) {
        oModel.setProperty("/ranking", oRanking || {});
      }).catch(function () {
        oModel.setProperty("/ranking", {});
        MessageBox.error(that.getI18nText("msgRankingFailed"));
      });
    },

    onAward: function () {
      var that = this;
      MessageBox.confirm(this.getI18nText("confirmAward"), {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            that.submitData(function () {
              return rfqService.award(that._sRfqId, {});
            }, that.getI18nText("rfqAwarded")).then(function (oData) {
              if (oData) { that._loadRfq(that._sRfqId); }
            });
          }
        }
      });
    },

    onReject: function () {
      var that = this;
      MessageBox.confirm(this.getI18nText("confirmReject"), {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            that.submitData(function () {
              return rfqService.reject(that._sRfqId, {});
            }, that.getI18nText("rfqRejected")).then(function (oData) {
              if (oData) { that._loadRfq(that._sRfqId); }
            });
          }
        }
      });
    },

    onRefresh: function () {
      var that = this;
      MessageBox.confirm(this.getI18nText("confirmRefreshRfq"), {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            that.submitData(function () {
              return rfqService.refresh(that._sRfqId, {});
            }, that.getI18nText("rfqRefreshed")).then(function (oData) {
              if (oData) { that._loadRfq(that._sRfqId); }
            });
          }
        }
      });
    },

    onArchive: function () {
      var that = this;
      MessageBox.confirm(this.getI18nText("confirmArchiveRfq"), {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            that.submitData(function () {
              return rfqService.archive(that._sRfqId);
            }, that.getI18nText("rfqArchived")).then(function () {
              that.navToList("rfq");
            });
          }
        }
      });
    },

    /* ─── FCL Navigation ─── */

    onViewDocuments: function () {
      this.navToEndColumn("rfqDocument", { rfqId: this._sRfqId });
    },

    onToggleMidFullScreen: function () {
      var oModel = this.getViewModel();
      var bMidFull = oModel.getProperty("/midFullScreen");
      if (bMidFull) {
        this.setLayout(LayoutType.TwoColumnsMidExpanded);
        oModel.setProperty("/midFullScreen", false);
      } else {
        this.setLayout(LayoutType.MidColumnFullScreen);
        oModel.setProperty("/midFullScreen", true);
      }
    },

    onClose: function () {
      this.navToList("rfq");
    }
  });
});
