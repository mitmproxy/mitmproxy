define(["dojo/_base/lang",
		"./_DetailViewPane",
		"../../flow/FlowBindings",
		"dojo/text!./templates/RawPane.html"
], function(lang, _DetailViewPane, FlowBindings, template) {

	//remove prettifyTransform from displayContent
	var rawBindings = lang.mixin({}, FlowBindings);
	rawBindings.displayContent = FlowBindings._displayContent(undefined, undefined);

	return _DetailViewPane.createSubclass([], {
		bindings: rawBindings,
		templateString: template,
		title: "Raw"
	});
});