define(["./BinaryView","../simpleMatcher"], 
         function(BinaryView, simpleMatcher) {
           
  var FlashView = BinaryView.createSubclass([]);
  
  FlashView.className = "flow-flash " + BinaryView.className;
  FlashView.resourceName = "Adobe Flash file"
  FlashView.matches = simpleMatcher(/flash/i, /\.swf$/i);

  return FlashView;
});