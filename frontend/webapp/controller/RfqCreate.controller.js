sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/rfqService"
], function (BaseController, rfqService) {
  "use strict";

  var _emptyForm = function () {
    return {
      intent: "COMMERCIAL_HEDGE",
      commodity: "",
      direction: "BUY",
      quantity_mt: "",
      delivery_window_start: "",
      delivery_window_end: "",
      order_id: ""
    };
  };

  return BaseController.extend("hedgecontrol.controller.RfqCreate", {
    onInit: function () {
      this.initViewModel("rfqCrt", {
        form: _emptyForm()
      });
      this.getRouter().getRoute("rfqCreate").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this.getViewModel().setProperty("/form", _emptyForm());
      this.getViewModel().setProperty("/errorMessage", "");
    },

    onSubmit: function () {
      var oModel = this.getViewModel();
      var oForm = oModel.getProperty("/form");

      if (!oForm.commodity || !oForm.quantity_mt || !oForm.delivery_window_start || !oForm.delivery_window_end) {
        oModel.setProperty("/errorMessage", this.getI18nText("validationRequiredFields"));
        return;
      }

      var oPayload = {
        intent: oForm.intent,
        commodity: oForm.commodity,
        direction: oForm.direction,
        quantity_mt: parseFloat(oForm.quantity_mt),
        delivery_window_start: oForm.delivery_window_start,
        delivery_window_end: oForm.delivery_window_end,
        invitations: []
      };
      if (oForm.order_id) {
        oPayload.order_id = oForm.order_id;
      }

      var that = this;
      this.submitData(function () {
        return rfqService.create(oPayload);
      }, this.getI18nText("rfqCreated")).then(function (oData) {
        if (oData) {
          that.navToList("rfq");
        }
      });
    },

    onCancel: function () {
      this.navToList("rfq");
    }
  });
});
