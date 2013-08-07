define(["dojo/_base/declare",
		'dojo/aspect',
		"./DetailPane"
], function(declare, aspect, DetailPane) {
	return declare([], {
		showDetails: function(flow) {

			var self = this;

			if (this.detailView) {
				this.detailView.setModel(flow);
			} else {
				this.detailView = new DetailPane({
					region: "bottom",
					splitter: true
				});
				this.detailView.setModel(flow);
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