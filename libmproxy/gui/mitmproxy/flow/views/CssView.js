define(["./BasicContentView","../simpleMatcher"], 
         function(BasicContentView, simpleMatcher) {
           
  var CssView = BasicContentView.createSubclass([]);
  
  CssView.className = "flow-css " + BasicContentView.className;
  CssView.matches = simpleMatcher(/css/i, /\.css$/i);
  
  return CssView;
});