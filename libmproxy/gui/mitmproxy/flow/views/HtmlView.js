define(["./BasicContentView", "../simpleMatcher"], 
         function(BasicContentView, simpleMatcher) {
           
  var HtmlView = BasicContentView.createSubclass([]);
  
  HtmlView.className = "flow-html " + BasicContentView.className;
  HtmlView.matches = simpleMatcher(/html/i, /\.(x?html|php|aspx?)$/i);

  return HtmlView;
});