/**
 * Main View
 */
define([
		"require",
		"dojo/_base/declare",
		"dojo/_base/lang",
		"dojo/dom-construct",
		"dijit/layout/BorderContainer",
		"./_DetailViewMixin",
		"./ReportOutput",
		"./ReportEditor",
		"../report/context"
], function(require, declare, lang, domConstruct, BorderContainer, _DetailViewMixin, ReportOutput, ReportEditor, reportContext) {
	return declare([BorderContainer, _DetailViewMixin], {
		design: "sidebar",
		postCreate: function() {
			var self = this;

			this.reportOutput = new ReportOutput({
				region: "center",
				splitter: true
			});

			this.reportEditor = new ReportEditor({
				region: "right",
				splitter: true,
				submitClick: function() {
					var code = self.reportEditor.getCode();
					if (self.detailView)
						self.detailView.destroyRecursive();
					domConstruct.empty(self.reportOutput.out);

					var _mid;
					try {
                        
                        if(self.active){
                            self.active.shutdown();
                        }

						/*jshint evil:true, withstmt:true*/
						// https://developers.google.com/closure/compiler/docs/compilation_levels
						// Compilation [...] always preserves the functionality of syntactically valid JavaScript, 
						// provided that the code does not access local variables using string names (by using eval() statements, for example).
						window._reportPaneExterns = lang.mixin({}, reportContext, {
							detailView: {
								showDetails: self.showDetails.bind(self)
							},
							out: self.reportOutput.out
						});

						//Adjust RequireJS module loading path
						_mid = require.module.mid;
						require.module.mid = "ReportScripts/" + self.reportEditor.filename;
                        var module;
						with(window._reportPaneExterns) {
							module = eval(code);
						}
                        if(module && typeof module === "object"){
                            self.active = module;
                            if(module.start)
                                module.start();
                            
                        }

					} catch (e) {

						//TODO: This is ugly.
						self.reportOutput.out.innerHTML = "<pre>" + e.message + "\n\n" + e.stack.replace(/http.+?\/\/.+?\//g, "") + "</pre>";
						console.log(e);
						window.HoneyProxy.exception = e;

					} finally {

						delete window._reportPaneExterns;
						require.module.mid = _mid;

					}
				}
			});

			//populate trafficPane
			self.addChild(self.reportOutput);
			self.addChild(self.reportEditor);
		},
		_onShow: function() {
			this.reportEditor._onShow(); //Delegate _onShow to avoid sizing issues with CodeMirror
		}
	});
});