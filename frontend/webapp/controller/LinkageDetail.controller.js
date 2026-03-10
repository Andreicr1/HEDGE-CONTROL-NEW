sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/linkagesService",
  "hedgecontrol/service/ordersService",
  "hedgecontrol/service/contractsService"
], function (BaseController, linkagesService, ordersService, contractsService) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.LinkageDetail", {

    onInit: function () {
      this.initViewModel("lnkDet", { order: null, contract: null });
      this.getRouter().getRoute("linkageDetail").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (oEvent) {
      this._sLinkageId = oEvent.getParameter("arguments").linkageId;
      if (!this._isValidId(this._sLinkageId)) { this.getRouter().navTo("notFound"); return; }
      this._loadLinkage();
    },

    _loadLinkage: function () {
      var oModel = this.getViewModel();
      oModel.setProperty("/busy", true);
      linkagesService.getById(this._sLinkageId).then(function (oData) {
        oModel.setData(Object.assign({ busy: false, errorMessage: "", order: null, contract: null }, oData));
        if (oData.order_id) {
          ordersService.getById(oData.order_id).then(function (o) {
            oModel.setProperty("/order", o || null);
          }).catch(function () { oModel.setProperty("/order", null); });
        }
        if (oData.contract_id) {
          contractsService.getHedgeById(oData.contract_id).then(function (c) {
            oModel.setProperty("/contract", c || null);
          }).catch(function () { oModel.setProperty("/contract", null); });
        }
      }).catch(function (oError) {
        oModel.setProperty("/busy", false);
        oModel.setProperty("/errorMessage", this._formatError(oError));
      }.bind(this));
    },

    onExit: function () {
      this.getRouter().getRoute("linkageDetail").detachPatternMatched(this._onRouteMatched, this);
    },

    onClose: function () {
      this.navToList("linkages");
    }
  });
});
