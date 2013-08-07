define(["./BinaryView", "../simpleMatcher"], 
         function(BinaryView, simpleMatcher) {
           
  var GoogleSafebrowsingView = BinaryView.createSubclass([]);
  
  GoogleSafebrowsingView.className = "flow-googlesafebrowsing " + BinaryView.className;
  GoogleSafebrowsingView.resourceName = "Google Safe Browsing Service";
  GoogleSafebrowsingView.matches = simpleMatcher(/google\.safebrowsing/i);
  
  return GoogleSafebrowsingView;
});