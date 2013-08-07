/**
 * Flow subclass responsible for proper display of general files. Basically
 * loading file content into a pre tag. Most other flow classes inherit from
 * this.
 */
define(["./AbstractView",
        "../simpleMatcher",
         "dojo/text!./templates/BasicContentView.html"], 
         function(AbstractView, simpleMatcher, template) {
           
  var BasicContentView = AbstractView.createSubclass([],{
  	templateString: template
  });
  
  BasicContentView.className = "flow-text";
  BasicContentView.matches = simpleMatcher(/application|text/i);

  return BasicContentView;
});