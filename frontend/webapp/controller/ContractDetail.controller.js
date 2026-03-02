sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/contractsService",
  "sap/m/MessageBox"
], function (BaseController, contractsService, MessageBox) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.ContractDetail", {

    onInit: function () {
      this.initViewModel("ctrDet", {});
      this.getRouter().getRoute("contractDetail").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (oEvent) {
      this._sContractId = oEvent.getParameter("arguments").contractId;
      this._loadContract();
    },

    _loadContract: function () {
      var oModel = this.getViewModel();
      oModel.setProperty("/busy", true);
      contractsService.getHedgeById(this._sContractId).then(function (oData) {
        oModel.setData(Object.assign({ busy: false, errorMessage: "" }, oData));
      }).catch(function (oError) {
        oModel.setProperty("/busy", false);
        oModel.setProperty("/errorMessage", this._formatError(oError));
      }.bind(this));
    },

    onArchive: function () {
      var that = this;
      MessageBox.confirm(this.getI18nText("confirmArchiveContract"), {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            that.submitData(
              contractsService.archive(that._sContractId),
              that.getI18nText("contractArchived")
            ).then(function () {
              that.navToList("contracts");
            });
          }
        }
      });
    },

    onClose: function () {
      this.navToList("contracts");
    },

    isNotArchived: function (sDeletedAt) {
      return !sDeletedAt;
    },

    formatClassificationState: function (sClassification) {
      if (!sClassification) { return "None"; }
      return sClassification === "long" ? "Success" : "Error";
    }
  });
});
