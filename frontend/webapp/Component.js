sap.ui.define([
  "sap/ui/core/UIComponent",
  "hedgecontrol/model/models"
], function (UIComponent, models) {
  "use strict";

  return UIComponent.extend("hedgecontrol.Component", {
    metadata: {
      manifest: "json"
    },

    init: function () {
      UIComponent.prototype.init.apply(this, arguments);

      this.setModel(models.createAppModel(), "app");

      this.getRouter().initialize();
    }
  });
});