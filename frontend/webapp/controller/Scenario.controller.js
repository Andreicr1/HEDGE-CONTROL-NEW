sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "sap/ui/model/json/JSONModel",
  "sap/m/MessageBox",
  "sap/m/MessageToast",
  "sap/m/Dialog",
  "sap/m/VBox",
  "sap/m/Label",
  "sap/m/Input",
  "sap/m/Select",
  "sap/m/DatePicker",
  "sap/ui/core/Item",
  "sap/m/Button",
  "hedgecontrol/service/scenarioService"
], function (BaseController, JSONModel, MessageBox, MessageToast,
  Dialog, VBox, Label, Input, Select, DatePicker, Item, Button,
  scenarioService) {
  "use strict";

  function _emptyForm() {
    return {
      as_of_date: "",
      period_start: "",
      period_end: "",
      deltas: [],
      hasResults: false,
      results: null
    };
  }

  /** Build human-readable summary for a delta row */
  function _summary(d) {
    switch (d.delta_type) {
      case "add_unlinked_hedge_contract":
        return d.contract_id + " | " + d.quantity_mt + " MT | " + d.fixed_leg_side +
          " @ " + d.fixed_price_value + " " + (d.fixed_price_unit || "USD/MT");
      case "adjust_order_quantity_mt":
        return d.order_id + " → " + d.new_quantity_mt + " MT";
      case "add_cash_settlement_price_override":
        return d.symbol + " | " + d.settlement_date + " | " + d.price_usd + " USD";
      default:
        return JSON.stringify(d);
    }
  }

  return BaseController.extend("hedgecontrol.controller.Scenario", {

    onInit: function () {
      this.initViewModel("scen", _emptyForm());
      this.getRouter().getRoute("scenario").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this.getViewModel().setData(_emptyForm());
    },

    /* ─── Delta Management ─── */

    onAddDeltaHedge: function () {
      var oBundle = this.getOwnerComponent().getModel("i18n").getResourceBundle();
      this._openDeltaDialog("add_unlinked_hedge_contract", [
        { label: oBundle.getText("contractId"), key: "contract_id" },
        { label: oBundle.getText("quantityMt"), key: "quantity_mt", type: "number" },
        { label: oBundle.getText("fixedLegSide"), key: "fixed_leg_side", items: ["buy", "sell"] },
        { label: oBundle.getText("variableLegSide"), key: "variable_leg_side", items: ["buy", "sell"] },
        { label: oBundle.getText("fixedPriceValue"), key: "fixed_price_value", type: "number" },
        { label: oBundle.getText("fixedPriceUnit"), key: "fixed_price_unit", defaultVal: "USD/MT" },
        { label: oBundle.getText("floatPricingConvention"), key: "float_pricing_convention" }
      ]);
    },

    onAddDeltaOrder: function () {
      var oBundle = this.getOwnerComponent().getModel("i18n").getResourceBundle();
      this._openDeltaDialog("adjust_order_quantity_mt", [
        { label: oBundle.getText("orderId"), key: "order_id" },
        { label: oBundle.getText("scenarioNewQuantityMt"), key: "new_quantity_mt", type: "number" }
      ]);
    },

    onAddDeltaPrice: function () {
      var oBundle = this.getOwnerComponent().getModel("i18n").getResourceBundle();
      this._openDeltaDialog("add_cash_settlement_price_override", [
        { label: oBundle.getText("symbol"), key: "symbol" },
        { label: oBundle.getText("settlementDate"), key: "settlement_date", type: "date" },
        { label: oBundle.getText("scenarioPriceUsd"), key: "price_usd", type: "number" }
      ]);
    },

    _openDeltaDialog: function (sDeltaType, aFields) {
      var that = this;
      var aContent = [];
      var oRefs = {};

      aFields.forEach(function (f) {
        aContent.push(new Label({ text: f.label, required: true }));

        if (f.items) {
          var oSel = new Select({ width: "100%" });
          f.items.forEach(function (v) { oSel.addItem(new Item({ key: v, text: v })); });
          oRefs[f.key] = oSel;
          aContent.push(oSel);
        } else if (f.type === "date") {
          var oDP = new DatePicker({ displayFormat: "dd/MM/yyyy", valueFormat: "yyyy-MM-dd", width: "100%" });
          oRefs[f.key] = oDP;
          aContent.push(oDP);
        } else {
          var oInp = new Input({
            width: "100%",
            value: f.defaultVal || "",
            type: f.type === "number" ? "Number" : "Text"
          });
          oRefs[f.key] = oInp;
          aContent.push(oInp);
        }
      });

      var oDialog = new Dialog({
        title: that.getI18nText("scenarioDeltaTitle"),
        type: "Message",
        content: new VBox({ items: aContent }).addStyleClass("sapUiSmallMargin"),
        beginButton: new Button({
          text: that.getI18nText("btnAdd"),
          type: "Emphasized",
          press: function () {
            var oDelta = { delta_type: sDeltaType };
            var bValid = true;

            aFields.forEach(function (f) {
              var ctrl = oRefs[f.key];
              var val;
              if (f.items) {
                val = ctrl.getSelectedKey();
              } else if (f.type === "date") {
                val = ctrl.getValue();
              } else {
                val = ctrl.getValue();
                if (f.type === "number" && val) {
                  val = parseFloat(val);
                }
              }
              if (!val && val !== 0) { bValid = false; }
              oDelta[f.key] = val;
            });

            if (!bValid) {
              MessageToast.show(that.getI18nText("msgAllFieldsRequired"));
              return;
            }

            oDelta._summary = _summary(oDelta);
            var oModel = that.getViewModel();
            var aDeltas = oModel.getProperty("/deltas");
            aDeltas.push(oDelta);
            oModel.setProperty("/deltas", aDeltas);
            oDialog.close();
          }
        }),
        endButton: new Button({
          text: that.getI18nText("cancel"),
          press: function () { oDialog.close(); }
        }),
        afterClose: function () { oDialog.destroy(); }
      });

      oDialog.open();
    },

    onRemoveDelta: function (oEvent) {
      var oCtx = oEvent.getSource().getBindingContext("scen");
      var sPath = oCtx.getPath();
      var idx = parseInt(sPath.split("/").pop(), 10);
      var oModel = this.getViewModel();
      var aDeltas = oModel.getProperty("/deltas");
      aDeltas.splice(idx, 1);
      oModel.setProperty("/deltas", aDeltas);
    },

    /* ─── Run ─── */

    onRunWhatIf: function () {
      var oModel = this.getViewModel();
      var sAsOf = oModel.getProperty("/as_of_date");
      var sPeriodStart = oModel.getProperty("/period_start");
      var sPeriodEnd = oModel.getProperty("/period_end");

      if (!sAsOf || !sPeriodStart || !sPeriodEnd) {
        MessageBox.warning(this.getI18nText("msgFillPeriodParams"));
        return;
      }

      var aDeltas = (oModel.getProperty("/deltas") || []).map(function (d) {
        var oCopy = Object.assign({}, d);
        delete oCopy._summary;
        return oCopy;
      });

      var oPayload = {
        as_of_date: sAsOf,
        period_start: sPeriodStart,
        period_end: sPeriodEnd,
        deltas: aDeltas
      };

      var that = this;
      scenarioService.runWhatIf(oPayload)
        .then(function (oData) {
          oModel.setProperty("/results", oData);
          oModel.setProperty("/hasResults", true);
          MessageToast.show(that.getI18nText("whatIfCompleted"));
        })
        .catch(function (err) {
          MessageBox.error(that._formatError(err));
        });
    }
  });
});
