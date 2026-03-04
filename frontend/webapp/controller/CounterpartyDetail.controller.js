sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/counterpartiesService",
  "sap/m/MessageBox"
], function (BaseController, counterpartiesService, MessageBox) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.CounterpartyDetail", {
    onInit: function () {
      this.initViewModel("cptyDet", { detail: {}, editMode: false });
      this.getRouter().getRoute("counterpartyDetail").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (oEvent) {
      this._sId = oEvent.getParameter("arguments").counterpartyId;
      this.getViewModel().setProperty("/editMode", false);
      this._loadData();
    },

    _loadData: function () {
      this.loadData(function () {
        return counterpartiesService.getById(this._sId);
      }.bind(this), "/detail");
    },

    onToggleEdit: function () {
      var oModel = this.getViewModel();
      oModel.setProperty("/editMode", !oModel.getProperty("/editMode"));
    },

    onSave: function () {
      var oModel = this.getViewModel();
      var oDetail = oModel.getProperty("/detail");
      var oPayload = {
        name: oDetail.name,
        short_name: oDetail.short_name,
        tax_id: oDetail.tax_id,
        country: oDetail.country,
        city: oDetail.city,
        contact_name: oDetail.contact_name,
        contact_email: oDetail.contact_email,
        contact_phone: oDetail.contact_phone,
        whatsapp_phone: oDetail.whatsapp_phone,
        credit_limit_usd: oDetail.credit_limit_usd,
        kyc_status: oDetail.kyc_status,
        risk_rating: oDetail.risk_rating,
        is_active: oDetail.is_active,
        notes: oDetail.notes
      };

      var that = this;
      this.submitData(function () {
        return counterpartiesService.update(that._sId, oPayload);
      }, this.getI18nText("counterpartySaved")).then(function (oData) {
        if (oData) {
          oModel.setProperty("/detail", oData);
          oModel.setProperty("/editMode", false);
        }
      });
    },

    onDeactivate: function () {
      var that = this;
      MessageBox.confirm(this.getI18nText("confirmDeactivateCounterparty"), {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            that.submitData(function () {
              return counterpartiesService.remove(that._sId);
            }, that.getI18nText("counterpartyDeactivated")).then(function () {
              that.navToList("counterparties");
            });
          }
        }
      });
    },

    onClose: function () {
      this.navToList("counterparties");
    }
  });
});
