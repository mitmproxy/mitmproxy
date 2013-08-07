define([ "./_DetailViewPane", "dojo/text!./templates/PreviewPane.html" ], function(_DetailViewPane, template) {
	return _DetailViewPane.createSubclass([],{
		templateString: template,
		title: "Preview"
	});
});