sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/linkagesService",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator",
  "sap/m/Dialog",
  "sap/m/Button",
  "sap/m/Label",
  "sap/m/Input",
  "sap/m/MessageBox",
  "sap/m/MessageToast",
  "sap/ui/layout/form/Form",
  "sap/ui/layout/form/FormContainer",
  "sap/ui/layout/form/FormElement",
  "sap/ui/layout/form/ColumnLayout"
], function (BaseController, linkagesService, Filter, FilterOperator,
  Dialog, Button, Label, Input, MessageBox, MessageToast,
  Form, FormContainer, FormElement, ColumnLayout) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.LinkagesList", {

    onInit: function () {
      this.initViewModel("lnk", { items: [] });
      this.getRouter().getRoute("linkages").attachPatternMatched(this._onRouteMatched, this);
      this.getRouter().getRoute("linkageDetail").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this._loadLinkages();
    },

    _loadLinkages: function () {
      var oModel = this.getViewModel();
      oModel.setProperty("/busy", true);
      linkagesService.list().then(function (oResponse) {
        oModel.setProperty("/items", oResponse.items || []);
      }).catch(function (oError) {
        oModel.setProperty("/errorMessage", this._formatError(oError));
      }.bind(this)).finally(function () {
        oModel.setProperty("/busy", false);
      });
    },

    onSearch: function (oEvent) {
      var sQuery = oEvent.getParameter("newValue");
      var oList = this.byId("linkagesList");
      var oBinding = oList.getBinding("items");
      if (!sQuery) {
        oBinding.filter([]);
        return;
      }
      var aFilters = [
        new Filter("order_id", FilterOperator.Contains, sQuery),
        new Filter("contract_id", FilterOperator.Contains, sQuery)
      ];
      oBinding.filter(new Filter({ filters: aFilters, and: false }));
    },

    onLinkageSelect: function (oEvent) {
      var oItem = oEvent.getParameter("listItem");
      var sId = oItem.getBindingContext("lnk").getProperty("id");
      this.navToDetail("linkageDetail", { linkageId: sId });
    },

    onCreateLinkage: function () {
      var that = this;
      var oOrderIdInput = new Input({ placeholder: that.getI18nText("placeholderOrderId"), required: true });
      var oContractIdInput = new Input({ placeholder: that.getI18nText("placeholderContractId"), required: true });
      var oQuantityInput = new Input({ placeholder: "0,00", type: "Number", required: true });

      var oDialog = new Dialog({
        title: that.getI18nText("newLinkage"),
        type: "Message",
        content: [
          new Form({
            editable: true,
            layout: new ColumnLayout({ columnsM: 1, columnsL: 1 }),
            formContainers: [
              new FormContainer({
                formElements: [
                  new FormElement({ label: new Label({ text: that.getI18nText("orderId"), required: true }), fields: [oOrderIdInput] }),
                  new FormElement({ label: new Label({ text: that.getI18nText("contractId"), required: true }), fields: [oContractIdInput] }),
                  new FormElement({ label: new Label({ text: that.getI18nText("quantityMt"), required: true }), fields: [oQuantityInput] })
                ]
              })
            ]
          })
        ],
        beginButton: new Button({
          text: that.getI18nText("submit"),
          type: "Emphasized",
          press: function () {
            var sOrderId = oOrderIdInput.getValue().trim();
            var sContractId = oContractIdInput.getValue().trim();
            var fQuantity = parseFloat(oQuantityInput.getValue());

            if (!sOrderId || !sContractId) {
              MessageBox.warning(that.getI18nText("allFieldsRequired"));
              return;
            }
            if (isNaN(fQuantity) || fQuantity <= 0) {
              MessageBox.warning(that.getI18nText("quantityPositive"));
              return;
            }

            linkagesService.create({
              order_id: sOrderId,
              contract_id: sContractId,
              quantity_mt: fQuantity
            }).then(function () {
              MessageToast.show(that.getI18nText("linkageCreated"));
              oDialog.close();
              that._loadLinkages();
            }).catch(function (oError) {
              MessageBox.error(that._formatError(oError));
            });
          }
        }),
        endButton: new Button({
          text: that.getI18nText("cancel"),
          press: function () { oDialog.close(); }
        }),
        afterClose: function () { oDialog.destroy(); }
      });

      oDialog.open();
    }
  });
});
