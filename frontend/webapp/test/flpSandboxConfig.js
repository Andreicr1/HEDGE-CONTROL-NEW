// eslint-disable-next-line no-unused-vars
window["sap-ushell-config"] = {
	defaultRenderer: "fiori2",
	renderers: {
		fiori2: {
			componentData: {
				config: {
					search: "hidden",
					enableSearch: false
				}
			}
		}
	},
	applications: {
		"app-tile": {
			title: "Hedge Control Alcast",
			description: "Hedge Control – SAPUI5 Frontend",
			additionalInformation: "SAPUI5.Component=hedgecontrol",
			applicationType: "URL",
			url: "../",
			i18n: "../i18n/i18n.properties"
		}
	}
};
