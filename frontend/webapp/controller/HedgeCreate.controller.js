sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/hedgesService"
], function (BaseController, hedgesService) {
  "use strict";

  function _emptyForm() {
    return {
      counterparty_id: "",
      commodity: "",
      direction: "buy",
      tons: "",
      price_per_ton: "",
      premium_discount: "0",
      settlement_date: "",
      prompt_date: "",
      source_type: "manual",
      notes: ""
    };
  }

  return BaseController.extend("hedgecontrol.controller.HedgeCreate", {
    onInit: function () {
      this.initViewModel("hdgCrt", {
        form: _emptyForm()
      });
      this.getRouter().getRoute("hedgeCreate").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this.getViewModel().setProperty("/form", _emptyForm());
      this.getViewModel().setProperty("/errorMessage", "");
    },

    onSubmit: function () {
      var oModel = this.getViewModel();
      var oForm = oModel.getProperty("/form");

      if (!oForm.counterparty_id || !oForm.commodity || !oForm.tons || !oForm.price_per_ton || !oForm.settlement_date) {
        oModel.setProperty("/errorMessage", this.getI18nText("validationHedgeRequired"));
        return;
      }

      var oPayload = {
        counterparty_id: oForm.counterparty_id,
        commodity: oForm.commodity,
        direction: oForm.direction,
        tons: parseFloat(oForm.tons),
        price_per_ton: parseFloat(oForm.price_per_ton),
        premium_discount: parseFloat(oForm.premium_discount) || 0,
        settlement_date: oForm.settlement_date,
        source_type: oForm.source_type
      };
      if (oForm.prompt_date) { oPayload.prompt_date = oForm.prompt_date; }
      if (oForm.notes) { oPayload.notes = oForm.notes; }

      var that = this;
      this.submitData(function () {
        return hedgesService.create(oPayload);
      }, this.getI18nText("hedgeCreated")).then(function (oData) {
        if (oData) {
          that.navToList("hedges");
        }
      });
    },

    onCancel: function () {
      this.navToList("hedges");
    }
  });
});
