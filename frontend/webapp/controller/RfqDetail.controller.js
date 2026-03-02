sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/rfqService",
  "hedgecontrol/service/apiClient",
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
], function (BaseController, rfqService, apiClient, MessageBox, Dialog, Button, Label, Input, Select, Item, VBox, MessageToast, fioriLibrary) {
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
      var bSpread = sIntent === "SPREAD";
      var sId = oModel.getProperty("/detail/id");
      var fnRanking = bSpread
        ? function () { return rfqService.getRanking(sId); }
        : function () { return rfqService.getTradeRanking(sId); };

      fnRanking().then(function (oRanking) {
        oModel.setProperty("/ranking", oRanking || {});

        var aRows = [];
        if (oRanking && oRanking.ranking) {
          oRanking.ranking.forEach(function (item) {
            if (bSpread) {
              aRows.push({
                rank: item.rank,
                counterparty_id: item.counterparty_id,
                price: item.spread_value,
                unit: "spread",
                convention: ""
              });
            } else {
              var q = item.quote || {};
              aRows.push({
                rank: item.rank,
                counterparty_id: q.counterparty_id,
                price: q.fixed_price_value,
                unit: q.fixed_price_unit || "USD/MT",
                convention: q.float_pricing_convention || ""
              });
            }
          });
        }
        oModel.setProperty("/rankingRows", aRows);
        oModel.setProperty("/rankingIntent", bSpread ? "SPREAD" : "TRADE");
      }).catch(function () {
        oModel.setProperty("/ranking", {});
        oModel.setProperty("/rankingRows", []);
        MessageBox.error(that.getI18nText("msgRankingFailed"));
      });
    },

    _userPayload: function () {
      return { user_id: apiClient.getCurrentUserId() };
    },

    onAward: function () {
      var that = this;
      var oRanking = this.getViewModel().getProperty("/ranking");
      if (!oRanking || !oRanking.ranking || oRanking.ranking.length === 0) {
        MessageBox.warning(this.getI18nText("msgLoadRankingFirst"));
        return;
      }

      var oTop = oRanking.ranking[0];
      var sMsg = this.getI18nText("confirmAwardWithDetails", [
        oTop.counterparty_id || oTop.counterparty_name || "—",
        oTop.spread_value || oTop.quote && oTop.quote.fixed_price_value || "—"
      ]);

      MessageBox.confirm(sMsg, {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            that.submitData(function () {
              return rfqService.award(that._sRfqId, that._userPayload());
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
              return rfqService.reject(that._sRfqId, that._userPayload());
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
              return rfqService.refresh(that._sRfqId, that._userPayload());
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
