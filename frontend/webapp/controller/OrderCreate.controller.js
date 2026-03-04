sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/ordersService",
  "hedgecontrol/service/dealsService"
], function (BaseController, ordersService, dealsService) {
  "use strict";

  var _EMPTY_FORM = {
    deal_id: "",
    counterparty_name: "",
    price_type: "fixed",
    avg_entry_price: "",
    pricing_convention: "",
    reference_month: "",
    observation_date_start: "",
    observation_date_end: "",
    fixing_date: "",
    quantity_mt: "",
    notes: ""
  };

  return BaseController.extend("hedgecontrol.controller.OrderCreate", {
    onInit: function () {
      this.initViewModel("ordCrt", {
        pageTitle: "",
        orderType: "",
        deals: [],
        form: Object.assign({}, _EMPTY_FORM)
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
      oModel.setProperty("/form", Object.assign({}, _EMPTY_FORM));
      oModel.setProperty("/errorMessage", "");
      this._loadDeals();
    },

    _loadDeals: function () {
      var that = this;
      dealsService.list().then(function (oData) {
        var aItems = (oData && oData.items) || [];
        that.getViewModel().setProperty("/deals", aItems);
      }).catch(function () {
        // silently fail – deals dropdown will be empty
      });
    },

    onDealChange: function () {
      var oModel = this.getViewModel();
      if (oModel.getProperty("/form/deal_id")) {
        oModel.setProperty("/errorMessage", "");
      }
    },

    onPriceTypeChange: function () {
      var oModel = this.getViewModel();
      var sPriceType = oModel.getProperty("/form/price_type");
      // Clear conditional fields when switching price type
      if (sPriceType === "fixed") {
        oModel.setProperty("/form/pricing_convention", "");
        oModel.setProperty("/form/reference_month", "");
        oModel.setProperty("/form/observation_date_start", "");
        oModel.setProperty("/form/observation_date_end", "");
        oModel.setProperty("/form/fixing_date", "");
      } else {
        oModel.setProperty("/form/avg_entry_price", "");
      }
    },

    onConventionChange: function () {
      var oModel = this.getViewModel();
      // Clear all convention-specific fields, user fills the relevant one
      oModel.setProperty("/form/reference_month", "");
      oModel.setProperty("/form/observation_date_start", "");
      oModel.setProperty("/form/observation_date_end", "");
      oModel.setProperty("/form/fixing_date", "");
    },

    onCreateNewDeal: function () {
      this.getRouter().navTo("dealCreate");
    },

    onSubmit: function () {
      var oModel = this.getViewModel();
      var oForm = oModel.getProperty("/form");
      var sType = oModel.getProperty("/orderType");

      // Validate deal selection
      if (!oForm.deal_id) {
        oModel.setProperty("/errorMessage", this.getI18nText("dealRequired"));
        return;
      }

      var fQty = parseFloat(oForm.quantity_mt);
      if (isNaN(fQty) || fQty <= 0) {
        oModel.setProperty("/errorMessage", this.getI18nText("validationQuantityRequired"));
        return;
      }

      // Build payload
      var oPayload = {
        price_type: oForm.price_type,
        quantity_mt: fQty
      };

      // Counterparty name
      if (oForm.counterparty_name) {
        oPayload.counterparty_name = oForm.counterparty_name;
      }

      // Notes
      if (oForm.notes) {
        oPayload.notes = oForm.notes;
      }

      if (oForm.price_type === "fixed") {
        // Fixed price
        if (oForm.avg_entry_price) {
          oPayload.avg_entry_price = parseFloat(oForm.avg_entry_price);
        }
      } else {
        // Variable price
        if (!oForm.pricing_convention) {
          oModel.setProperty("/errorMessage", this.getI18nText("validationConventionRequired"));
          return;
        }
        oPayload.pricing_convention = oForm.pricing_convention;

        if (oForm.pricing_convention === "AVG") {
          if (!oForm.reference_month) {
            oModel.setProperty("/errorMessage", this.getI18nText("validationReferenceMonthRequired"));
            return;
          }
          oPayload.reference_month = oForm.reference_month;
        } else if (oForm.pricing_convention === "AVGInter") {
          if (!oForm.observation_date_start || !oForm.observation_date_end) {
            oModel.setProperty("/errorMessage", this.getI18nText("validationObservationDatesRequired"));
            return;
          }
          oPayload.observation_date_start = oForm.observation_date_start;
          oPayload.observation_date_end = oForm.observation_date_end;
        } else if (oForm.pricing_convention === "C2R") {
          if (!oForm.fixing_date) {
            oModel.setProperty("/errorMessage", this.getI18nText("validationFixingDateRequired"));
            return;
          }
          oPayload.fixing_date = oForm.fixing_date;
        }
      }

      var that = this;
      var sDealId = oForm.deal_id;
      var sLinkedType = sType === "sales" ? "sales_order" : "purchase_order";
      var fnCall = sType === "sales"
        ? function () { return ordersService.createSales(oPayload); }
        : function () { return ordersService.createPurchase(oPayload); };

      this.submitData(fnCall, this.getI18nText("orderCreated")).then(function (oData) {
        if (oData && oData.id) {
          return dealsService.addLink(sDealId, {
            linked_type: sLinkedType,
            linked_id: oData.id
          }).then(function () {
            that.navToList("orders");
          }).catch(function () {
            that.navToList("orders");
          });
        }
      });
    },

    onCancel: function () {
      this.navToList("orders");
    }
  });
});
