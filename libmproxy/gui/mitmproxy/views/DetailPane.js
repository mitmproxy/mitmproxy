/**
 * Shows details when clicking on a flow.
 */
define(["dojo/_base/declare",
		"dijit/layout/TabContainer",
		"./_CloseableTabContainer",
		"./DetailPane/RawPane",
		"./DetailPane/PreviewPane",
		"./DetailPane/DetailsPane"
], function(declare, TabContainer, _CloseableTabContainer, RawPane, PreviewPane, DetailsPane) {

	return declare([TabContainer, _CloseableTabContainer], {
		postCreate: function() {
			this.inherited(arguments);
			var preview = new PreviewPane();
			var raw = new RawPane();
			var details = new DetailsPane();
			this.addChild(preview);
			this.addChild(details);
			this.addChild(raw);

			this.domNode.classList.add("detailPane");
			//Scroll to top when switching tab.
			this.own(
				this.watch("selectedChildWidget", function() {
				this.containerNode.scrollTop = 0;
			}));

		},
		setModel: function(model) {
			if (this.get("model") === model)
				return;
			this.set("model", model);
			this.getChildren().forEach(function(c) {

				var oldValue = c.model;
				c.model = model;
				if (oldValue) {
					c.notify({
						type: "updated",
						object: c,
						name: "model",
						oldValue: oldValue
					});
				} else {
					c.notify({
						type: "new",
						object: c,
						name: "model"
					});
				}

			});
		}
	});
});