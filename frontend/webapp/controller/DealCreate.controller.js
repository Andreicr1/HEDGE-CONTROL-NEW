sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/dealsService"
], function (BaseController, dealsService) {
  "use strict";

  function _emptyForm() {
    return {
      name: "",
      commodity: ""
    };
  }

  return BaseController.extend("hedgecontrol.controller.DealCreate", {
    onInit: function () {
      this.initViewModel("dealCrt", {
        form: _emptyForm()
      });
      this.getRouter().getRoute("dealCreate").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this.getViewModel().setProperty("/form", _emptyForm());
      this.getViewModel().setProperty("/errorMessage", "");
    },

    onSubmit: function () {
      var oModel = this.getViewModel();
      var oForm = oModel.getProperty("/form");

      if (!oForm.name || !oForm.commodity) {
        oModel.setProperty("/errorMessage", this.getI18nText("validationDealNameCommodityRequired"));
        return;
      }

      var oPayload = {
        name: oForm.name,
        commodity: oForm.commodity
      };

      var that = this;
      this.submitData(function () {
        return dealsService.create(oPayload);
      }, this.getI18nText("dealCreated")).then(function (oData) {
        if (oData) {
          that.navToList("deals");
        }
      });
    },

    onCancel: function () {
      this.navToList("deals");
    }
  });
});
