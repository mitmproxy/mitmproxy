define(["dojo/_base/declare",
		'dojo/aspect',
		"./DetailPane"
], function(declare, aspect, DetailPane) {
	return declare([], {
		showDetails: function(flow) {

			var self = this;

			if (this.detailView) {
                var oldValue = this.detailView.model;
				this.detailView.model = flow;
                this.detailView.notify({
						type: "updated",
						name: "model",
						object: this.detailView,
						oldValue: oldValue
				});
			} else {
				this.detailView = new DetailPane({
					region: "bottom",
					splitter: true,
                    model: flow
                });
				var signal = aspect.before(this.detailView,"destroy",function(){
					signal.remove();
					self.removeChild(self.detailView);
					delete self.detailView;
				});
				this.addChild(this.detailView);
			}
		}
	});
});