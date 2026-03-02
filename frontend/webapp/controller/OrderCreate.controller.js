sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/ordersService"
], function (BaseController, ordersService) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.OrderCreate", {
    onInit: function () {
      this.initViewModel("ordCrt", {
        pageTitle: "",
        orderType: "",
        form: {
          price_type: "fixed",
          quantity_mt: "",
          pricing_convention: "",
          avg_entry_price: ""
        }
      });
      this.getRouter().getRoute("orderCreate").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (oEvent) {
      var sType = oEvent.getParameter("arguments").type;
      var oModel = this.getViewModel();
      oModel.setProperty("/orderType", sType);
      oModel.setProperty("/pageTitle",
        sType === "sales" ? this.getI18nText("newSalesOrder") : this.getI18nText("newPurchaseOrder"));
      // reset form
      oModel.setProperty("/form", {
        price_type: "fixed",
        quantity_mt: "",
        pricing_convention: "",
        avg_entry_price: ""
      });
      oModel.setProperty("/errorMessage", "");
    },

    onSubmit: function () {
      var oModel = this.getViewModel();
      var oForm = oModel.getProperty("/form");
      var sType = oModel.getProperty("/orderType");

      var oPayload = {
        price_type: oForm.price_type,
        quantity_mt: parseFloat(oForm.quantity_mt)
      };
      if (oForm.pricing_convention) {
        oPayload.pricing_convention = oForm.pricing_convention;
      }
      if (oForm.price_type === "fixed" && oForm.avg_entry_price) {
        oPayload.avg_entry_price = parseFloat(oForm.avg_entry_price);
      }

      if (isNaN(oPayload.quantity_mt) || oPayload.quantity_mt <= 0) {
        oModel.setProperty("/errorMessage", this.getI18nText("validationQuantityRequired"));
        return;
      }

      var that = this;
      var fnCall = sType === "sales"
        ? function () { return ordersService.createSales(oPayload); }
        : function () { return ordersService.createPurchase(oPayload); };

      this.submitData(fnCall, this.getI18nText("orderCreated")).then(function (oData) {
        if (oData) {
          that.navToList("orders");
        }
      });
    },

    onCancel: function () {
      this.navToList("orders");
    }
  });
});
