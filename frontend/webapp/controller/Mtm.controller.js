sap.ui.define([
  "hedgecontrol/controller/BaseController",
  "hedgecontrol/service/contractsService",
  "hedgecontrol/service/mtmService",
  "sap/m/MessageBox"
], function (BaseController, contractsService, mtmService, MessageBox) {
  "use strict";

  return BaseController.extend("hedgecontrol.controller.Mtm", {

    onInit: function () {
      this.initViewModel("mtm", {
        contractList: [],
        selectAll: false,
        resultLoaded: false,
        summaryText: "",
        totals: {},
        treeData: []
      });
      this.getRouter().getRoute("mtm").attachPatternMatched(this._onRouteMatched, this);
    },

    _onRouteMatched: function () {
      this._loadContracts();
    },

    /* ─── Contract loading ─── */

    _loadContracts: function () {
      var oModel = this.getViewModel();
      contractsService.list().then(function (oData) {
        var aItems = (oData.items || oData || []).map(function (c) {
          var sLabel = (c.reference || (c.id || "").substring(0, 8)) + " – " + (c.commodity || "");
          return { id: c.id, label: sLabel, reference: c.reference, commodity: c.commodity };
        });
        oModel.setProperty("/contractList", aItems);
      }).catch(function () {
        oModel.setProperty("/contractList", []);
      });
    },

    /* ─── Filter actions ─── */

    onSelectAllContracts: function (oEvent) {
      var bSelected = oEvent.getParameter("selected");
      var oCombo = this.byId("mtmContractSelector");
      if (bSelected) {
        oCombo.setSelectedItems(oCombo.getItems());
      } else {
        oCombo.removeAllSelectedItems();
      }
    },

    onContractSelectionChange: function () {
      var oModel = this.getViewModel();
      var oCombo = this.byId("mtmContractSelector");
      var aList = oModel.getProperty("/contractList") || [];
      var bAll = oCombo.getSelectedItems().length === aList.length && aList.length > 0;
      oModel.setProperty("/selectAll", bAll);
    },

    /* ─── Calculate MTM for selected contracts ─── */

    onCalculateMtm: function () {
      var oModel = this.getViewModel();
      var oCombo = this.byId("mtmContractSelector");
      var aSelectedItems = oCombo.getSelectedItems();

      if (aSelectedItems.length === 0) {
        MessageBox.warning(this.getI18nText("mtmSelectAtLeastOne"));
        return;
      }

      var sDate = this.byId("mtmDatePicker").getValue();
      if (!sDate) {
        var oToday = new Date();
        sDate = oToday.getFullYear() + "-" +
          String(oToday.getMonth() + 1).padStart(2, "0") + "-" +
          String(oToday.getDate()).padStart(2, "0");
        this.byId("mtmDatePicker").setValue(sDate);
      }

      var aIds = aSelectedItems.map(function (oItem) { return oItem.getKey(); });

      oModel.setProperty("/resultLoaded", false);
      var that = this;

      // Call MTM for each selected contract in parallel
      var aPromises = aIds.map(function (sId) {
        return mtmService.getForHedgeContract(sId, sDate).then(function (oData) {
          return { id: sId, data: oData, error: null };
        }).catch(function (err) {
          return { id: sId, data: null, error: err };
        });
      });

      Promise.all(aPromises).then(function (aResults) {
        var aSuccessful = aResults.filter(function (r) { return r.data !== null; });
        var aContractList = oModel.getProperty("/contractList") || [];

        // Build tree data
        var aTree = that._buildTreeData(aSuccessful, aContractList);
        oModel.setProperty("/treeData", aTree);

        // Compute totals
        var fTotalMtm = 0;
        var fTotalQty = 0;
        aSuccessful.forEach(function (r) {
          fTotalMtm += parseFloat(r.data.mtm_value) || 0;
          fTotalQty += parseFloat(r.data.quantity_mt) || 0;
        });

        oModel.setProperty("/totals", {
          total_mtm: fTotalMtm,
          contract_count: aSuccessful.length,
          total_quantity: fTotalQty
        });

        oModel.setProperty("/resultLoaded", true);
        oModel.setProperty("/summaryText",
          aSuccessful.length + " contrato(s) | MTM Total: " + fTotalMtm.toFixed(2) + " USD"
        );

        // Warn about failures
        var nFailed = aResults.length - aSuccessful.length;
        if (nFailed > 0) {
          MessageBox.warning(nFailed + " contrato(s) sem dados de MTM disponíveis.");
        }
      });
    },

    /* ─── Tree building: Contract → detail row ─── */

    _buildTreeData: function (aResults, aContractList) {
      var mContracts = {};
      aContractList.forEach(function (c) { mContracts[c.id] = c; });

      return aResults.map(function (r) {
        var oContract = mContracts[r.id] || {};
        var oData = r.data;
        var fMtm = parseFloat(oData.mtm_value) || 0;

        // Detail row as child
        var oDetail = {
          description: (oData.object_type || "hedge_contract") + " #" + (oData.object_id || r.id || "").substring(0, 8),
          commodity: oContract.commodity || "",
          quantity: parseFloat(oData.quantity_mt) || null,
          entryPrice: parseFloat(oData.entry_price) || null,
          priceD1: parseFloat(oData.price_d1) || null,
          mtmValue: fMtm,
          children: []
        };

        // Contract root node
        return {
          description: oContract.label || (r.id || "").substring(0, 8),
          commodity: oContract.commodity || "",
          quantity: parseFloat(oData.quantity_mt) || null,
          entryPrice: null,
          priceD1: null,
          mtmValue: fMtm,
          children: [oDetail]
        };
      });
    },

    /* ─── TreeTable expand/collapse ─── */

    onExpandAll: function () {
      this.byId("mtmTreeTable").expandToLevel(2);
    },

    onCollapseAll: function () {
      this.byId("mtmTreeTable").collapseAll();
    },

    /* ─── Helpers ─── */

    formatMtmState: function (fValue) {
      if (fValue === undefined || fValue === null) { return "None"; }
      var n = parseFloat(fValue);
      if (n > 0) { return "Success"; }
      if (n < 0) { return "Error"; }
      return "None";
    }
  });
});
