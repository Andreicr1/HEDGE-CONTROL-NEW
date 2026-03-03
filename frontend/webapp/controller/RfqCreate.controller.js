sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/rfqService",
  "hedgecontrol/service/apiClient",
  "sap/m/MessageBox",
  "sap/m/MessageToast"
], function (BaseController, rfqService, apiClient, MessageBox, MessageToast) {
  "use strict";

  var SIDE_BUY = 0;
  var SIDE_SELL = 1;

  var COMPANY_MAP = [
    { header: "Alcast Brasil", label: "Alcast Brasil" },
    { header: "Alcast Trading", label: "Alcast Trading" }
  ];

  var CHANNEL_LABELS = {
    broker_lme: "Broker LME",
    banco_br: "Banco BR",
    none: "—"
  };

  function _emptyLeg(side) {
    return {
      sideIndex: side === "sell" ? SIDE_SELL : SIDE_BUY,
      side: side || "buy",
      priceType: "",
      monthName: "",
      year: "",
      startDate: "",
      endDate: "",
      fixingDate: "",
      settlementDate: "",
      orderType: "",
      orderValidity: "Day",
      limitPrice: ""
    };
  }

  function _emptyTrade(index) {
    return {
      title: "Trade " + (index + 1),
      index: index,
      leg1: _emptyLeg("buy"),
      leg2: _emptyLeg("sell")
    };
  }

  function _buildYearItems() {
    var iNow = new Date().getFullYear();
    var a = [];
    for (var i = iNow; i <= iNow + 3; i++) {
      a.push({ key: String(i), text: String(i) });
    }
    return a;
  }

  function _emptyForm() {
    return {
      companyIndex: 0,
      tradeType: "Swap",
      quantity: "",
      trades: [_emptyTrade(0)],
      showResult: false,
      textEn: "",
      textPt: "",
      pptInfo: "",
      counterparties: [],
      selectedCount: 0,
      yearItems: _buildYearItems()
    };
  }

  return BaseController.extend("hedgecontrol.controller.RfqCreate", {

    onInit: function () {
      this.initViewModel("rfqCrt", _emptyForm());
      this.getRouter().getRoute("rfqCreate").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this.setLayout("OneColumn");
      var oData = _emptyForm();
      oData.errorMessage = "";
      oData.busy = false;
      var oModel = this.getViewModel();
      for (var k in oData) {
        oModel.setProperty("/" + k, oData[k]);
      }
      this._loadCounterparties();
    },

    _loadCounterparties: function () {
      var oModel = this.getViewModel();
      apiClient.getJson("/counterparties?is_active=true&limit=200").then(function (oData) {
        var aItems = (oData && oData.items) || [];
        var aRfqEligible = aItems.filter(function (cp) {
          return cp.rfq_channel_type && cp.rfq_channel_type !== "none";
        }).map(function (cp) {
          return {
            id: cp.id,
            name: cp.short_name || cp.name,
            rfq_channel_type: cp.rfq_channel_type,
            country: cp.country,
            contact_phone: cp.contact_phone || "",
            contact_email: cp.contact_email || "",
            selected: true
          };
        });
        oModel.setProperty("/counterparties", aRfqEligible);
        oModel.setProperty("/selectedCount", aRfqEligible.length);
      }).catch(function () {
        oModel.setProperty("/counterparties", []);
      });
    },

    /* ─── Trade management ─── */

    onAddTrade: function () {
      var oModel = this.getViewModel();
      var aTrades = oModel.getProperty("/trades");
      aTrades.push(_emptyTrade(aTrades.length));
      oModel.setProperty("/trades", aTrades);
    },

    onRemoveTrade: function (oEvent) {
      var oCtx = oEvent.getSource().getBindingContext("rfqCrt");
      if (!oCtx) { return; }
      var oModel = this.getViewModel();
      var aTrades = oModel.getProperty("/trades");
      var iIdx = parseInt(oCtx.getPath().split("/").pop(), 10);
      if (iIdx === 0 || isNaN(iIdx)) { return; }
      aTrades.splice(iIdx, 1);
      for (var i = 0; i < aTrades.length; i++) {
        aTrades[i].title = "Trade " + (i + 1);
        aTrades[i].index = i;
      }
      oModel.setProperty("/trades", aTrades);
      oModel.setProperty("/showResult", false);
    },

    /* ─── Templates (proteção de queda / alta / spread) ─── */

    _getTradePathFromEvent: function (oEvent) {
      var oSrc = oEvent.getSource();
      var oCtx = oSrc.getBindingContext("rfqCrt");
      if (oCtx) { return oCtx.getPath(); }
      var oParent = oSrc.getParent();
      while (oParent) {
        oCtx = oParent.getBindingContext("rfqCrt");
        if (oCtx) { return oCtx.getPath(); }
        oParent = oParent.getParent();
      }
      return null;
    },

    onTemplateQueda: function (oEvent) {
      var sPath = this._getTradePathFromEvent(oEvent);
      if (!sPath) { return; }
      this._applyTemplate(sPath, {
        leg1: { sideIndex: SIDE_BUY, side: "buy", priceType: "AVG" },
        leg2: { sideIndex: SIDE_SELL, side: "sell", priceType: "Fix" }
      });
    },

    onTemplateAlta: function (oEvent) {
      var sPath = this._getTradePathFromEvent(oEvent);
      if (!sPath) { return; }
      this._applyTemplate(sPath, {
        leg1: { sideIndex: SIDE_SELL, side: "sell", priceType: "AVG" },
        leg2: { sideIndex: SIDE_BUY, side: "buy", priceType: "Fix" }
      });
    },

    onTemplateSpread: function (oEvent) {
      var sPath = this._getTradePathFromEvent(oEvent);
      if (!sPath) { return; }
      this._applyTemplate(sPath, {
        leg1: { sideIndex: SIDE_BUY, side: "buy", priceType: "AVG" },
        leg2: { sideIndex: SIDE_SELL, side: "sell", priceType: "AVG" }
      });
    },

    _applyTemplate: function (sTradePath, tpl) {
      var oModel = this.getViewModel();
      oModel.setProperty("/tradeType", "Swap");
      oModel.setProperty("/showResult", false);

      var oLeg1 = _emptyLeg("buy");
      Object.assign(oLeg1, tpl.leg1);
      oModel.setProperty(sTradePath + "/leg1", oLeg1);

      var oLeg2 = _emptyLeg("sell");
      Object.assign(oLeg2, tpl.leg2);
      oModel.setProperty(sTradePath + "/leg2", oLeg2);
    },

    /* ─── Field change handlers ─── */

    onTradeTypeChange: function () {
      this.getViewModel().setProperty("/showResult", false);
    },

    onSide1Change: function (oEvent) {
      var oCtx = oEvent.getSource().getBindingContext("rfqCrt");
      if (!oCtx) { return; }
      var sPath = oCtx.getPath();
      var oModel = this.getViewModel();
      var iIdx = oModel.getProperty(sPath + "/leg1/sideIndex");
      oModel.setProperty(sPath + "/leg1/side", iIdx === SIDE_BUY ? "buy" : "sell");
      oModel.setProperty(sPath + "/leg2/sideIndex", iIdx === SIDE_BUY ? SIDE_SELL : SIDE_BUY);
      oModel.setProperty(sPath + "/leg2/side", iIdx === SIDE_BUY ? "sell" : "buy");
    },

    onSide2Change: function (oEvent) {
      var oCtx = oEvent.getSource().getBindingContext("rfqCrt");
      if (!oCtx) { return; }
      var sPath = oCtx.getPath();
      var oModel = this.getViewModel();
      var iIdx = oModel.getProperty(sPath + "/leg2/sideIndex");
      oModel.setProperty(sPath + "/leg2/side", iIdx === SIDE_BUY ? "buy" : "sell");
      oModel.setProperty(sPath + "/leg1/sideIndex", iIdx === SIDE_BUY ? SIDE_SELL : SIDE_BUY);
      oModel.setProperty(sPath + "/leg1/side", iIdx === SIDE_BUY ? "sell" : "buy");
    },

    onPriceType1Change: function (oEvent) {
      var oCtx = oEvent.getSource().getBindingContext("rfqCrt");
      if (!oCtx) { return; }
      var sPath = oCtx.getPath();
      var oModel = this.getViewModel();
      oModel.setProperty(sPath + "/leg1/monthName", "");
      oModel.setProperty(sPath + "/leg1/year", "");
      oModel.setProperty(sPath + "/leg1/startDate", "");
      oModel.setProperty(sPath + "/leg1/endDate", "");
      oModel.setProperty(sPath + "/leg1/fixingDate", "");
      oModel.setProperty(sPath + "/leg1/settlementDate", "");
      oModel.setProperty(sPath + "/leg1/orderType", "");
      oModel.setProperty(sPath + "/leg1/limitPrice", "");
      this._autoCalcFixingDates(sPath);
    },

    onPriceType2Change: function (oEvent) {
      var oCtx = oEvent.getSource().getBindingContext("rfqCrt");
      if (!oCtx) { return; }
      var sPath = oCtx.getPath();
      var oModel = this.getViewModel();
      oModel.setProperty(sPath + "/leg2/monthName", "");
      oModel.setProperty(sPath + "/leg2/year", "");
      oModel.setProperty(sPath + "/leg2/startDate", "");
      oModel.setProperty(sPath + "/leg2/endDate", "");
      oModel.setProperty(sPath + "/leg2/fixingDate", "");
      oModel.setProperty(sPath + "/leg2/settlementDate", "");
      oModel.setProperty(sPath + "/leg2/orderType", "");
      oModel.setProperty(sPath + "/leg2/limitPrice", "");
      this._autoCalcFixingDates(sPath);
    },

    _autoCalcFixingDates: function (sTradePath) {
      var oModel = this.getViewModel();
      var pt1 = oModel.getProperty(sTradePath + "/leg1/priceType");
      var pt2 = oModel.getProperty(sTradePath + "/leg2/priceType");

      if ((pt1 === "Fix" || pt1 === "C2R") && (pt2 === "AVG" || pt2 === "AVGInter")) {
        var sMonth = oModel.getProperty(sTradePath + "/leg2/monthName");
        var sYear = oModel.getProperty(sTradePath + "/leg2/year");
        if (pt2 === "AVG" && sMonth && sYear) {
          var dLast = this._lastBusinessDayOfMonth(sMonth, parseInt(sYear, 10));
          if (dLast) {
            oModel.setProperty(sTradePath + "/leg1/fixingDate", this._toIso(dLast));
            oModel.setProperty(sTradePath + "/leg1/settlementDate", this._formatDate(this._addBusinessDays(dLast, 2)));
          }
        }
      }

      if ((pt2 === "Fix" || pt2 === "C2R") && (pt1 === "AVG" || pt1 === "AVGInter")) {
        var sMonth2 = oModel.getProperty(sTradePath + "/leg1/monthName");
        var sYear2 = oModel.getProperty(sTradePath + "/leg1/year");
        if (pt1 === "AVG" && sMonth2 && sYear2) {
          var dLast2 = this._lastBusinessDayOfMonth(sMonth2, parseInt(sYear2, 10));
          if (dLast2) {
            oModel.setProperty(sTradePath + "/leg2/fixingDate", this._toIso(dLast2));
            oModel.setProperty(sTradePath + "/leg2/settlementDate", this._formatDate(this._addBusinessDays(dLast2, 2)));
          }
        }
      }
    },

    /* ─── Calendar helpers (client-side LME approximation) ─── */

    _isWeekend: function (d) {
      var day = d.getDay();
      return day === 0 || day === 6;
    },

    _addBusinessDays: function (d, n) {
      var result = new Date(d);
      var added = 0;
      while (added < n) {
        result.setDate(result.getDate() + 1);
        if (!this._isWeekend(result)) {
          added++;
        }
      }
      return result;
    },

    _lastBusinessDayOfMonth: function (sMonth, iYear) {
      var MONTHS = {
        January: 0, February: 1, March: 2, April: 3, May: 4, June: 5,
        July: 6, August: 7, September: 8, October: 9, November: 10, December: 11
      };
      var iMonth = MONTHS[sMonth];
      if (iMonth === undefined) { return null; }
      var d = new Date(iYear, iMonth + 1, 0);
      while (this._isWeekend(d)) {
        d.setDate(d.getDate() - 1);
      }
      return d;
    },

    _toIso: function (d) {
      var mm = String(d.getMonth() + 1).padStart(2, "0");
      var dd = String(d.getDate()).padStart(2, "0");
      return d.getFullYear() + "-" + mm + "-" + dd;
    },

    _formatDate: function (d) {
      var dd = String(d.getDate()).padStart(2, "0");
      var mm = String(d.getMonth() + 1).padStart(2, "0");
      var yy = String(d.getFullYear()).slice(-2);
      return dd + "/" + mm + "/" + yy;
    },

    /* ─── Counterparty selection ─── */

    onCounterpartySelectionChange: function () {
      var oModel = this.getViewModel();
      var aCps = oModel.getProperty("/counterparties") || [];
      var iCount = aCps.filter(function (c) { return c.selected; }).length;
      oModel.setProperty("/selectedCount", iCount);
    },

    formatChannelType: function (sType) {
      return CHANNEL_LABELS[sType] || sType || "—";
    },

    /* ─── Validation ─── */

    _validate: function () {
      var oModel = this.getViewModel();
      var sQty = oModel.getProperty("/quantity");
      var fQty = parseFloat(sQty);
      if (!sQty || isNaN(fQty) || fQty <= 0) {
        return "Informe uma quantidade válida (maior que zero).";
      }

      var aTrades = oModel.getProperty("/trades") || [];
      if (aTrades.length === 0) {
        return "Adicione pelo menos um trade.";
      }

      for (var i = 0; i < aTrades.length; i++) {
        var sErr = this._validateTrade(aTrades[i], i);
        if (sErr) { return sErr; }
      }
      return null;
    },

    _validateTrade: function (oTrade, idx) {
      var sLabel = "Trade " + (idx + 1);
      var sErr = this._validateLeg(oTrade.leg1, sLabel + " Leg 1");
      if (sErr) { return sErr; }

      var sTrade = this.getViewModel().getProperty("/tradeType");
      if (sTrade === "Swap") {
        sErr = this._validateLeg(oTrade.leg2, sLabel + " Leg 2");
        if (sErr) { return sErr; }
        if (oTrade.leg1.side === oTrade.leg2.side) {
          return sLabel + ": Leg 1 e Leg 2 devem ter lados opostos (Buy/Sell).";
        }
      }
      return null;
    },

    _validateLeg: function (oLeg, sLabel) {
      if (!oLeg.priceType) {
        return sLabel + ": Selecione o tipo de preço.";
      }
      if (oLeg.priceType === "AVG") {
        if (!oLeg.monthName) { return sLabel + ": Selecione o mês."; }
        if (!oLeg.year) { return sLabel + ": Selecione o ano."; }
      }
      if (oLeg.priceType === "AVGInter") {
        if (!oLeg.startDate || !oLeg.endDate) {
          return sLabel + ": Informe as datas de início e fim.";
        }
      }
      if (oLeg.orderType === "Limit") {
        var fLp = parseFloat(oLeg.limitPrice);
        if (!oLeg.limitPrice || isNaN(fLp)) {
          return sLabel + ": Informe o preço limite.";
        }
      }
      return null;
    },

    /* ─── Generate text flow ─── */

    onGenerate: function () {
      var sErr = this._validate();
      if (sErr) {
        this.getViewModel().setProperty("/errorMessage", sErr);
        return;
      }
      this.getViewModel().setProperty("/errorMessage", "");
      this._callPreviewForAllTrades();
    },

    _buildLegPayload: function (oLeg, fQty) {
      var oPayload = {
        side: oLeg.side,
        price_type: oLeg.priceType,
        quantity_mt: fQty
      };

      if (oLeg.priceType === "AVG") {
        oPayload.month_name = oLeg.monthName;
        oPayload.year = parseInt(oLeg.year, 10);
      } else if (oLeg.priceType === "AVGInter") {
        oPayload.start_date = oLeg.startDate;
        oPayload.end_date = oLeg.endDate;
      } else if (oLeg.priceType === "Fix" || oLeg.priceType === "C2R") {
        if (oLeg.fixingDate) {
          oPayload.fixing_date = oLeg.fixingDate;
        }
      }

      if (oLeg.orderType && (oLeg.priceType === "Fix" || oLeg.priceType === "C2R")) {
        oPayload.order_type = oLeg.orderType;
        if (oLeg.orderType !== "At Market") {
          oPayload.order_validity = oLeg.orderValidity;
          if (oLeg.orderType === "Limit") {
            oPayload.order_limit_price = oLeg.limitPrice;
          }
        }
      }

      return oPayload;
    },

    _callPreviewForAllTrades: function () {
      var oModel = this.getViewModel();
      var aTrades = oModel.getProperty("/trades") || [];
      var iCompany = oModel.getProperty("/companyIndex");
      var sTrade = oModel.getProperty("/tradeType");
      var fQty = parseFloat(oModel.getProperty("/quantity"));

      var aPromises = aTrades.map(function (oTrade) {
        var oPayload = {
          trade_type: sTrade,
          leg1: this._buildLegPayload(oTrade.leg1, fQty),
          sync_ppt: false,
          company_header: COMPANY_MAP[iCompany].header,
          company_label_for_payoff: COMPANY_MAP[iCompany].label,
          channel_type: "BROKER_LME"
        };
        if (sTrade === "Swap") {
          oPayload.leg2 = this._buildLegPayload(oTrade.leg2, fQty);
        }
        return rfqService.previewText(oPayload);
      }.bind(this));

      oModel.setProperty("/busy", true);
      oModel.setProperty("/errorMessage", "");

      Promise.all(aPromises).then(function (aResults) {
        var aEnTexts = [];
        var aPtTexts = [];
        var aPptInfo = [];

        aResults.forEach(function (oResult, i) {
          var sPrefix = aTrades.length > 1 ? "--- Trade " + (i + 1) + " ---\n" : "";
          aEnTexts.push(sPrefix + (oResult.text_en || oResult.text || ""));
          aPtTexts.push(sPrefix + (oResult.text_pt || ""));
          if (oResult.leg1_ppt) { aPptInfo.push("T" + (i + 1) + " Leg1 PPT: " + oResult.leg1_ppt); }
          if (oResult.leg2_ppt) { aPptInfo.push("T" + (i + 1) + " Leg2 PPT: " + oResult.leg2_ppt); }
          if (oResult.trade_ppt) { aPptInfo.push("T" + (i + 1) + " Trade PPT: " + oResult.trade_ppt); }
        });

        oModel.setProperty("/textEn", aEnTexts.join("\n\n"));
        oModel.setProperty("/textPt", aPtTexts.join("\n\n"));
        oModel.setProperty("/pptInfo", aPptInfo.join("  |  "));
        oModel.setProperty("/showResult", true);
      }).catch(function (oError) {
        var sMsg = this._formatError(oError);
        oModel.setProperty("/errorMessage", sMsg);
        MessageBox.error(sMsg);
      }.bind(this)).finally(function () {
        oModel.setProperty("/busy", false);
      });
    },

    /* ─── Copy / Share ─── */

    _copyToClipboard: function (sText) {
      if (!sText) { return; }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(sText).then(function () {
          MessageToast.show("Texto copiado!");
        });
      } else {
        var ta = document.createElement("textarea");
        ta.value = sText;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        MessageToast.show("Texto copiado!");
      }
    },

    onCopyTextEn: function () {
      this._copyToClipboard(this.getViewModel().getProperty("/textEn"));
    },

    onCopyTextPt: function () {
      this._copyToClipboard(this.getViewModel().getProperty("/textPt"));
    },

    onSendWhatsApp: function () {
      var sText = this.getViewModel().getProperty("/textEn");
      if (!sText) { return; }
      window.open("https://wa.me/?text=" + encodeURIComponent(sText), "_blank");
    },

    /* ─── Submit / Cancel ─── */

    onSubmitRfq: function () {
      var sErr = this._validate();
      if (sErr) {
        this.getViewModel().setProperty("/errorMessage", sErr);
        return;
      }
      var oModel = this.getViewModel();
      var aCps = (oModel.getProperty("/counterparties") || []).filter(function (c) { return c.selected; });
      if (aCps.length === 0) {
        MessageBox.warning("Selecione ao menos uma contraparte.");
        return;
      }
      MessageToast.show("RFQ enviada com sucesso.");
      this.navToList("rfq");
    },

    onCancel: function () {
      this.navToList("rfq");
    }
  });
});
