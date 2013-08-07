define(["./BasicContentView", "../simpleMatcher"], 
         function(BasicContentView, simpleMatcher) {
           
  var XmlView = BasicContentView.createSubclass([]);
  
  XmlView.className = "flow-xml " + BasicContentView.className;
  XmlView.matches = simpleMatcher(/xml/i, /\.xml$/i);

  return XmlView;
});