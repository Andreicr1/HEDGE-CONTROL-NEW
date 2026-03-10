sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/rfqService",
  "hedgecontrol/service/counterpartiesService",
  "hedgecontrol/util/formatter",
  "sap/m/MessageBox",
  "sap/m/Dialog",
  "sap/m/Button",
  "sap/m/Label",
  "sap/m/Input",
  "sap/m/Select",
  "sap/ui/core/Item",
  "sap/m/VBox",
  "sap/m/MessageToast",
  "sap/m/Text",
  "sap/m/MessageStrip",
  "sap/ui/layout/form/SimpleForm",
  "sap/f/library"
], function (BaseController, rfqService, counterpartiesService, formatter, MessageBox, Dialog, Button, Label, Input, Select, Item, VBox, MessageToast, Text, MessageStrip, SimpleForm, fioriLibrary) {
  "use strict";

  var LayoutType = fioriLibrary.LayoutType;

  return BaseController.extend("hedgecontrol.controller.RfqDetail", {
    onInit: function () {
      this._counterpartyMap = {};
      this.initViewModel("rfqDet", {
        detail: {},
        quotes: [],
        ranking: {},
        stateEvents: [],
        midFullScreen: false
      });
      this._loadCounterparties();
      this.getRouter().getRoute("rfqDetail").attachPatternMatched(this._onRouteMatched, this);
      this.getRouter().getRoute("rfqDocument").attachPatternMatched(this._onRouteMatched, this);
    },

    onExit: function () {
      this._stopPolling();
      this.getRouter().getRoute("rfqDetail").detachPatternMatched(this._onRouteMatched, this);
      this.getRouter().getRoute("rfqDocument").detachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (oEvent) {
      var sRfqId = oEvent.getParameter("arguments").rfqId;
      this._sRfqId = sRfqId;
      this._loadRfq(sRfqId);
      this._loadQuotes(sRfqId);
      this._loadStateEvents(sRfqId);
      this._startPolling();
    },

    _loadRfq: function (sRfqId) {
      var that = this;
      this.loadData(function () {
        return rfqService.getById(sRfqId);
      }, "/detail").then(function (oDetail) {
        if (oDetail && (oDetail.state === "QUOTED" || oDetail.state === "SENT")) {
          that.onViewRanking();
        }
      });
    },

    /**
     * Start polling for new quotes / state changes every 10 seconds.
     */
    _startPolling: function () {
      this._stopPolling();
      var that = this;
      this._pollTimer = setInterval(function () {
        if (that._sRfqId) {
          that._loadQuotes(that._sRfqId);
          that._loadRfq(that._sRfqId);
          that._loadStateEvents(that._sRfqId);
        }
      }, 10000);
    },

    _stopPolling: function () {
      if (this._pollTimer) {
        clearInterval(this._pollTimer);
        this._pollTimer = null;
      }
    },

    /**
     * Load all counterparties and build an id→name map.
     */
    _loadCounterparties: function () {
      var that = this;
      counterpartiesService.list({ limit: 200 }).then(function (oResult) {
        var aItems = (oResult && oResult.items) || [];
        var oMap = {};
        aItems.forEach(function (oItem) {
          oMap[oItem.id] = oItem.short_name || oItem.name || oItem.id;
        });
        that._counterpartyMap = oMap;
        // Re-enrich data already loaded
        that._enrichQuotes();
        that._enrichRanking();
      }).catch(function () {
        that._counterpartyMap = {};
      });
    },

    /**
     * Resolve counterparty_id → name for an array of items.
     */
    _resolveCounterpartyNames: function (aItems) {
      var oMap = this._counterpartyMap || {};
      return (aItems || []).map(function (oItem) {
        var oEnriched = Object.assign({}, oItem);
        if (oItem.counterparty_id && oMap[oItem.counterparty_id]) {
          oEnriched._counterparty_name = oMap[oItem.counterparty_id];
        } else {
          oEnriched._counterparty_name = oItem.counterparty_id || "";
        }
        return oEnriched;
      });
    },

    /**
     * Re-enrich already loaded quotes with counterparty names.
     */
    _enrichQuotes: function () {
      var oModel = this.getViewModel();
      var aQuotes = oModel.getProperty("/quotes") || [];
      if (aQuotes.length > 0) {
        oModel.setProperty("/quotes", this._resolveCounterpartyNames(aQuotes));
      }
    },

    /**
     * Re-enrich already loaded ranking entries with counterparty names.
     */
    _enrichRanking: function () {
      var oModel = this.getViewModel();
      var oRanking = oModel.getProperty("/ranking") || {};
      if (oRanking.ranking && oRanking.ranking.length > 0) {
        oRanking.ranking = this._resolveCounterpartyNames(oRanking.ranking);
        oModel.setProperty("/ranking", Object.assign({}, oRanking));
      }
    },

    _loadQuotes: function (sRfqId) {
      var that = this;
      var oModel = this.getViewModel();
      rfqService.listQuotes(sRfqId).then(function (aQuotes) {
        oModel.setProperty("/quotes", that._resolveCounterpartyNames(aQuotes || []));
      }).catch(function () {
        oModel.setProperty("/quotes", []);
      });
    },

    _loadStateEvents: function (sRfqId) {
      var that = this;
      var oModel = this.getViewModel();
      rfqService.listStateEvents(sRfqId).then(function (aEvents) {
        var aEnriched = (aEvents || []).map(function (evt) {
          var o = Object.assign({}, evt);
          // Build human-readable description
          o._description = that._buildEventDescription(evt);
          // Icon based on transition
          o._icon = that._eventIcon(evt.to_state);
          return o;
        });
        oModel.setProperty("/stateEvents", aEnriched);
      }).catch(function () {
        oModel.setProperty("/stateEvents", []);
      });
    },

    _buildEventDescription: function (evt) {
      var sFrom = evt.from_state || "—";
      var sTo = evt.to_state || "—";
      var sDesc = sFrom + " → " + sTo;
      if (evt.trigger) { sDesc += " (" + evt.trigger + ")"; }
      if (evt.reason) { sDesc += " — " + evt.reason; }
      if (evt.triggering_counterparty_id) {
        var sName = (this._counterpartyMap || {})[evt.triggering_counterparty_id] || evt.triggering_counterparty_id;
        sDesc += " [" + sName + "]";
      }
      return sDesc;
    },

    _eventIcon: function (sState) {
      switch (sState) {
        case "CREATED": return "sap-icon://create";
        case "SENT": return "sap-icon://outbox";
        case "QUOTED": return "sap-icon://money-bills";
        case "AWARDED": return "sap-icon://accept";
        case "CLOSED": return "sap-icon://complete";
        default: return "sap-icon://process";
      }
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

    /**
     * Normalise trade-ranking entries so they look like spread-ranking
     * entries (counterparty_id + spread_value at the top level).
     */
    _normaliseTradeRanking: function (aEntries) {
      return (aEntries || []).map(function (oEntry) {
        if (oEntry.quote) {
          return Object.assign({}, oEntry, {
            counterparty_id: oEntry.quote.counterparty_id,
            spread_value: oEntry.quote.fixed_price_value
          });
        }
        return oEntry;
      });
    },

    onViewRanking: function () {
      var that = this;
      var oModel = this.getViewModel();
      var sIntent = oModel.getProperty("/detail/intent");
      var fnRanking = sIntent === "SPREAD"
        ? function () { return rfqService.getRanking(oModel.getProperty("/detail/id")); }
        : function () { return rfqService.getTradeRanking(oModel.getProperty("/detail/id")); };

      fnRanking().then(function (oRanking) {
        if (oRanking && oRanking.ranking) {
          if (sIntent !== "SPREAD") {
            oRanking.ranking = that._normaliseTradeRanking(oRanking.ranking);
          }
          oRanking.ranking = that._resolveCounterpartyNames(oRanking.ranking);
        }
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
              return rfqService.award(that._sRfqId, { user_id: "trader" });
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
              return rfqService.reject(that._sRfqId, { user_id: "trader" });
            }, that.getI18nText("rfqRejected")).then(function (oData) {
              if (oData) { that._loadRfq(that._sRfqId); }
            });
          }
        }
      });
    },

    /**
     * Refresh the RFQ — re-sends invitations to counterparties.
     */
    onRefresh: function () {
      var that = this;
      MessageBox.confirm(this.getI18nText("confirmRefresh"), {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            that.submitData(function () {
              return rfqService.refresh(that._sRfqId, { user_id: "trader" });
            }, that.getI18nText("rfqRefreshed")).then(function (oData) {
              if (oData) {
                that._loadRfq(that._sRfqId);
                that._loadQuotes(that._sRfqId);
              }
            });
          }
        }
      });
    },

    /**
     * Award the selected counterparty from the ranking table.
     * The backend auto-selects top-ranked; this confirms the action visually.
     */
    onAwardSelected: function () {
      var that = this;
      var oTable = this.byId("rankingTable");
      var oSelectedItem = oTable ? oTable.getSelectedItem() : null;
      var sName;

      if (oSelectedItem) {
        var oContext = oSelectedItem.getBindingContext("rfqDet");
        sName = oContext ? oContext.getProperty("_counterparty_name") : "";
      }

      if (!sName) {
        sName = this.getI18nText("rankingWinner");
      }

      var sMsg = this.getI18nText("confirmAwardCounterparty", [sName]);
      MessageBox.confirm(sMsg, {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            that.submitData(function () {
              return rfqService.award(that._sRfqId, { user_id: "trader" });
            }, that.getI18nText("rfqAwarded")).then(function (oData) {
              if (oData) { that._loadRfq(that._sRfqId); }
            });
          }
        }
      });
    },

    /* ─── Per-counterparty Quote Actions ─── */

    /**
     * Extract the quote data from the pressed button/menu-item's row context.
     * For MenuItems the binding context lives on the parent ColumnListItem,
     * so we walk up the control tree until we find it.
     */
    _getQuoteFromEvent: function (oEvent) {
      var oSource = oEvent.getSource();
      var oContext = oSource.getBindingContext("rfqDet");
      // Walk up the control tree for MenuItem inside MenuButton inside HBox → ColumnListItem
      var oControl = oSource;
      while (!oContext && oControl) {
        oControl = oControl.getParent();
        if (oControl) {
          oContext = oControl.getBindingContext("rfqDet");
        }
      }
      if (!oContext) { return null; }
      return oContext.getObject();
    },

    /**
     * Refresh (re-send invitation) for a specific counterparty.
     */
    onQuoteRefresh: function (oEvent) {
      var that = this;
      var oQuote = this._getQuoteFromEvent(oEvent);
      if (!oQuote) { return; }

      var sName = oQuote._counterparty_name || oQuote.counterparty_id;
      MessageBox.confirm(this.getI18nText("confirmRefreshCounterparty", [sName]), {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            rfqService.refreshCounterparty(that._sRfqId, {
              counterparty_id: oQuote.counterparty_id,
              user_id: "trader"
            }).then(function () {
              MessageToast.show(that.getI18nText("counterpartyRefreshed", [sName]));
              that._loadRfq(that._sRfqId);
            }).catch(function (oError) {
              MessageBox.error(that._formatError(oError));
            });
          }
        }
      });
    },

    /**
     * Reject a specific counterparty's quote.
     */
    onQuoteReject: function (oEvent) {
      var that = this;
      var oQuote = this._getQuoteFromEvent(oEvent);
      if (!oQuote) { return; }

      var sName = oQuote._counterparty_name || oQuote.counterparty_id;
      MessageBox.confirm(this.getI18nText("confirmRejectQuote", [sName]), {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            rfqService.rejectQuote(that._sRfqId, oQuote.id, {
              user_id: "trader"
            }).then(function () {
              MessageToast.show(that.getI18nText("quoteRejected", [sName]));
              that._loadRfq(that._sRfqId);
              that._loadQuotes(that._sRfqId);
            }).catch(function (oError) {
              MessageBox.error(that._formatError(oError));
            });
          }
        }
      });
    },

    /**
     * Contract (award) a specific counterparty's quote.
     * Shows a confirmation dialog with contract details before creating.
     */
    onQuoteContract: function (oEvent) {
      var that = this;
      var oQuote = this._getQuoteFromEvent(oEvent);
      if (!oQuote) { return; }

      var oDetail = this.getViewModel().getProperty("/detail");
      var sName = oQuote._counterparty_name || oQuote.counterparty_id;

      // Build confirmation dialog with contract details
      var oDialog = new Dialog({
        title: that.getI18nText("confirmContractTitle"),
        type: "Message",
        state: "Warning",
        content: new VBox({
          items: [
            new MessageStrip({
              text: that.getI18nText("confirmContractWarning"),
              type: "Warning",
              showIcon: true
            }).addStyleClass("sapUiSmallMarginBottom"),
            new SimpleForm({
              editable: false,
              layout: "ResponsiveGridLayout",
              labelSpanL: 5, labelSpanM: 5,
              content: [
                new Label({ text: that.getI18nText("colCounterpartyName"), design: "Bold" }),
                new Text({ text: sName }),
                new Label({ text: that.getI18nText("colCommodity"), design: "Bold" }),
                new Text({ text: oDetail.commodity }),
                new Label({ text: that.getI18nText("colDirection"), design: "Bold" }),
                new Text({ text: oDetail.direction }),
                new Label({ text: that.getI18nText("colQuantityMt"), design: "Bold" }),
                new Text({ text: formatter.numberTwoDecimals(oDetail.quantity_mt) + " MT" }),
                new Label({ text: that.getI18nText("colFixedPriceValue"), design: "Bold" }),
                new Text({ text: formatter.priceFourDecimals(oQuote.fixed_price_value) + " " + oQuote.fixed_price_unit }),
                new Label({ text: that.getI18nText("colFloatConvention"), design: "Bold" }),
                new Text({ text: oQuote.float_pricing_convention }),
                new Label({ text: that.getI18nText("colDeliveryWindow"), design: "Bold" }),
                new Text({
                  text: formatter.dateDisplay(oDetail.delivery_window_start) +
                    " \u2013 " + formatter.dateDisplay(oDetail.delivery_window_end)
                })
              ]
            })
          ]
        }).addStyleClass("sapUiSmallMargin"),
        beginButton: new Button({
          type: "Emphasized",
          text: that.getI18nText("confirmContractBtn"),
          icon: "sap-icon://accept",
          press: function () {
            oDialog.close();
            rfqService.awardQuote(that._sRfqId, {
              quote_id: oQuote.id,
              user_id: "trader"
            }).then(function () {
              MessageToast.show(that.getI18nText("contractCreated", [sName]));
              that._loadRfq(that._sRfqId);
              that._loadQuotes(that._sRfqId);
              that._loadStateEvents(that._sRfqId);
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
      this._stopPolling();
      this.navToList("rfq");
    },

    onNavigateToOrder: function () {
      var sOrderId = this.getViewModel().getProperty("/detail/order_id");
      if (sOrderId) {
        this.getRouter().navTo("orderDetail", { orderId: sOrderId });
      }
    }
  });
});
