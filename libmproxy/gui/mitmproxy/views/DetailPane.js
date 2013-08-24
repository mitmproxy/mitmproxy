/**
 * Shows details when clicking on a flow.
 */
define(["dojo/_base/declare",
		"dijit/layout/TabContainer",
		"./_CloseableTabContainer",
        "../util/Observer",
		"./DetailPane/RawPane",
		"./DetailPane/PreviewPane",
		"./DetailPane/DetailsPane"
], function(declare, TabContainer, _CloseableTabContainer, Observer, RawPane, PreviewPane, DetailsPane) {

	return declare([TabContainer, _CloseableTabContainer, Observer.ObservablePolyfillMixin], {
		postCreate: function() {
            var self = this;
			this.inherited(arguments);
			var preview = new PreviewPane({model: this.model});
			var raw = new RawPane({model: this.model});
			var details = new DetailsPane({model: this.model});
			this.addChild(preview);
			this.addChild(details);
			this.addChild(raw);

			this.domNode.classList.add("detailPane");
			//Scroll to top when switching tab.
			this.own(
				this.watch("selectedChildWidget", function(_, from, to) {
                    self._updateChild(to);
				    this.containerNode.scrollTop = 0;
			}));

            this.own(
                Observer.observe(this, function(record) {
                    if(record.name !== "model")
                        return;
                    self._updateChild(this.selectedChildWidget);
                }, true)
            );

		},
        /**
         * This function makes sure that the passed child widget displays the currently selected model.
         * For performance reasons, we only update the current tab.
         */
        _updateChild: function(child){
            if(child.model === this.model)
                return;
            var oldValue = child.model;
            child.model = this.model;
            if (oldValue) {
                child.notify({
                    type: "updated",
                    object: child,
                    name: "model",
                    oldValue: oldValue
                });
            } else {
                child.notify({
                    type: "new",
                    object: child,
                    name: "model"
                });
            }
        }
	});
});