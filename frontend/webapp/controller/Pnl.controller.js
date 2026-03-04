sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/dealsService",
  "sap/m/MessageBox",
  "sap/m/MessageToast"
], function (BaseController, dealsService, MessageBox, MessageToast) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.Pnl", {

    onInit: function () {
      this.initViewModel("pl", {
        dealList: [],
        selectAll: false,
        resultLoaded: false,
        summaryText: "",
        totals: {},
        treeData: []
      });
      this.getRouter().getRoute("pnl").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this._loadDeals();
    },

    /* ─── Deal loading ─── */

    _loadDeals: function () {
      var oModel = this.getViewModel();
      dealsService.list({ limit: 200 }).then(function (oData) {
        var aItems = (oData.items || []).map(function (d) {
          var sLabel = (d.reference || "") + " – " + (d.name || d.commodity || "");
          return { id: d.id, label: sLabel, reference: d.reference, name: d.name };
        });
        oModel.setProperty("/dealList", aItems);
      }).catch(function () {
        oModel.setProperty("/dealList", []);
      });
    },

    /* ─── Filter actions ─── */

    onSelectAllDeals: function (oEvent) {
      var bSelected = oEvent.getParameter("selected");
      var oCombo = this.byId("pnlDealSelector");
      if (bSelected) {
        var aItems = oCombo.getItems();
        oCombo.setSelectedItems(aItems);
      } else {
        oCombo.removeAllSelectedItems();
      }
    },

    onDealSelectionChange: function () {
      var oModel = this.getViewModel();
      var oCombo = this.byId("pnlDealSelector");
      var aDealList = oModel.getProperty("/dealList") || [];
      var bAllSelected = oCombo.getSelectedItems().length === aDealList.length && aDealList.length > 0;
      oModel.setProperty("/selectAll", bAllSelected);
    },

    onCalculateBreakdown: function () {
      var oModel = this.getViewModel();
      var oCombo = this.byId("pnlDealSelector");
      var aSelectedItems = oCombo.getSelectedItems();
      var sDate = this.byId("pnlDatePicker").getValue();

      // Collect selected deal IDs (empty array = all deals on backend)
      var aIds = aSelectedItems.map(function (oItem) {
        return oItem.getKey();
      });

      // If "Select All" is checked or all are selected, send empty array
      var bSelectAll = oModel.getProperty("/selectAll");
      if (bSelectAll) {
        aIds = [];
      }

      if (!sDate) {
        // Default to today
        var oToday = new Date();
        sDate = oToday.getFullYear() + "-" +
          String(oToday.getMonth() + 1).padStart(2, "0") + "-" +
          String(oToday.getDate()).padStart(2, "0");
        this.byId("pnlDatePicker").setValue(sDate);
      }

      oModel.setProperty("/resultLoaded", false);
      var that = this;

      dealsService.getPnlBreakdown(aIds, sDate).then(function (oData) {
        oModel.setProperty("/totals", oData.totals || {});
        var aTree = that._buildTreeData(oData.deals || []);
        oModel.setProperty("/treeData", aTree);
        oModel.setProperty("/resultLoaded", true);

        var nDeals = (oData.deals || []).length;
        oModel.setProperty("/summaryText",
          nDeals + " deal(s) | Total P&L: " +
          that._fmt(oData.totals ? oData.totals.total_pnl : 0) + " USD"
        );
      }).catch(function (oError) {
        MessageBox.error(that._formatError(oError));
      });
    },

    /* ─── Tree building ─── */

    _buildTreeData: function (aDeals) {
      var that = this;
      return aDeals.map(function (oDeal) {
        // Physical group
        var aPhysicalChildren = (oDeal.physical_items || []).map(function (oItem) {
          return {
            description: oItem.order_type + " #" + (oItem.id || "").substring(0, 8),
            type: oItem.order_type,
            commodity: oItem.commodity || oDeal.commodity || "",
            quantity: oItem.quantity_mt,
            price: oItem.price,
            value: oItem.value,
            children: []
          };
        });

        var fPhysicalTotal = aPhysicalChildren.reduce(function (sum, c) {
          return sum + (c.value || 0);
        }, 0);

        var oPhysical = {
          description: that._getI18nText("pnlGroupPhysical"),
          type: "",
          commodity: "",
          quantity: null,
          price: null,
          value: fPhysicalTotal,
          children: aPhysicalChildren
        };

        // Financial group
        var aFinancialChildren = (oDeal.financial_items || []).map(function (oItem) {
          return {
            description: oItem.reference || (oItem.id || "").substring(0, 8),
            type: oItem.classification || "",
            commodity: oDeal.commodity || "",
            quantity: oItem.quantity_mt,
            price: oItem.entry_price,
            value: oItem.pnl,
            children: []
          };
        });

        var fFinancialTotal = aFinancialChildren.reduce(function (sum, c) {
          return sum + (c.value || 0);
        }, 0);

        var oFinancial = {
          description: that._getI18nText("pnlGroupFinancial"),
          type: "",
          commodity: "",
          quantity: null,
          price: null,
          value: fFinancialTotal,
          children: aFinancialChildren
        };

        // Deal root node
        return {
          description: (oDeal.deal_reference || "") + " – " + (oDeal.deal_name || ""),
          type: "Deal",
          commodity: oDeal.commodity || "",
          quantity: null,
          price: null,
          value: oDeal.total_pnl,
          children: [oPhysical, oFinancial]
        };
      });
    },

    _getI18nText: function (sKey) {
      return this.getView().getModel("i18n").getResourceBundle().getText(sKey);
    },

    /* ─── TreeTable expand/collapse ─── */

    onExpandAll: function () {
      this.byId("pnlTreeTable").expandToLevel(3);
    },

    onCollapseAll: function () {
      this.byId("pnlTreeTable").collapseAll();
    },

    /* ─── Helpers ─── */

    _fmt: function (fVal) {
      if (fVal === undefined || fVal === null) { return "0.00"; }
      return Number(fVal).toFixed(2);
    },

    formatPlState: function (fValue) {
      if (fValue === undefined || fValue === null) { return "None"; }
      var n = parseFloat(fValue);
      if (n > 0) { return "Success"; }
      if (n < 0) { return "Error"; }
      return "None";
    }
  });
});
