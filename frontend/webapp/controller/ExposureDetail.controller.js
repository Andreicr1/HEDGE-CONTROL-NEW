sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/exposuresService"
], function (BaseController, exposuresService) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.ExposureDetail", {
    onInit: function () {
      this.initViewModel("expDetail", {
        detail: {}
      });
      this.getRouter()
        .getRoute("exposureDetail")
        .attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (oEvent) {
      var sExposureId = oEvent.getParameter("arguments").exposureId;
      this._loadExposure(sExposureId);
    },

    _loadExposure: function (sId) {
      this.loadData(function () {
        return exposuresService.getExposure(sId);
      }, "/detail");
    },

    onClose: function () {
      this.navToList("exposures");
    },

    onHedge: function () {
      var oDetail = this.getViewModel().getProperty("/detail") || {};
      this.getRouter().navTo("rfqCreate", {
        "?query": {
          orderId: oDetail.source_id || "",
          orderType: oDetail.order_type || "",
          priceType: oDetail.price_type || ""
        }
      });
    }
  });
});
