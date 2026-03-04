sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/counterpartiesService"
], function (BaseController, counterpartiesService) {
  "use strict";

  function _emptyForm() {
    return {
      type: "broker",
      name: "",
      short_name: "",
      tax_id: "",
      country: "",
      city: "",
      contact_name: "",
      contact_email: "",
      contact_phone: "",
      whatsapp_phone: "",
      credit_limit_usd: "",
      kyc_status: "pending",
      risk_rating: "medium",
      notes: ""
    };
  }

  return BaseController.extend("hedgecontrol.controller.CounterpartyCreate", {
    onInit: function () {
      this.initViewModel("cptyCrt", {
        form: _emptyForm()
      });
      this.getRouter().getRoute("counterpartyCreate").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this.getViewModel().setProperty("/form", _emptyForm());
      this.getViewModel().setProperty("/errorMessage", "");
    },

    onSubmit: function () {
      var oModel = this.getViewModel();
      var oForm = oModel.getProperty("/form");

      if (!oForm.name || !oForm.country) {
        oModel.setProperty("/errorMessage", this.getI18nText("validationNameCountryRequired"));
        return;
      }

      var oPayload = {
        type: oForm.type,
        name: oForm.name,
        country: oForm.country,
        kyc_status: oForm.kyc_status,
        risk_rating: oForm.risk_rating
      };

      if (oForm.short_name) { oPayload.short_name = oForm.short_name; }
      if (oForm.tax_id) { oPayload.tax_id = oForm.tax_id; }
      if (oForm.city) { oPayload.city = oForm.city; }
      if (oForm.contact_name) { oPayload.contact_name = oForm.contact_name; }
      if (oForm.contact_email) { oPayload.contact_email = oForm.contact_email; }
      if (oForm.contact_phone) { oPayload.contact_phone = oForm.contact_phone; }
      if (oForm.whatsapp_phone) { oPayload.whatsapp_phone = oForm.whatsapp_phone; }
      if (oForm.credit_limit_usd) { oPayload.credit_limit_usd = parseFloat(oForm.credit_limit_usd); }
      if (oForm.notes) { oPayload.notes = oForm.notes; }

      var that = this;
      this.submitData(function () {
        return counterpartiesService.create(oPayload);
      }, this.getI18nText("counterpartyCreated")).then(function (oData) {
        if (oData) {
          that.navToList("counterparties");
        }
      });
    },

    onCancel: function () {
      this.navToList("counterparties");
    }
  });
});
