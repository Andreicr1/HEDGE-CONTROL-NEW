sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/rfqService",
  "hedgecontrol/service/apiClient",
  "hedgecontrol/service/exposuresService",
  "sap/m/MessageBox",
  "sap/m/MessageToast"
], function (BaseController, rfqService, apiClient, exposuresService, MessageBox, MessageToast) {
  "use strict";

  var SIDE_BUY = 0;
  var SIDE_SELL = 1;

  var COMPANY_MAP = [
    { header: "Alcast Brasil", label: "Alcast Brasil" },
    { header: "Alcast Trading", label: "Alcast Trading" }
  ];

  function _emptyLeg(side) {
    return {
      sideIndex: side === "sell" ? SIDE_SELL : SIDE_BUY,
      side: side || "buy",
      priceType: "",
      monthName: "",
      year: String(new Date().getFullYear()),
      startDate: "",
      endDate: "",
      fixingDate: "",
      settlementDate: "",
      orderType: "At Market",
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
      commodity: "Aluminium",
      intent: "GLOBAL_POSITION",
      quantity: "",
      orderId: "",
      orders: [],
      exposureOriginal: "",
      exposureOpen: "",
      exposureCommodity: "",
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

    _onRouteMatched: function (oEvent) {
      var oData = _emptyForm();
      oData.errorMessage = "";
      oData.busy = false;
      var oModel = this.getViewModel();
      for (var k in oData) {
        oModel.setProperty("/" + k, oData[k]);
      }
      this._loadCounterparties();

      // Check for pre-selected orderId from query parameters (from Hedge button)
      var oArgs = oEvent.getParameter("arguments");
      var oQuery = oArgs["?query"] || {};
      if (oQuery.orderId) {
        oModel.setProperty("/intent", "COMMERCIAL_HEDGE");
        this._sPresetOrderId = oQuery.orderId;
        this._sPresetOrderType = oQuery.orderType || null;
        this._sPresetPriceType = oQuery.priceType || null;
        this._loadOrders();
      } else {
        this._sPresetOrderId = null;
        this._sPresetOrderType = null;
        this._sPresetPriceType = null;
      }
    },

    _loadCounterparties: function () {
      var oModel = this.getViewModel();
      apiClient.getJson("/counterparties?is_active=true&limit=200").then(function (oData) {
        var aItems = (oData && oData.items) || [];
        var aMapped = aItems.map(function (cp) {
          return {
            id: cp.id,
            name: cp.short_name || cp.name,
            type: cp.type || "broker",
            country: cp.country,
            whatsapp_phone: cp.whatsapp_phone || "",
            contact_email: cp.contact_email || "",
            selected: true
          };
        });
        oModel.setProperty("/counterparties", aMapped);
        oModel.setProperty("/selectedCount", aMapped.length);
      }).catch(function (err) {
        jQuery.sap.log.warning("Failed to load counterparties", err && err.message);
        oModel.setProperty("/counterparties", []);
      });
    },

    /* ─── Intent / Order / Exposure handlers ─── */

    onIntentChange: function () {
      var oModel = this.getViewModel();
      var sIntent = oModel.getProperty("/intent");
      oModel.setProperty("/showResult", false);
      oModel.setProperty("/orderId", "");
      oModel.setProperty("/exposureOriginal", "");
      oModel.setProperty("/exposureOpen", "");
      oModel.setProperty("/exposureCommodity", "");
      if (sIntent === "COMMERCIAL_HEDGE") {
        this._loadOrders();
      } else {
        oModel.setProperty("/orders", []);
      }
    },

    _loadOrders: function () {
      var oModel = this.getViewModel();
      var that = this;
      // Load exposures to populate the order selector — exposures contain commodity and open_tons
      exposuresService.listExposures({ limit: 200 }).then(function (oData) {
        var aItems = (oData && oData.items) || [];
        var aOpen = aItems.filter(function (e) {
          return (e.status === "open" || e.status === "partially_hedged")
            && e.price_type === "variable";
        });
        var aOrders = [{ key: "", text: "Selecione uma ordem..." }];
        aOpen.forEach(function (e) {
          var sType = e.source_type === "sales_order" ? "SO" : "PO";
          var sQty = e.open_tons ? parseFloat(e.open_tons).toFixed(1) : "0";
          aOrders.push({
            key: e.source_id,
            text: sType + " — " + (e.commodity || "") + " — " + sQty + " MT aberto — " + (e.source_id || "").substring(0, 8),
            exposure: e
          });
        });
        oModel.setProperty("/orders", aOrders);

        // If a preset orderId was provided, select it and load exposure
        if (that._sPresetOrderId) {
          var oMatch = aOrders.find(function (o) { return o.key === that._sPresetOrderId; });
          if (oMatch) {
            oModel.setProperty("/orderId", that._sPresetOrderId);
            that._applyExposureFromList(that._sPresetOrderId, aOrders);
          }
          that._sPresetOrderId = null;
        }
      }).catch(function () {
        oModel.setProperty("/orders", []);
      });
    },

    onOrderChange: function () {
      var oModel = this.getViewModel();
      var sOrderId = oModel.getProperty("/orderId");
      oModel.setProperty("/showResult", false);
      if (!sOrderId) {
        oModel.setProperty("/exposureOriginal", "");
        oModel.setProperty("/exposureOpen", "");
        oModel.setProperty("/exposureCommodity", "");
        return;
      }
      var aOrders = oModel.getProperty("/orders") || [];
      this._applyExposureFromList(sOrderId, aOrders);
    },

    _applyExposureFromList: function (sOrderId, aOrders) {
      var oModel = this.getViewModel();
      var oMatch = aOrders.find(function (o) { return o.key === sOrderId; });
      if (oMatch && oMatch.exposure) {
        var e = oMatch.exposure;
        oModel.setProperty("/exposureOriginal", parseFloat(e.original_tons).toFixed(1));
        oModel.setProperty("/exposureOpen", parseFloat(e.open_tons).toFixed(1));
        oModel.setProperty("/exposureCommodity", e.commodity || "");
        // Auto-set commodity mapping from backend uppercase to Select keys
        if (e.commodity) {
          var mCommodityMap = {
            "ALUMINUM": "Aluminium", "ALUMINIUM": "Aluminium",
            "COPPER": "Copper", "ZINC": "Zinc",
            "NICKEL": "Nickel", "LEAD": "Lead", "TIN": "Tin"
          };
          var sMapped = mCommodityMap[(e.commodity || "").toUpperCase()];
          if (sMapped) {
            oModel.setProperty("/commodity", sMapped);
          }
        }
        oModel.setProperty("/quantity", String(e.open_tons || ""));

        // Auto-set trade sides based on order type:
        // PO → Buy Fix + Sell Variable (template "Queda")
        // SO → Sell Fix + Buy Variable (template "Alta")
        var sOrderType = e.order_type || (e.source_type === "purchase_order" ? "PO" : "SO");
        var sTradePath = "/trades/0";
        if (sOrderType === "PO") {
          // PO: Company buys at fixed price, hedges by buying AVG and selling Fix
          this._applyTemplate(sTradePath, {
            leg1: { sideIndex: SIDE_BUY, side: "buy", priceType: "AVG" },
            leg2: { sideIndex: SIDE_SELL, side: "sell", priceType: "Fix" }
          });
        } else {
          // SO: Company sells at fixed price, hedges by selling AVG and buying Fix
          this._applyTemplate(sTradePath, {
            leg1: { sideIndex: SIDE_SELL, side: "sell", priceType: "AVG" },
            leg2: { sideIndex: SIDE_BUY, side: "buy", priceType: "Fix" }
          });
        }
      } else {
        oModel.setProperty("/exposureOriginal", "");
        oModel.setProperty("/exposureOpen", "");
        oModel.setProperty("/exposureCommodity", "");
      }
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

      this._autoCalcFixingDates(sTradePath);
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

    onMonth1Change: function (oEvent) {
      var sPath = this._getTradePathFromEvent(oEvent);
      if (sPath) { this._autoCalcFixingDates(sPath); }
    },

    onYear1Change: function (oEvent) {
      var sPath = this._getTradePathFromEvent(oEvent);
      if (sPath) { this._autoCalcFixingDates(sPath); }
    },

    onMonth2Change: function (oEvent) {
      var sPath = this._getTradePathFromEvent(oEvent);
      if (sPath) { this._autoCalcFixingDates(sPath); }
    },

    onYear2Change: function (oEvent) {
      var sPath = this._getTradePathFromEvent(oEvent);
      if (sPath) { this._autoCalcFixingDates(sPath); }
    },

    onPriceType1Change: function (oEvent) {
      var oCtx = oEvent.getSource().getBindingContext("rfqCrt");
      if (!oCtx) { return; }
      var sPath = oCtx.getPath();
      var oModel = this.getViewModel();
      oModel.setProperty(sPath + "/leg1/monthName", "");
      oModel.setProperty(sPath + "/leg1/year", String(new Date().getFullYear()));
      oModel.setProperty(sPath + "/leg1/startDate", "");
      oModel.setProperty(sPath + "/leg1/endDate", "");
      oModel.setProperty(sPath + "/leg1/fixingDate", "");
      oModel.setProperty(sPath + "/leg1/settlementDate", "");
      oModel.setProperty(sPath + "/leg1/orderType", "At Market");
      oModel.setProperty(sPath + "/leg1/limitPrice", "");
      this._autoCalcFixingDates(sPath);
    },

    onPriceType2Change: function (oEvent) {
      var oCtx = oEvent.getSource().getBindingContext("rfqCrt");
      if (!oCtx) { return; }
      var sPath = oCtx.getPath();
      var oModel = this.getViewModel();
      oModel.setProperty(sPath + "/leg2/monthName", "");
      oModel.setProperty(sPath + "/leg2/year", String(new Date().getFullYear()));
      oModel.setProperty(sPath + "/leg2/startDate", "");
      oModel.setProperty(sPath + "/leg2/endDate", "");
      oModel.setProperty(sPath + "/leg2/fixingDate", "");
      oModel.setProperty(sPath + "/leg2/settlementDate", "");
      oModel.setProperty(sPath + "/leg2/orderType", "At Market");
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

    /* ─── Validation ─── */

    _validate: function () {
      var oModel = this.getViewModel();
      var sIntent = oModel.getProperty("/intent");

      // COMMERCIAL_HEDGE requires an order selection
      if (sIntent === "COMMERCIAL_HEDGE") {
        var sOrderId = oModel.getProperty("/orderId");
        if (!sOrderId) {
          return "Selecione uma ordem (PO/SO) para o hedge comercial.";
        }
      }

      var sQty = oModel.getProperty("/quantity");
      var fQty = parseFloat(sQty);
      if (!sQty || isNaN(fQty) || fQty <= 0) {
        return "Informe uma quantidade válida (maior que zero).";
      }

      // Limit quantity to exposure for COMMERCIAL_HEDGE
      if (sIntent === "COMMERCIAL_HEDGE") {
        var sOpen = oModel.getProperty("/exposureOpen");
        var fOpen = parseFloat(sOpen);
        if (!isNaN(fOpen) && fOpen > 0 && fQty > fOpen) {
          return "Quantidade (" + fQty + " MT) excede a exposição aberta (" + fOpen + " MT).";
        }
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
      var oPayload = this._buildCreatePayload();
      var that = this;
      this.submitData(function () {
        return rfqService.create(oPayload);
      }, "RFQ criada com sucesso.").then(function (oData) {
        if (oData && oData.id) {
          that.navToDetail("rfqDetail", { rfqId: oData.id });
        } else {
          that.navToList("rfq");
        }
      });
    },

    _buildCreatePayload: function () {
      var oModel = this.getViewModel();
      var sCommodity = oModel.getProperty("/commodity") || "Aluminium";
      var sIntent = oModel.getProperty("/intent") || "GLOBAL_POSITION";
      var fQty = parseFloat(oModel.getProperty("/quantity"));
      var aTrades = oModel.getProperty("/trades") || [];
      var oTrade = aTrades[0];

      // Derive direction from first leg side
      var sDirection = (oTrade.leg1.side || "buy").toUpperCase();

      // Derive delivery window from the first trade's legs
      var oWindow = this._deriveDeliveryWindow(oTrade);

      // Build invitations from selected counterparties
      var aCps = (oModel.getProperty("/counterparties") || []).filter(function (c) { return c.selected; });
      var aInvitations = aCps.map(function (cp) {
        return { counterparty_id: cp.id };
      });

      var oPayloadResult = {
        intent: sIntent,
        commodity: sCommodity,
        quantity_mt: fQty,
        delivery_window_start: oWindow.start,
        delivery_window_end: oWindow.end,
        direction: sDirection,
        invitations: aInvitations
      };

      // Include order_id for COMMERCIAL_HEDGE
      if (sIntent === "COMMERCIAL_HEDGE") {
        var sOrderId = oModel.getProperty("/orderId");
        if (sOrderId) {
          oPayloadResult.order_id = sOrderId;
        }
      }

      return oPayloadResult;
    },

    _deriveDeliveryWindow: function (oTrade) {
      var MONTHS = {
        January: 0, February: 1, March: 2, April: 3, May: 4, June: 5,
        July: 6, August: 7, September: 8, October: 9, November: 10, December: 11
      };
      var legs = [oTrade.leg1, oTrade.leg2];
      for (var i = 0; i < legs.length; i++) {
        var oLeg = legs[i];
        if (!oLeg) { continue; }
        if (oLeg.priceType === "AVG" && oLeg.monthName && oLeg.year) {
          var iMonth = MONTHS[oLeg.monthName];
          if (iMonth !== undefined) {
            var iYear = parseInt(oLeg.year, 10);
            var dStart = new Date(iYear, iMonth, 1);
            var dEnd = new Date(iYear, iMonth + 1, 0);
            return { start: this._toIso(dStart), end: this._toIso(dEnd) };
          }
        }
        if (oLeg.priceType === "AVGInter" && oLeg.startDate && oLeg.endDate) {
          return { start: oLeg.startDate, end: oLeg.endDate };
        }
      }
      // Fallback: current month
      var now = new Date();
      var dFallbackStart = new Date(now.getFullYear(), now.getMonth(), 1);
      var dFallbackEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0);
      return { start: this._toIso(dFallbackStart), end: this._toIso(dFallbackEnd) };
    },

    onCancel: function () {
      this.navToList("rfq");
    }
  });
});
