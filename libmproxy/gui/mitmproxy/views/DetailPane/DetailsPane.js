define(["lodash",
		"dojo/_base/declare",
		"./_DetailViewPane",
		"dojo/dom-construct",
		"dojo/text!./templates/DetailsPane.html"
], function(_, declare, _DetailViewPane, domConstruct, template) {

	return declare([_DetailViewPane], {
		templateString: template,
		title: "Details",
		loadContent: function() {
			var model = this.get("model");
			if (model.request.hasFormData) {
				var requestContentNode = this.requestContentNode;
				var headerRow = domConstruct.place("<tr></tr>", requestContentNode,
					"only");
				var loading = domConstruct.place("<td colspan=2>Loading...</td>",
					headerRow, "last");
				model.request.getFormData().then(function(formData) {
					var fragment = document.createDocumentFragment();
					for (var i = 0; i < formData.length; i++) {
						fragment.appendChild(domConstruct.toDom("<tr><td>" +
							_.escape(decodeURIComponent(formData[i].name)) + "</td><td>" +
							_.escape(decodeURIComponent(formData[i].value)) +
							"</td></tr>"));
					}
					domConstruct.empty(loading);
					domConstruct.place(fragment, requestContentNode, "last");
				});
			} else {
				domConstruct.empty(this.requestContentNode);
			}
		}
	});

});