sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/ordersService",
  "hedgecontrol/service/dealsService",
  "hedgecontrol/service/linkagesService",
  "sap/m/MessageBox"
], function (BaseController, ordersService, dealsService, linkagesService, MessageBox) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.OrderDetail", {
    onInit: function () {
      this.initViewModel("ordDet", {
        detail: {},
        deal: null,
        linkages: []
      });
      this.getRouter().getRoute("orderDetail").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function (oEvent) {
      var sOrderId = oEvent.getParameter("arguments").orderId;
      if (!this._isValidId(sOrderId)) { this.getRouter().navTo("notFound"); return; }
      this._sOrderId = sOrderId;
      this._loadOrder(sOrderId);
    },

    _loadOrder: function (sOrderId) {
      var that = this;
      this.loadData(function () {
        return ordersService.getById(sOrderId);
      }, "/detail").then(function () {
        that._loadDeal();
        that._loadLinkages();
      });
    },

    _loadDeal: function () {
      var that = this;
      var oDetail = this.getViewModel().getProperty("/detail");
      if (!oDetail || !oDetail.id) { return; }
      var sLinkedType = oDetail.order_type === "SO" ? "sales_order" : "purchase_order";
      dealsService.findByLinkedEntity(sLinkedType, oDetail.id).then(function (oDeal) {
        that.getViewModel().setProperty("/deal", oDeal || null);
      }).catch(function () {
        that.getViewModel().setProperty("/deal", null);
      });
    },

    _loadLinkages: function () {
      var that = this;
      var sOrderId = this._sOrderId;
      linkagesService.list().then(function (aAll) {
        var aFiltered = (aAll || []).filter(function (l) {
          return l.order_id === sOrderId;
        });
        that.getViewModel().setProperty("/linkages", aFiltered);
      }).catch(function () {
        that.getViewModel().setProperty("/linkages", []);
      });
    },

    onNavigateToDeal: function () {
      var oDeal = this.getViewModel().getProperty("/deal");
      if (oDeal && oDeal.id) {
        this.navToDetail("dealDetail", { dealId: oDeal.id });
      }
    },

    onNavigateToContract: function (oEvent) {
      var oCtx = oEvent.getSource().getBindingContext("ordDet");
      if (oCtx) {
        var sContractId = oCtx.getProperty("contract_id");
        if (sContractId) {
          this.navToDetail("contractDetail", { contractId: sContractId });
        }
      }
    },

    onArchive: function () {
      var that = this;
      MessageBox.confirm(this.getI18nText("confirmArchive"), {
        onClose: function (sAction) {
          if (sAction === MessageBox.Action.OK) {
            that.submitData(function () {
              return ordersService.archive(that._sOrderId);
            }, that.getI18nText("orderArchived")).then(function () {
              that.navToList("orders");
            });
          }
        }
      });
    },

    onExit: function () {
      this.getRouter().getRoute("orderDetail").detachPatternMatched(this._onRouteMatched, this);
    },

    onClose: function () {
      this.navToList("orders");
    },

    onHedge: function () {
      var oDetail = this.getViewModel().getProperty("/detail") || {};
      this.getRouter().navTo("rfqCreate", {
        "?query": {
          orderId: this._sOrderId,
          orderType: oDetail.order_type || "",
          priceType: oDetail.price_type || ""
        }
      });
    }
  });
});
