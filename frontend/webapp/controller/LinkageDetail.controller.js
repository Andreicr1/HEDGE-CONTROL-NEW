sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/linkagesService"
], function (BaseController, linkagesService) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.LinkageDetail", {

    onInit: function () {
      this.initViewModel("lnkDet", {});
      this.getRouter().getRoute("linkageDetail").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (oEvent) {
      this._sLinkageId = oEvent.getParameter("arguments").linkageId;
      this._loadLinkage();
    },

    _loadLinkage: function () {
      var oModel = this.getViewModel();
      oModel.setProperty("/busy", true);
      linkagesService.getById(this._sLinkageId).then(function (oData) {
        oModel.setData(Object.assign({ busy: false, errorMessage: "" }, oData));
      }).catch(function (oError) {
        oModel.setProperty("/busy", false);
        oModel.setProperty("/errorMessage", this._formatError(oError));
      }.bind(this));
    },

    onClose: function () {
      this.navToList("linkages");
    }
  });
});
