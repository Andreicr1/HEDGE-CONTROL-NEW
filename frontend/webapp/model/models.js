sap.ui.define([
  "sap/ui/model/json/JSONModel",
  "sap/f/library"
], function (JSONModel, fioriLibrary) {
  "use strict";

  return {
    createAppModel: function () {
      return new JSONModel({
        layout: fioriLibrary.LayoutType.OneColumn,
        selectedKey: "home",
        title: "Hedge Control Platform",
        badge: "Admin read-only (no auth configured)",
        showNavButton: false,
        notificationsCount: "",
        userInitials: "AU"
      });
    }
  };
});
