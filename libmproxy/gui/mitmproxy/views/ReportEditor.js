define(["lodash",
		"dojo/_base/declare",
		"dojo/Deferred",
		"../util/_ReactiveTemplatedWidget",
		"dojo/text!./templates/ReportEditor.html",
		"dojo/dom-construct",
		"dojo/query",
		"dojo/request",
		"codemirror",
		"../report/context",
		"../config",
		"../util/requestAuthenticator"
], function(_, declare, Deferred, _ReactiveTemplatedWidget, template, domConstruct, query, request,
	CodeMirror, reportContext, config) {

	var done = new Deferred();
	done.resolve();

	return declare([_ReactiveTemplatedWidget], {
		templateString: template,
		_onShow: function() {
			if (this.codeMirror)
				this.codeMirror.refresh();
		},
		postCreate: function() {
			this.inherited(arguments);
			var self = this;

			// ### Initialize CodeMirror ###
			CodeMirror.commands.autocomplete = function(cm) {
				CodeMirror.simpleHint(cm, CodeMirror.javascriptHint, {
					completeSingle: false,
					additionalContext: reportContext
				});
			};
			CodeMirror.commands.autoformat = function(cm) {
				var range = {
					from: cm.getCursor(true),
					to: cm.getCursor(false)
				};
				if (range.from.ch === range.to.ch && range.from.line === range.to.line)
					range = {
						"from": {
							"ch": 0,
							"line": 0
						},
						"to": {
							"ch": 0,
							"line": cm.lineCount()
						}
				};
				cm.autoIndentRange(range.from, range.to);
			};

			self.codeMirror = CodeMirror.fromTextArea(self.code, {
				lineNumbers: true,
				mode: "javascript",
				tabSize: 2,
				matchBrackets: true,
				extraKeys: {
					"Enter": "newlineAndIndentContinueComment",
					"Ctrl-Enter": self.submitClick.bind(self),
					"Alt-PageDown": self.loadNext.bind(self, 1),
					"Alt-PageUp": self.loadNext.bind(self, -1),
					"Ctrl-Space": "autocomplete",
					"Shift-Ctrl-F": "autoformat"
				}
			});
			self.codeMirror.on("cursorActivity", function() {
				self.codeMirror.matchHighlight("CodeMirror-matchhighlight");
			});
			self.codeMirror.on("change", this.onCodeChange.bind(this));

			// ### Initialize Editor ###
			self.setStatus("Init...", true);
			self.files = [];

			//Load all available scripts
			request(this.api_path + "?recursive=true", {
				handleAs: "json"
			}).then(function(dirs) {

				dirs.forEach(function(dir) {
					dir[2].forEach(function(file) {
						var filename = (dir[0].replace("\\", "/") + "/" + file).substr(1);
						self.files.push(filename);
					});
				});

				self.load("=intro.js");

			});
		},
		api_path: "/api/fs/",
		onCodeChange: function() {
			if (this._saveTimeout)
				window.clearTimeout(this._saveTimeout);
			this._saveTimeout = window.setTimeout(this.save.bind(this), 300);
		},
		getCode: function() {
			return this.codeMirror ? this.codeMirror.getValue() : "";
		},
		newFileClick: function() {
			var self = this;
			var filename = window.prompt("New file name:");
			if (filename !== null) {

				this.save().then(function() {
					//Check if file already exists
					if (self.files.indexOf(filename) > -1)
						return self.load(filename);

					self.files.push(filename);
					self.files.sort();
					self.filename = filename;
					self.updateBindings();
					self.codeMirror.setValue("\n\n\n\n\n\n\n\n");
					self.save(true);
				});
			}
		},
		isFileReadOnly: function() {
			if (config.get("readonly"))
				return true;
			if (this.filename && this.filename[0] === "=")
				return true;
		},
		isSaved: function() {
			return ((this.savedCode === this.getCode()) && (this.savedFile === this.filename));
		},
		save: function(isNewFile) {
			var self = this;

			if (this.isFileReadOnly()) {
				this.setStatus("read only", false);
				return done;
			}
			if (this.isSaved()) {
				return done;
			}

			if (this.files.indexOf(this.filename) === -1) { //a file that isn't in the file list is a deleted file
				return done;
			}

			if (this.saveRequest) {
				this.saveRequest.cancel();
			}

			var def = new Deferred();

			this.setStatus("save...", true);
			this.filename = this.filename.replace(/[^ \w\.\-\/\\]/g, "");
			var method = isNewFile ? request.post : request.put;
			var code = this.getCode();
			this.saveRequest = method(this.api_path + this.filename, {
				data: code,
                headers: { 'Content-Type': 'text/plain' }
			});
			this.saveRequest.then(function() {
				self.setStatus("saved", false);
				self.savedCode = code;
				self.savedFile = self.filename;
				delete self.saveRequest;
				def.resolve.apply(def, arguments);
			});

			return def;
		},
		deleteFileClick: function() {
			var del = window.prompt("Do you really want to delete " + this.filename + "?\nEnter \"" + this.filename + "\" to continue.");
			if (del === this.filename) {
				this.save().then(function() { //We need to save here as .load() calls .save() and .save() should be already done.
					var index = this.files.indexOf(this.filename);
					this.files.splice(index, 1); //Remove file from list
					var nextIndex = index % this.files.length; //modulo in case we're deleting the last file
					this.setStatus("Delete...", true);
					request.del(this.api_path + this.filename).then(function() {
						this.load(this.files[nextIndex]);
					});
				});
			}
		},
		loadNext: function(i) {
			var nextIndex = this.files.indexOf(this.filename) + i;
			//nextIndex modulo this.files.length (% doesn't do modulo for negativ numbers)
			nextIndex = ((nextIndex % this.files.length) + this.files.length) % this.files.length;
			this.load(this.files[nextIndex]);
		},
		submitClick: function() {},
		fileChange: function(event) {
			var filename = event.target[event.target.selectedIndex].value;
			this.load(filename);
		},
		load: function(filename) {
			var self = this;
			this.save().then(function() {
				self.setStatus("Load...", true);
				request.get(self.api_path + filename).then(function(code) {
					self.codeMirror.setValue(code);
					self.setStatus("", false);
					self.filename = filename;
					self.savedCode = code;
					self.savedFile = self.filename;
					self.updateBindings();
				});

			});
		},
		setStatus: function(text, isActive) {
			this.active.textContent = isActive ? text : "";
			this.status.textContent = !isActive ? text : "";
		}
	});

});