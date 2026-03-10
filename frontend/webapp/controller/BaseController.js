sap.ui.define([
	"sap/ui/core/mvc/Controller",
	"sap/ui/model/json/JSONModel",
	"sap/m/MessageBox",
	"sap/m/MessageToast",
	"sap/f/library"
], function (Controller, JSONModel, MessageBox, MessageToast, fioriLibrary) {
	"use strict";

	var LayoutType = fioriLibrary.LayoutType;

	return Controller.extend("hedgecontrol.controller.BaseController", {

		/**
		 * Get the router instance.
		 * @returns {sap.f.routing.Router}
		 */
		getRouter: function () {
			return this.getOwnerComponent().getRouter();
		},

		/**
		 * Get an i18n text by key.
		 * @param {string} sKey
		 * @param {Array} [aArgs]
		 * @returns {string}
		 */
		getI18nText: function (sKey, aArgs) {
			return this.getOwnerComponent().getModel("i18n").getResourceBundle().getText(sKey, aArgs);
		},

		/**
		 * Get the shared app model.
		 * @returns {sap.ui.model.json.JSONModel}
		 */
		getAppModel: function () {
			return this.getOwnerComponent().getModel("app");
		},

		/**
		 * Initialize a named JSONModel on the view.
		 * @param {string} sModelName
		 * @param {object} [oData] - initial data
		 */
		initViewModel: function (sModelName, oData) {
			this._sModelName = sModelName;
			var oDefaults = { busy: false, errorMessage: "" };
			var oMerged = Object.assign({}, oDefaults, oData || {});
			var oModel = new JSONModel(oMerged);
			oModel.setSizeLimit(5000);
			this.getView().setModel(oModel, sModelName);
		},

		/**
		 * Get the view model.
		 * @returns {sap.ui.model.json.JSONModel}
		 */
		getViewModel: function () {
			return this.getView().getModel(this._sModelName);
		},

		/**
		 * Set the FCL layout.
		 * @param {string} sLayout - e.g. "OneColumn", "TwoColumnsMidExpanded"
		 */
		setLayout: function (sLayout) {
			this.getAppModel().setProperty("/layout", sLayout);
		},

		/**
		 * Format error for display (institutional — no HTTP codes, no raw backend details).
		 * @param {Error} oError
		 * @returns {string}
		 */
		_formatError: function (oError) {
			if (!oError) {
				return this.getI18nText("errorUnknown");
			}
			var sMsg = oError.message || this.getI18nText("errorRequestFailed");
			return sMsg;
		},

		/**
		 * Load data from an async service call, store on model property.
		 * @param {function} fnCall - returns Promise
		 * @param {string} sProperty - model property path (e.g. "/items")
		 * @returns {Promise}
		 */
		loadData: function (fnCall, sProperty) {
			var oModel = this.getViewModel();
			var that = this;
			oModel.setProperty("/busy", true);
			oModel.setProperty("/errorMessage", "");
			return fnCall()
				.then(function (oData) {
					oModel.setProperty(sProperty, oData);
					return oData;
				})
				.catch(function (oError) {
					var sMsg = that._formatError(oError);
					oModel.setProperty("/errorMessage", sMsg);
				})
				.finally(function () {
					oModel.setProperty("/busy", false);
				});
		},

		/**
		 * Submit data to a service. Shows success toast, error MessageBox.
		 * @param {function} fnCall - returns Promise
		 * @param {string} [sSuccessMsg] - custom success message
		 * @returns {Promise}
		 */
		submitData: function (fnCall, sSuccessMsg) {
			var oModel = this.getViewModel();
			var that = this;
			oModel.setProperty("/busy", true);
			oModel.setProperty("/errorMessage", "");
			return fnCall()
				.then(function (oData) {
					MessageToast.show(sSuccessMsg || that.getI18nText("msgOperationSuccess"));
					return oData;
				})
				.catch(function (oError) {
					var sMsg = that._formatError(oError);
					oModel.setProperty("/errorMessage", sMsg);
					MessageBox.error(sMsg);
				})
				.finally(function () {
					oModel.setProperty("/busy", false);
				});
		},

		/**
		 * Navigate back to list view (FCL → OneColumn).
		 * @param {string} sRoute - list route name
		 */
		navToList: function (sRoute) {
			this.setLayout(LayoutType.OneColumn);
			this.getRouter().navTo(sRoute, {}, false);
		},

		/**
		 * Navigate to detail view (FCL → TwoColumnsMidExpanded).
		 * @param {string} sRoute - detail route name
		 * @param {object} oParams - route parameters
		 */
		navToDetail: function (sRoute, oParams) {
			this.setLayout(LayoutType.TwoColumnsMidExpanded);
			this.getRouter().navTo(sRoute, oParams, false);
		},

		/**
		 * Navigate to end column view (FCL → ThreeColumnsMidExpanded).
		 * @param {string} sRoute - end column route name
		 * @param {object} oParams - route parameters
		 */
		navToEndColumn: function (sRoute, oParams) {
			this.setLayout(LayoutType.ThreeColumnsMidExpanded);
			this.getRouter().navTo(sRoute, oParams, false);
		},

		/**
		 * Run multiple async calls in parallel. Propagates the first rejection so callers
		 * can handle HTTP errors (401 session expiry, 403 access denied, network failures).
		 * @param {Array<function>} aFnCalls - array of functions returning Promises
		 * @returns {Promise<Array>}
		 */
		loadParallel: function (aFnCalls) {
			return Promise.all(aFnCalls.map(function (fn) { return fn(); }))
				.catch(function (oErr) {
					var iStatus = oErr && oErr.status;
					if (iStatus === 401) {
						console.warn("[SECURITY] SESSION_EXPIRED", { url: oErr.url, ts: Date.now() });
						window.location.href = "/";
					} else if (iStatus === 403) {
						console.warn("[SECURITY] ACCESS_DENIED", { url: oErr.url, ts: Date.now() });
					} else if (iStatus === 429) {
						console.warn("[SECURITY] RATE_LIMITED", { url: oErr.url, ts: Date.now() });
					} else {
						console.error("[APP] LOAD_FAILURE", oErr);
					}
					return Promise.reject(oErr);
				});
		},

		/**
		 * Set busy state on a specific control by local ID (granular, not page-level).
		 * @param {string} sControlId - local view ID
		 * @param {boolean} bBusy
		 */
		setBusy: function (sControlId, bBusy) {
			var oControl = this.byId(sControlId);
			if (oControl) { oControl.setBusy(bBusy); }
		},

		/**
		 * Validate a route ID parameter — accepts UUID v4 or plain numeric strings.
		 * Prevents requests being fired with garbage values (e.g. "undefined", ":id").
		 * @param {*} sId
		 * @returns {boolean}
		 */
		_isValidId: function (sId) {
			if (!sId || typeof sId !== "string") { return false; }
			var rUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
			var rNumeric = /^\d+$/;
			return rUuid.test(sId) || rNumeric.test(sId);
		},

		/**
		 * Show a confirmation dialog, wrapped in a Promise.
		 * @param {string} sMessage
		 * @param {string} [sTitle]
		 * @returns {Promise<boolean>} resolves true if user confirmed
		 */
		showConfirm: function (sMessage, sTitle) {
			return new Promise(function (resolve) {
				MessageBox.confirm(sMessage, {
					title: sTitle || "Confirmar",
					onClose: function (sAction) {
						resolve(sAction === MessageBox.Action.OK);
					}
				});
			});
		}
	});
});
