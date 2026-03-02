sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "sap/f/library"
], function (BaseController, fioriLibrary) {
  "use strict";

  var LayoutType = fioriLibrary.LayoutType;

  return BaseController.extend("hedgecontrol.controller.RfqDocument", {
    onInit: function () {
      this.initViewModel("rfqDoc", {
        title: "",
        pdfSource: "",
        loading: false,
        errorMessage: ""
      });
      this.getRouter().getRoute("rfqDocument").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (oEvent) {
      var oArgs = oEvent.getParameter("arguments");
      this._sRfqId = oArgs.rfqId;
      this._sDocType = oArgs.docType || "contract";
      this._loadDocument();
    },

    /**
     * Load document based on type.
     * Placeholder — actual endpoint to be implemented.
     */
    _loadDocument: function () {
      var oModel = this.getViewModel();
      oModel.setProperty("/loading", true);
      oModel.setProperty("/errorMessage", "");

      var sTitle = this._sDocType === "contract"
        ? this.getI18nText("docContract")
        : this._sDocType === "negotiation"
          ? this.getI18nText("docNegotiationNote")
          : this.getI18nText("viewDocuments");

      oModel.setProperty("/title", sTitle);

      // TODO: Replace with actual document endpoint when available
      // For now, set a placeholder source
      var sBaseUrl = sap.ui.require("hedgecontrol/service/apiClient")
        ? "" : "";
      oModel.setProperty("/pdfSource", "");
      oModel.setProperty("/loading", false);
    },

    onPdfLoaded: function () {
      this.getViewModel().setProperty("/loading", false);
    },

    onPdfError: function () {
      var oModel = this.getViewModel();
      oModel.setProperty("/loading", false);
      oModel.setProperty("/errorMessage", this.getI18nText("docLoadError"));
    },

    onDownload: function () {
      var sSource = this.getViewModel().getProperty("/pdfSource");
      if (sSource) {
        sap.m.URLHelper.redirect(sSource, true);
      }
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
