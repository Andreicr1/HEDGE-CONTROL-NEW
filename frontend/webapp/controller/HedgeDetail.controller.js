sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/hedgesService",
  "sap/m/MessageBox"
], function (BaseController, hedgesService, MessageBox) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.HedgeDetail", {
    onInit: function () {
      this.initViewModel("hdgDet", {
        detail: {},
        editMode: false
      });
      this.getRouter().getRoute("hedgeDetail").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (oEvent) {
      this._sHedgeId = oEvent.getParameter("arguments").hedgeId;
      this.getViewModel().setProperty("/editMode", false);
      this._loadData();
    },

    _loadData: function () {
      var that = this;
      this.loadData(function () {
        return hedgesService.getById(that._sHedgeId);
      }, "/detail");
    },

    onToggleEdit: function () {
      var oModel = this.getViewModel();
      oModel.setProperty("/editMode", !oModel.getProperty("/editMode"));
    },

    onSave: function () {
      var oModel = this.getViewModel();
      var oDetail = oModel.getProperty("/detail");
      var oPayload = {
        commodity: oDetail.commodity,
        direction: oDetail.direction,
        tons: oDetail.tons,
        price_per_ton: oDetail.price_per_ton,
        premium_discount: oDetail.premium_discount,
        settlement_date: oDetail.settlement_date,
        prompt_date: oDetail.prompt_date,
        notes: oDetail.notes
      };

      var that = this;
      this.submitData(function () {
        return hedgesService.update(that._sHedgeId, oPayload);
      }, this.getI18nText("hedgeSaved")).then(function (oData) {
        if (oData) {
          oModel.setProperty("/detail", oData);
          oModel.setProperty("/editMode", false);
        }
      });
    },

    onSetStatus: function (oEvent) {
      var sNewStatus = oEvent.getSource().data("status");
      var that = this;
      MessageBox.confirm(this.getI18nText("confirmStatusChange"), {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            that.submitData(function () {
              return hedgesService.updateStatus(that._sHedgeId, sNewStatus);
            }, that.getI18nText("hedgeStatusUpdated")).then(function (oData) {
              if (oData) {
                that.getViewModel().setProperty("/detail", oData);
              }
            });
          }
        }
      });
    },

    onCancel: function () {
      var that = this;
      MessageBox.confirm(this.getI18nText("confirmCancelHedge"), {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            that.submitData(function () {
              return hedgesService.cancel(that._sHedgeId);
            }, that.getI18nText("hedgeCancelled")).then(function () {
              that.navToList("hedges");
            });
          }
        }
      });
    },

    onClose: function () {
      this.navToList("hedges");
    }
  });
});
