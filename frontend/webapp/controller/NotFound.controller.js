sap.ui.define([
  "hedgecontrol/controller/BaseController"
], function (BaseController) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.NotFound", {
    onNavBack: function () {
      this.getRouter().navTo("home");
    }
  });
});
