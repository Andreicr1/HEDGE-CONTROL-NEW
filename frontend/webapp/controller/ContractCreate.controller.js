sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/contractsService",
  "sap/m/MessageBox",
  "sap/m/MessageToast"
], function (BaseController, contractsService, MessageBox, MessageToast) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.ContractCreate", {

    onInit: function () {
      this.initViewModel("ctrCrt", this._emptyForm());
      this.getRouter().getRoute("contractCreate").attachPatternMatched(this._onRouteMatched, this);
    },

    _emptyForm: function () {
      return {
        commodity: "",
        quantity_mt: "",
        fixed_leg_side: "buy",
        variable_leg_side: "sell",
        errorMessage: ""
      };
    },

    _onRouteMatched: function () {
      this.getViewModel().setData(Object.assign({ busy: false }, this._emptyForm()));
    },

    onSubmit: function () {
      var oModel = this.getViewModel();
      var sCommodity = (oModel.getProperty("/commodity") || "").trim();
      var fQuantity = parseFloat(oModel.getProperty("/quantity_mt"));
      var sFixedSide = oModel.getProperty("/fixed_leg_side");
      var sVariableSide = sFixedSide === "buy" ? "sell" : "buy";

      if (!sCommodity) {
        oModel.setProperty("/errorMessage", this.getI18nText("commodityRequired"));
        return;
      }
      if (isNaN(fQuantity) || fQuantity <= 0) {
        oModel.setProperty("/errorMessage", this.getI18nText("quantityPositive"));
        return;
      }

      oModel.setProperty("/errorMessage", "");
      var oPayload = {
        commodity: sCommodity,
        quantity_mt: fQuantity,
        legs: [
          { side: sFixedSide, price_type: "fixed" },
          { side: sVariableSide, price_type: "variable" }
        ]
      };

      var that = this;
      oModel.setProperty("/busy", true);
      contractsService.createHedge(oPayload).then(function () {
        MessageToast.show(that.getI18nText("contractCreated"));
        that.navToList("contracts");
      }).catch(function (oError) {
        MessageBox.error(that._formatError(oError));
      }).finally(function () {
        oModel.setProperty("/busy", false);
      });
    },

    onCancel: function () {
      this.navToList("contracts");
    },

    hasError: function (sMsg) {
      return !!sMsg;
    }
  });
});
