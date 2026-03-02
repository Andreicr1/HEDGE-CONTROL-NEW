sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/rfqService",
  "sap/f/library"
], function (BaseController, rfqService, fioriLibrary) {
  "use strict";

  var LayoutType = fioriLibrary.LayoutType;

  return BaseController.extend("hedgecontrol.controller.RfqDocument", {
    onInit: function () {
      this.initViewModel("rfqDoc", {
        title: "",
        rfq: null,
        quotes: [],
        ranking: [],
        loading: false,
        errorMessage: "",
        htmlContent: ""
      });
      this.getRouter().getRoute("rfqDocument").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (oEvent) {
      var oArgs = oEvent.getParameter("arguments");
      this._sRfqId = oArgs.rfqId;
      this._loadDocument();
    },

    _loadDocument: function () {
      var oModel = this.getViewModel();
      oModel.setProperty("/loading", true);
      oModel.setProperty("/errorMessage", "");
      oModel.setProperty("/title", this.getI18nText("rfqDocumentTitle"));

      var that = this;
      Promise.all([
        rfqService.getById(this._sRfqId),
        rfqService.listQuotes(this._sRfqId),
        rfqService.getRanking(this._sRfqId).catch(function () { return { items: [] }; })
      ]).then(function (aResults) {
        var oRfq = aResults[0] || {};
        var aQuotes = (aResults[1] && aResults[1].items) ? aResults[1].items : (aResults[1] || []);
        var aRanking = (aResults[2] && aResults[2].items) ? aResults[2].items : [];

        oModel.setProperty("/rfq", oRfq);
        oModel.setProperty("/quotes", aQuotes);
        oModel.setProperty("/ranking", aRanking);
        oModel.setProperty("/title", "RFQ " + (oRfq.rfq_number || that._sRfqId.substring(0, 8)));

        that._buildHtmlSummary(oRfq, aQuotes, aRanking);
      }).catch(function (oError) {
        oModel.setProperty("/errorMessage", that._formatError(oError));
      }).finally(function () {
        oModel.setProperty("/loading", false);
      });
    },

    _buildHtmlSummary: function (oRfq, aQuotes, aRanking) {
      var aLines = [];
      aLines.push("<h2>RFQ " + (oRfq.rfq_number || "") + "</h2>");
      aLines.push("<table style='width:100%;border-collapse:collapse;'>");
      aLines.push("<tr><td style='padding:4px;font-weight:bold;width:180px;'>Estado</td><td>" + (oRfq.state || "") + "</td></tr>");
      aLines.push("<tr><td style='padding:4px;font-weight:bold;'>Commodity</td><td>" + (oRfq.commodity || "") + "</td></tr>");
      aLines.push("<tr><td style='padding:4px;font-weight:bold;'>Direção</td><td>" + (oRfq.direction || "") + "</td></tr>");
      aLines.push("<tr><td style='padding:4px;font-weight:bold;'>Quantidade (MT)</td><td>" + (oRfq.quantity_mt || "") + "</td></tr>");
      aLines.push("<tr><td style='padding:4px;font-weight:bold;'>Janela Entrega</td><td>" + (oRfq.delivery_window_start || "") + " — " + (oRfq.delivery_window_end || "") + "</td></tr>");
      aLines.push("<tr><td style='padding:4px;font-weight:bold;'>Criado em</td><td>" + (oRfq.created_at ? new Date(oRfq.created_at).toLocaleString() : "") + "</td></tr>");
      aLines.push("</table>");

      if (aQuotes.length > 0) {
        aLines.push("<h3 style='margin-top:16px;'>Cotações (" + aQuotes.length + ")</h3>");
        aLines.push("<table style='width:100%;border-collapse:collapse;border:1px solid #ccc;'>");
        aLines.push("<tr style='background:#f5f5f5;'><th style='padding:6px;border:1px solid #ccc;text-align:left;'>Contraparte</th><th style='padding:6px;border:1px solid #ccc;text-align:right;'>Preço</th><th style='padding:6px;border:1px solid #ccc;text-align:left;'>Recebido</th></tr>");
        aQuotes.forEach(function (q) {
          aLines.push("<tr>");
          aLines.push("<td style='padding:6px;border:1px solid #ccc;'>" + (q.counterparty_name || q.counterparty_id || "") + "</td>");
          aLines.push("<td style='padding:6px;border:1px solid #ccc;text-align:right;'>" + (q.price != null ? q.price : "") + "</td>");
          aLines.push("<td style='padding:6px;border:1px solid #ccc;'>" + (q.received_at ? new Date(q.received_at).toLocaleString() : "") + "</td>");
          aLines.push("</tr>");
        });
        aLines.push("</table>");
      }

      if (aRanking.length > 0) {
        aLines.push("<h3 style='margin-top:16px;'>Ranking</h3>");
        aLines.push("<table style='width:100%;border-collapse:collapse;border:1px solid #ccc;'>");
        aLines.push("<tr style='background:#f5f5f5;'><th style='padding:6px;border:1px solid #ccc;'>#</th><th style='padding:6px;border:1px solid #ccc;text-align:left;'>Contraparte</th><th style='padding:6px;border:1px solid #ccc;text-align:right;'>Preço</th></tr>");
        aRanking.forEach(function (r, i) {
          aLines.push("<tr>");
          aLines.push("<td style='padding:6px;border:1px solid #ccc;text-align:center;'>" + (i + 1) + "</td>");
          aLines.push("<td style='padding:6px;border:1px solid #ccc;'>" + (r.counterparty_name || r.counterparty_id || "") + "</td>");
          aLines.push("<td style='padding:6px;border:1px solid #ccc;text-align:right;'>" + (r.price != null ? r.price : "") + "</td>");
          aLines.push("</tr>");
        });
        aLines.push("</table>");
      }

      this.getViewModel().setProperty("/htmlContent", aLines.join(""));
    },

    onToggleEndFullScreen: function () {
      var oAppModel = this.getAppModel();
      var sCurrentLayout = oAppModel.getProperty("/layout");
      if (sCurrentLayout === LayoutType.ThreeColumnsEndExpanded) {
        oAppModel.setProperty("/layout", LayoutType.ThreeColumnsMidExpanded);
      } else {
        oAppModel.setProperty("/layout", LayoutType.ThreeColumnsEndExpanded);
      }
    },

    onCloseEndColumn: function () {
      this.setLayout(LayoutType.TwoColumnsMidExpanded);
      this.getRouter().navTo("rfqDetail", { rfqId: this._sRfqId }, false);
    }
  });
});
