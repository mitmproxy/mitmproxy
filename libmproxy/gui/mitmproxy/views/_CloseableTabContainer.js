define(["dojo/_base/declare", "dojo/dom-construct", "dojo/on"], function(declare, domConstruct, on) {
	return declare([], {
		postCreate: function() {

			var closeButton = domConstruct.toDom('<button style="position: absolute;right: 2px;top:0;z-index:2"class="close">&times;</button>');
			domConstruct.place(closeButton, this.tablist.tablistWrapper, "first");
			this.own(
				on(closeButton, "click", this.destroyRecursive.bind(this)));
		}
	});
});