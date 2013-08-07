define(["./BinaryView", "../simpleMatcher"], 
         function(BinaryView, simpleMatcher) {
           
  var JavaView = BinaryView.createSubclass([]);
  
  JavaView.className = "flow-java " + BinaryView.className;
  JavaView.resourceName = "Java Archive"
  JavaView.matches = simpleMatcher(/application\/java-archive/i, /\.(jar|class)$/i);

  return JavaView;
});