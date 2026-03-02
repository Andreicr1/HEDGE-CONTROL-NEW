sap.ui.define([
    'sap/ui/core/util/MockServer',
    'sap/base/Log'
], function(MockServer, Log) {
    'use strict';
    var oMockServer,
        _sAppModulePath = 'hedgecontrol/',
        _sJsonFilesModulePath = _sAppModulePath + 'localService/mockdata';

    return {
        /**
         * Initializes the mock server.
         * You can configure the delay with the URL parameter "serverDelay".
         * The local mock data in this folder is returned instead of the real data for testing.
         * @public
         */

        init: function() {
            var oUriParameters = new URLSearchParams(window.location.search),
                sJsonFilesUrl = sap.ui.require.toUrl(_sJsonFilesModulePath),
                sManifestUrl = sap.ui.require.toUrl(_sAppModulePath + 'manifest') + '.json',
                sEntity = '',
                sErrorParam = oUriParameters.get('errorType'),
                iErrorCode = sErrorParam === 'badRequest' ? 400 : 500;

            var oSyncXhr = new XMLHttpRequest();
            oSyncXhr.open("GET", sManifestUrl, false);
            oSyncXhr.send();
            var oManifest = JSON.parse(oSyncXhr.responseText),
                oDataSource = oManifest['sap.app'].dataSources,
                oMainDataSource = oDataSource.mainService,
                sMetadataUrl = sap.ui.require.toUrl(
                    _sAppModulePath + oMainDataSource.settings.localUri.replace('.xml', '')
                ) + '.xml',
                // ensure there is a trailing slash
                sMockServerUrl = /.*\/$/.test(oMainDataSource.uri) ? oMainDataSource.uri : oMainDataSource.uri + '/',
                aAnnotations = oMainDataSource.settings.annotations;

            oMockServer = new MockServer({
                rootUri: sMockServerUrl
            });

            // configure mock server with a delay of 1s
            MockServer.config({
                autoRespond: true,
                autoRespondAfter: oUriParameters.get('serverDelay') || 1000
            });

            // load local mock data
            oMockServer.simulate(sMetadataUrl, {
                sMockdataBaseUrl: sJsonFilesUrl,
                bGenerateMissingMockData: true
            });

            var aRequests = oMockServer.getRequests(),
                fnResponse = function(iErrCode, sMessage, aRequest) {
                    aRequest.response = function(oXhr) {
                        oXhr.respond(
                            iErrCode,
                            {
                                'Content-Type': 'text/plain;charset=utf-8'
                            },
                            sMessage
                        );
                    };
                };

            // handling the metadata error test
            if (oUriParameters.get('metadataError')) {
                aRequests.forEach(function(aEntry) {
                    if (aEntry.path.toString().indexOf('$metadata') > -1) {
                        fnResponse(500, 'metadata Error', aEntry);
                    }
                });
            }

            // Handling request errors
            if (sErrorParam) {
                aRequests.forEach(function(aEntry) {
                    if (aEntry.path.toString().indexOf(sEntity) > -1) {
                        fnResponse(iErrorCode, sErrorParam, aEntry);
                    }
                });
            }
            oMockServer.start();

            Log.info('Running the app with mock data');

            if (aAnnotations && aAnnotations.length > 0) {
                aAnnotations.forEach(function(sAnnotationName) {
                    var oAnnotation = oDataSource[sAnnotationName],
                        sUri = oAnnotation.uri,
                        sLocalUri = sap.ui.require.toUrl(
                            _sAppModulePath + oAnnotation.settings.localUri.replace('.xml', '')
                        ) + '.xml';

                    // backend annotations
                    new MockServer({
                        rootUri: sUri,
                        requests: [
                            {
                                method: 'GET',
                                path: new RegExp('([?#].*)?'),
                                response: function(oXhr) {
                                    var oSyncReq = new XMLHttpRequest();
                                    oSyncReq.open("GET", sLocalUri, false);
                                    oSyncReq.send();
                                    var oAnnotations = oSyncReq.responseXML;

                                    oXhr.respondXML(200, {}, new XMLSerializer().serializeToString(oAnnotations));
                                    return true;
                                }
                            }
                        ]
                    }).start();
                });
            }
        },

        /**
         * @public returns the mockserver of the app, should be used in integration tests
         * @returns {sap.ui.core.util.MockServer}
         */
        getMockServer: function() {
            return oMockServer;
        }
    };
});
