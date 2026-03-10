sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/cashflowProjectionService",
  "sap/m/MessageBox",
  "sap/viz/ui5/controls/feeds/FeedItem"
], function (BaseController, projectionService, MessageBox, FeedItem) {
  "use strict";

  var INSTRUMENT_LABELS = {
    sales_order: "instrSalesOrder",
    purchase_order: "instrPurchaseOrder",
    hedge_buy: "instrHedgeBuy",
    hedge_sell: "instrHedgeSell",
    hedge_contract: "instrHedgeContract"
  };

  var PRICE_SOURCE_LABELS = {
    fixed: "priceSourceFixed",
    market: "priceSourceMarket",
    entry: "priceSourceEntry"
  };

  var MONTH_NAMES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
  ];

  var MONTHS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

  return BaseController.extend("hedgecontrol.controller.Cashflow", {

    onAfterRendering: function () {
      if (!this._cfFeedsInit) {
        this._cfFeedsInit = true;
        var oChart = this.byId("cashflowChart");
        oChart.addFeed(new FeedItem({ uid: "valueAxis", values: ["Inflows", "Outflows", "Net"] }));
        oChart.addFeed(new FeedItem({ uid: "categoryAxis", values: ["Per\u00edodo"] }));
      }
    },

    onInit: function () {
      this.initViewModel("cf", {
        projection: { items: [], summary: { total_inflows: 0, total_outflows: 0, net_cashflow: 0, instrument_count: 0 } },
        projectionTree: [],
        projectionBusy: false,
        projectionLoaded: false,
        chartData: []
      });
      this.getRouter().getRoute("cashflow").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      // Reset state on navigation
    },

    onLoadProjection: function () {
      var sDate = this.byId("projectionDate").getValue();
      if (!sDate) {
        MessageBox.warning(this.getI18nText("dateRequired"));
        return;
      }
      var oModel = this.getViewModel();
      oModel.setProperty("/projectionBusy", true);
      oModel.setProperty("/projectionLoaded", false);
      var that = this;
      projectionService.get(sDate).then(function (oData) {
        oModel.setProperty("/projection", oData);
        var aTree = that._buildProjectionTree(oData.items || [], sDate);
        oModel.setProperty("/projectionTree", aTree);
        oModel.setProperty("/chartData", that._buildChartData(oData.items || []));
        oModel.setProperty("/projectionLoaded", true);
      }).catch(function (oError) {
        MessageBox.error(this._formatError(oError));
      }.bind(this)).finally(function () {
        oModel.setProperty("/projectionBusy", false);
      });
    },

    /* ─── Projection TreeTable: expand / collapse ─── */

    onProjectionExpandAll: function () {
      this.byId("projectionTreeTable").expandToLevel(3);
    },

    onProjectionCollapseAll: function () {
      this.byId("projectionTreeTable").collapseAll();
    },

    /* ─── VizFrame chart dataset: Inflows / Outflows / Net per month ─── */

    _buildChartData: function (aItems) {
      var mMonths = {};
      aItems.forEach(function (oItem) {
        var d = new Date(oItem.settlement_date);
        var sKey = d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0");
        if (!mMonths[sKey]) { mMonths[sKey] = { inflows: 0, outflows: 0 }; }
        var fAmt = parseFloat(oItem.amount_usd) || 0;
        if (fAmt >= 0) {
          mMonths[sKey].inflows += fAmt;
        } else {
          mMonths[sKey].outflows += fAmt;
        }
      });
      return Object.keys(mMonths).sort().map(function (sKey) {
        var oParts = sKey.split("-");
        var sLabel = MONTHS[parseInt(oParts[1], 10) - 1] + " " + oParts[0];
        var fIn = mMonths[sKey].inflows;
        var fOut = mMonths[sKey].outflows;
        return { label: sLabel, inflows: fIn, outflows: fOut, net: fIn + fOut };
      });
    },

    /* ─────────────────────────────────────────────────
       Build projection tree: Quarter → Month → Items
       Each item carries its settlement day for drill-down
       ───────────────────────────────────────────────── */

    _buildProjectionTree: function (aItems, sAsOfDate) {
      var that = this;

      var oBase = new Date(sAsOfDate);
      var aQuarters = this._getNextQuarters(oBase, 4);

      // Bucket items into quarters
      var mBuckets = {};
      aQuarters.forEach(function (oQ) { mBuckets[oQ.key] = []; });
      mBuckets["beyond"] = [];

      aItems.forEach(function (oItem) {
        var dSettle = new Date(oItem.settlement_date);
        var bPlaced = false;
        for (var i = 0; i < aQuarters.length; i++) {
          if (dSettle >= aQuarters[i].start && dSettle <= aQuarters[i].end) {
            mBuckets[aQuarters[i].key].push(oItem);
            bPlaced = true;
            break;
          }
        }
        if (!bPlaced) {
          mBuckets["beyond"].push(oItem);
        }
      });

      var aTree = [];

      aQuarters.forEach(function (oQ) {
        var aQItems = mBuckets[oQ.key];
        aTree.push(that._buildQuarterNode(oQ, aQItems));
      });

      var aBeyond = mBuckets["beyond"];
      if (aBeyond.length > 0) {
        aTree.push(that._buildQuarterNode(
          { label: that.getI18nText("projectionBeyondLabel"), start: null, end: null },
          aBeyond
        ));
      }

      return aTree;
    },

    /**
     * Quarter → Month children.
     * Each month groups items that fall within it; months sorted ascending.
     */
    _buildQuarterNode: function (oQ, aItems) {
      var that = this;

      // Group items by YYYY-MM
      var mMonths = {};
      aItems.forEach(function (oItem) {
        var d = new Date(oItem.settlement_date);
        var sKey = d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0");
        if (!mMonths[sKey]) { mMonths[sKey] = []; }
        mMonths[sKey].push(oItem);
      });

      // Sort month keys ascending
      var aSortedKeys = Object.keys(mMonths).sort();

      var aMonthChildren = aSortedKeys.map(function (sMonthKey) {
        return that._buildMonthNode(sMonthKey, mMonths[sMonthKey]);
      });

      var fQIn = aMonthChildren.reduce(function (s, c) { return s + (c.inflows || 0); }, 0);
      var fQOut = aMonthChildren.reduce(function (s, c) { return s + (c.outflows || 0); }, 0);

      return that._makeNode(
        oQ.label + " (" + aItems.length + " itens)",
        "", "", "", null, null, fQIn, fQOut, fQIn + fQOut, "", "",
        aMonthChildren
      );
    },

    /**
     * Month → individual cashflow items (leaves).
     */
    _buildMonthNode: function (sMonthKey, aItems) {
      var that = this;
      var aParts = sMonthKey.split("-");
      var iYear = parseInt(aParts[0], 10);
      var iMonth = parseInt(aParts[1], 10) - 1; // 0-based
      var sMonthLabel = MONTH_NAMES[iMonth] + " " + iYear;

      // Sort items by settlement_date ascending
      aItems.sort(function (a, b) {
        return new Date(a.settlement_date) - new Date(b.settlement_date);
      });

      var aLeaves = aItems.map(function (oItem) {
        var fAmount = parseFloat(oItem.amount_usd) || 0;
        return that._makeNode(
          that.formatInstrumentType(oItem.instrument_type) +
            " #" + (oItem.instrument_id || "").substring(0, 8),
          that.formatInstrumentType(oItem.instrument_type),
          oItem.commodity || "",
          that._formatDateShort(oItem.settlement_date),
          parseFloat(oItem.quantity_mt) || null,
          parseFloat(oItem.price_per_mt) || null,
          fAmount > 0 ? fAmount : null,
          fAmount < 0 ? fAmount : null,
          fAmount,
          that.formatPriceSource(oItem.price_source),
          oItem.deal_id ? oItem.deal_id.substring(0, 8) : "",
          []
        );
      });

      var fIn = aLeaves.reduce(function (s, c) { return s + (c.inflows || 0); }, 0);
      var fOut = aLeaves.reduce(function (s, c) { return s + (c.outflows || 0); }, 0);

      return that._makeNode(
        sMonthLabel + " (" + aLeaves.length + ")",
        "", "", "", null, null, fIn || null, fOut || null, fIn + fOut, "", "",
        aLeaves
      );
    },

    /** Helper: create tree node object */
    _makeNode: function (desc, instrType, commodity, settleDate, qty, price, inflows, outflows, net, source, dealId, children) {
      return {
        description: desc,
        instrumentType: instrType,
        commodity: commodity,
        settlementDate: settleDate,
        quantity: qty,
        price: price,
        inflows: inflows,
        outflows: outflows,
        net: net,
        priceSource: source,
        dealId: dealId,
        children: children
      };
    },

    _getNextQuarters: function (oDate, nCount) {
      var aQuarters = [];
      var iYear = oDate.getFullYear();
      var iMonth = oDate.getMonth();
      var iCurrentQ = Math.floor(iMonth / 3);

      for (var i = 0; i < nCount; i++) {
        var iQ = (iCurrentQ + i) % 4;
        var iY = iYear + Math.floor((iCurrentQ + i) / 4);
        var iStartMonth = iQ * 3;
        var iEndMonth = iStartMonth + 2;
        var sLabel = this.getI18nText("projectionQuarter", [iQ + 1, iY]);

        aQuarters.push({
          key: "Q" + (iQ + 1) + "_" + iY,
          label: sLabel,
          start: new Date(iY, iStartMonth, 1),
          end: new Date(iY, iEndMonth + 1, 0, 23, 59, 59, 999)
        });
      }
      return aQuarters;
    },

    _formatDateShort: function (sDate) {
      if (!sDate) { return ""; }
      var d = new Date(sDate);
      if (isNaN(d.getTime())) { return sDate; }
      var sDay = String(d.getDate()).padStart(2, "0");
      var sMonth = String(d.getMonth() + 1).padStart(2, "0");
      return sDay + "/" + sMonth + "/" + d.getFullYear();
    },

    formatInstrumentType: function (sType) {
      var sKey = INSTRUMENT_LABELS[sType];
      return sKey ? this.getI18nText(sKey) : sType;
    },

    formatPriceSource: function (sSource) {
      var sKey = PRICE_SOURCE_LABELS[sSource];
      return sKey ? this.getI18nText(sKey) : sSource;
    },

    formatAmountState: function (fAmount) {
      if (fAmount > 0) { return "Success"; }
      if (fAmount < 0) { return "Error"; }
      return "None";
    },

    hasValue: function (sVal) {
      return !!sVal;
    }
  });
});
